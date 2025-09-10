from app.utils import card_hash, chunk_material
from app.scheduler import next_interval


def test_chunk_material() -> None:
    content = "Part1\n\nPart2\n\n"
    assert chunk_material(content) == ["Part1", "Part2"]


def test_card_hash_deterministic() -> None:
    assert card_hash("front", "back") == card_hash("front", "back")


def test_next_interval() -> None:
    assert next_interval(0, 50) == 1
    assert next_interval(1, 90) == 2
    assert next_interval(2, 70) == 2
