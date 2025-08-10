from typing import Iterator, List

PATTERN: List[str] = [
    "LEFT","RIGHT","UP","DOWN",
    "LEFT","UP","RIGHT","DOWN",
    "MENU","INTERACT",
    "UP","UP","RIGHT","DOWN","LEFT"
]

def routine() -> Iterator[str]:
    i = 0
    while True:
        yield PATTERN[i % len(PATTERN)]
        i += 1
