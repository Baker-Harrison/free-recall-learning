"""Scheduling utilities."""


def next_interval(prev: int, score: int) -> int:
    """Compute the next interval in days based on previous interval and score."""
    if prev <= 0:
        return 1
    if score < 60:
        return 1
    if score < 80:
        return max(1, prev)
    return prev * 2
