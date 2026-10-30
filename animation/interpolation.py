from __future__ import annotations


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * smoothstep(amount)
