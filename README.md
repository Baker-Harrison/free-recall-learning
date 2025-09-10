# Ultra‑Specific Coding Prompt: Free Recall Study App (SQLite + AnkiConnect)

You are an expert full‑stack engineer tasked with producing a production‑ready app that implements a **free recall learning cycle** with AI feedback, **SQLite** persistence, and **Anki** synchronization via **AnkiConnect**. Generate complete, runnable code and documentation per the specs below. Favor clarity, correctness, and robust error handling.

---

## Goals

1. Let users upload study material and chunk it into topics.
2. Run free‑recall sessions that compare recall vs. source using an LLM.
3. Parse **strict JSON** from the LLM (score, feedback, flashcards).
4. Persist everything in SQLite.
5. Automatically create atomic flashcards for missed/incorrect info and sync to Anki.
6. Maintain a topic‑level expanded retrieval schedule (1, 2, 4, 7, 14, … days).
7. Provide endpoints and a minimal frontend for upload, recall, due topics, and history.

---

## Implementation Constraints

* **Language**: Python 3.11+.
* **Framework**: Prefer **FastAPI** for built‑in OpenAPI and pydantic. If you use Flask, replicate equivalent validation with `pydantic`/`marshmallow`. FastAPI is recommended.
* **DB**: SQLite (`study_app.db`) using `sqlite3` or `sqlalchemy` (recommended) with WAL mode enabled. Include indices and constraints.
* **LLM Provider**: Gemini with a pluggable interface (plus a no‑network `MockLLM` for tests). Use the official client library and hide keys in environment variables.
* **Anki**: AnkiConnect at `http://localhost:8765`. Create deck if missing. Prevent duplicates.
* **Time**: Store UTC timestamps as ISO 8601. Convert to local time only in UI.
* **Security**: Input validation, request size limits, CORS config, API key loading from env, simple auth hook (optional token) that can be toggled via env.

---

## Environment & Config

Provide `.env.example` and config loader.

* `LLM_PROVIDER=gemini|mock`
* `GEMINI_API_KEY=...`
* `MODEL_NAME=gemini-1.5-flash`
* `ANKI_CONNECT_URL=http://localhost:8765`
* `ANKI_DECK_NAME=Pharmacy_Recall_AI`
* `APP_AUTH_TOKEN=` (optional; if set, require `Authorization: Bearer <token>`)
* `MAX_UPLOAD_BYTES=1048576` (1MB default)

---

## Data Model (SQL)

Use **SQLAlchemy** models or raw DDL (include migrations/init script). Ensure indexes and uniqueness where noted.

```sql
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS study_material (
  id INTEGER PRIMARY KEY,
  topic TEXT NOT NULL UNIQUE,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Optional: chunked material for long sources (improves diffing & coverage)
CREATE TABLE IF NOT EXISTS material_chunk (
  id INTEGER PRIMARY KEY,
  topic TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  FOREIGN KEY(topic) REFERENCES study_material(topic) ON DELETE CASCADE,
  UNIQUE(topic, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunk_topic ON material_chunk(topic);

-- Free recall history
CREATE TABLE IF NOT EXISTS recall_history (
  id INTEGER PRIMARY KEY,
  topic TEXT NOT NULL,
  recall_text TEXT NOT NULL,
  feedback_json TEXT NOT NULL,
  score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
  created_at TEXT NOT NULL,
  FOREIGN KEY(topic) REFERENCES study_material(topic) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_history_topic_created ON recall_history(topic, created_at DESC);

-- Flashcards (dedupe via content hash)
CREATE TABLE IF NOT EXISTS flashcard (
  id INTEGER PRIMARY KEY,
  topic TEXT NOT NULL,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  front_back_sha256 TEXT NOT NULL,
  added_to_anki INTEGER NOT NULL DEFAULT 0,
  anki_note_id INTEGER,
  created_at TEXT NOT NULL,
  UNIQUE(front_back_sha256)
);
CREATE INDEX IF NOT EXISTS idx_flash_topic ON flashcard(topic);

-- Topic scheduling (expanded retrieval)
CREATE TABLE IF NOT EXISTS topic_schedule (
  topic TEXT PRIMARY KEY,
  interval_days INTEGER NOT NULL,
  next_review TEXT NOT NULL,
  last_review TEXT,
  easiness REAL NOT NULL DEFAULT 2.3 -- reserved if later moving to SM-2/FSRS
);
```

Include a small migration helper (e.g., `user_version` pragma) to evolve schema.

---

## Material Chunking Strategy

Implement `chunk_material(content) -> list[str]`:

* Split by headings (`\n#`, `\n##`, slide titles), then further by paragraphs/bullets.
* Target **\~800–1200 tokens** per chunk (estimate by words or tiktoken if available).
* Preserve order; store `chunk_index`.
* For diffing/coverage, keep chunks separate in DB.

---

## LLM Contract (Strict JSON)

LLM must return **exact JSON** only, matching this **JSON Schema** (Draft‑07). No markdown fences, no comments.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["score", "feedback", "flashcards"],
  "properties": {
    "score": {"type": "integer", "minimum": 0, "maximum": 100},
    "feedback": {"type": "string", "minLength": 1},
    "flashcards": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["front", "back"],
        "properties": {
          "front": {"type": "string", "minLength": 1, "maxLength": 200},
          "back":  {"type": "string", "minLength": 1, "maxLength": 500},
          "tags":  {"type": "array", "items": {"type": "string"}},
          "priority": {"type": "string", "enum": ["low","medium","high"], "default": "medium"}
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
```

**Atomic flashcard rules (must be enforced by the LLM prompt):**

* One fact per card; no multi‑step procedures on a single card.
* Front is a single question/cue; back is concise (≤ \~25–40 words when possible).
* Avoid vague terms; include units and thresholds where relevant.
* No duplicates or near‑duplicates; prefer most general version.

### LLM Prompt Template

Provide this exact prompt when calling the LLM (fill variables). If the topic has chunks, compare against concatenated chunk content or chunk‑wise and aggregate.

```
SYSTEM:
You strictly output JSON that conforms to the provided JSON Schema. Do not include Markdown or commentary.

USER:
Compare this student free recall to the official notes.
Return ONLY valid JSON conforming to the schema (no code fences):

JSON Schema:
<insert JSON schema above verbatim>

Student Recall (plain text):
"""
{RECALL_TEXT}
"""

Source Material for topic "{TOPIC}":
"""
{SOURCE_TEXT}
"""

Scoring guidance:
- 100 = complete and accurate, no omissions
- 80–99 = minor omissions or small inaccuracies
- 60–79 = several omissions or inaccuracies
- <60 = major gaps or wrong statements

Feedback:
- 3–6 bullet points: biggest omissions, misunderstandings, and succinct advice.

Flashcards:
- Create atomic front/back pairs ONLY for missed or incorrect information.
- Enforce max lengths.
- Avoid duplicates; prefer general, syllabus‑aligned facts.
- If none missed: return an empty list.
```

### JSON Validation & Repair Strategy

* Validate against schema with `jsonschema`. If validation fails, run a **single** automatic repair step:

  * Strip markdown fences, attempt `json.loads`.
  * If still invalid, prompt LLM with: *“Repair the following into JSON that validates against the schema. Output JSON only.”* and include the invalid output. Re‑validate.
* If still invalid, fall back to `{ "score": 0, "feedback": "LLM output invalid", "flashcards": [] }` and log.

---

## AnkiConnect Integration (Deduping & Idempotency)

* Ensure deck exists (`createDeck`).
* Before adding, check for duplicates:

  1. Compute `sha256(front + "\x1e" + back)`; store in DB with `UNIQUE`.
  2. Query AnkiConnect `findNotes` with `deck:{deck} "{front}"` (escape quotes). Optionally fetch `notesInfo` to compare fields.
* Add note with action `addNote` (model `Basic`, tags: `AIRecall`, `Topic:{topic}`), `options.allowDuplicate=false`.
* Update `flashcard.added_to_anki=1` and `anki_note_id` on success. Handle errors gracefully.

---

## Scheduling Logic (Topic‑Level)

* Expanded retrieval sequence: **1, 2, 4, 7, 14, 28, 56, …** (doubling after day 7 optional). Implement as: if record exists, `new_interval = next_interval(prev_interval)`, else `1`.
* `next_interval(i)` default: `i < 7 ? i*2 : i*2` (i.e., doubling always), configurable via env or settings.
* `last_review = now() UTC`, `next_review = today + new_interval`.
* (Optional) If `score < 60`, reset to `1`. If `60≤score<80`, halve the increment.

---

## API Design

Return JSON; include OpenAPI docs (FastAPI auto). Enforce optional bearer token if `APP_AUTH_TOKEN` is set.

**POST `/upload`**

* Body: `{ "topic": str, "content": str }`
* Behavior: upsert `study_material`, regenerate `material_chunk` via `chunk_material`, update `updated_at`.
* Returns: `{ "status": "ok", "topic": "...", "chunks": N }`

**GET `/topics`**

* Returns: `[ {"topic": str, "updated_at": iso, "has_chunks": bool } ]`

**POST `/recall`**

* Body: `{ "topic": str, "recall": str }`
* Steps: fetch source (concatenate chunks if any) → LLM → validate JSON → persist recall\_history → create flashcards (DB + Anki) → update schedule.
* Returns: `{ "score": int, "feedback": str, "flashcards_added": int, "next_review": iso }`

**GET `/due`**

* Query: `?date=YYYY-MM-DD` (optional; default today)
* Returns: `{ "due_topics": [str] }`

**GET `/history/{topic}`**

* Returns: `[ { "recall": str, "feedback": str, "score": int, "created_at": iso } ]`

**GET `/health`**

* Returns: `{ "ok": true }`

**POST `/flashcards/sync`** (optional manual retry)

* Body: `{ "topic": str|null }` (if null, sync all unsent)
* Returns: `{ "synced": int }`

**Errors**: Use consistent structure `{ "error": { "type": str, "message": str } }` and proper HTTP codes.

---

## Backend Structure (Suggested)

```
app/
  main.py              # FastAPI app, routers include
  config.py            # env loading
  db.py                # engine/session, init, migrations
  models.py            # SQLAlchemy models
  schemas.py           # pydantic request/response models
  chunking.py          # chunk_material()
  llm/
    __init__.py
    provider.py        # interface + factory
    gemini_provider.py
    mock_provider.py
  anki.py              # AnkiConnect client + dedupe
  scheduling.py        # next interval logic
  routes/
    material.py        # /upload, /topics
    recall.py          # /recall, /history, /due
    flashcards.py      # /flashcards/sync
  utils/json_guard.py  # schema validation & repair
  utils/hash.py        # sha256(front+sep+back)
  utils/auth.py        # optional bearer token

frontend/
  streamlit_app.py     # or React app (Vite) with simple UI

.tests/
  test_api.py          # pytest + httpx
  test_chunking.py
  test_llm_contract.py # validate provider output against JSON schema
  test_anki.py         # requests-mock for AnkiConnect

Dockerfile
docker-compose.yml
README.md
.env.example
```

---

## Minimal Frontend (Streamlit or React)

**Must‑have views:**

* **Upload**: textarea/file upload for content → topic text input → upload button → server response.
* **Recall Session**: select topic → show only topic/cue → textarea for free recall → submit → display score (progress bar), feedback bullets, and next review date; show cards added.
* **Dashboard**: list due topics (today), quick start buttons.
* **History**: topic selector → table of attempts (timestamp, score) → expandable feedback.

---

## Testing & Quality

* **Unit tests** for chunking, scheduling, hashing, JSON validation.
* **Integration tests** for `/upload`, `/recall`, `/due`, `/history/{topic}` using `MockLLM` and `requests-mock` for Anki.
* **Type checking**: `mypy` configuration.
* **Linting**: `ruff` or `flake8`.
* **Logging**: structured logs with `logging` at INFO/ERROR; include request IDs.

---

## Error Handling & Edge Cases

* Large uploads: enforce `MAX_UPLOAD_BYTES`; return 413.
* Missing topic: 404 with helpful message.
* LLM outages/timeouts: circuit breaker/backoff (retry ×2) then degrade gracefully (score=0, no cards).
* AnkiConnect down: queue cards in DB with `added_to_anki=0`; `/flashcards/sync` can retry.
* Duplicate cards: prevent via `front_back_sha256` and Anki search.
* Unicode/emoji: ensure UTF‑8 everywhere.

---

## Example Workflows

1. **Upload**: POST `/upload` `{topic:"Enzymes Intro", content:"..."}` → chunks stored.
2. **Recall**: POST `/recall` with memory dump → returns `{score: 72, feedback: "...", flashcards_added: 5, next_review: "..."}`.
3. **Due**: GET `/due` → `["Enzymes Intro", "Nucleic Acids"]`.
4. **History**: GET `/history/Enzymes Intro` → list of attempts.

---

## Acceptance Criteria

* All endpoints function as specified with robust validation and error handling.
* LLM output strictly validates against JSON Schema; repair step implemented.
* Flashcards are atomic, deduped, and synced to Anki; retries supported.
* Scheduling updates after each recall attempt and surfaces via `/due`.
* Frontend provides upload, recall, due list, and history with clear UX.
* Tests pass (≥90% coverage for core logic), app runs with `make run` or `uvicorn app.main:app`.

---

## Deliverables

* Full codebase per structure above.
* `README.md` with setup (venv, install, env vars), running instructions, and screenshots/gifs (optional).
* `.env.example` filled with placeholders.
* Postman/REST Client examples or OpenAPI served at `/docs`.

---

## Optional Enhancements (If Time Allows)

* **FTS5** index for content search.
* **Per‑topic rubrics** to weight sections in scoring.
* **SM‑2/FSRS** topic scheduling with per‑attempt quality mapping from `score`.
* **Role‑based auth** for multi‑user.
* **Export** flashcards as TSV/CSV.

---

## Reference Snippets (Implement or Adapt)

### JSON Repair Helper (concept)

````python
from jsonschema import validate, ValidationError

def parse_llm_json(output_str: str, schema: dict) -> dict:
    raw = output_str.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.strip('`')
    try:
        data = json.loads(raw)
        validate(data, schema)
        return data
    except Exception as e:
        # Optional: single repair roundtrip to LLM
        raise
````

### Anki Dedupe Hash

```python
import hashlib

def card_hash(front: str, back: str) -> str:
    return hashlib.sha256((front + "\x1e" + back).encode("utf-8")).hexdigest()
```

### Next Interval Logic

```python
def next_interval(prev: int, score: int) -> int:
    if prev <= 0:
        return 1
    if score < 60:
        return 1
    if score < 80:
        return max(1, prev)  # soft repeat
    return prev * 2
```

---

## Final Instruction to the Code Generator

Produce:

1. A fully working **FastAPI** backend with the specified routes, models, validation, logging, tests, and Docker setup.
2. A minimal but usable **Streamlit** (or React) frontend implementing the required views.
3. Clear **README** covering setup, running, and troubleshooting (AnkiConnect, deck creation, API keys).
4. Ensure strict adherence to the **LLM JSON Schema**, atomic flashcards, Anki dedupe, and topic scheduling.

Return the complete codebase and docs in your answer.
