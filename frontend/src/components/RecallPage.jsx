import React, { useState } from 'react';
import { useParams } from 'react-router-dom';

export default function RecallPage() {
  const { topic } = useParams();
  const [recallText, setRecallText] = useState('');
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    const res = await fetch('/recall', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, recall_text: recallText })
    });
    if (res.ok) {
      setResult(await res.json());
    } else {
      setResult({ error: 'Recall failed' });
    }
  };

  return (
    <div>
      <h2>Recall: {topic}</h2>
      <form onSubmit={submit}>
        <textarea
          value={recallText}
          onChange={(e) => setRecallText(e.target.value)}
          rows={10}
          placeholder="Write everything you remember"
          required
        />
        <div>
          <button type="submit">Submit</button>
        </div>
      </form>
      {result && (
        <div>
          {result.error && <p>{result.error}</p>}
          {result.score !== undefined && (
            <div>
              <p>Score: {result.score}</p>
              <p>Feedback: {result.feedback}</p>
              <p>Cards Added: {result.cards_added}</p>
              <p>Next Review: {result.next_review}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
