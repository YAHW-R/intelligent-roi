#!/usr/bin/env python3
"""Candidate verse filter (Fase 1, paso 1).

Reduces the full Bible (31,103 verses) to a manageable list of "candidate"
verses that are likely to contain an explicit or implicit promise from God.
These candidates are then sent to an LLM (Ollama) for classification.

Design notes
------------
- Uses fast keyword regex (pandas str.contains), NO LLM calls here.
- Focuses on strong divine-promise markers to keep volume low and precision
  high: first-person divine speech, third-person divine declarations, and the
  classic "do not be afraid" comfort formula.
- The World English Bible uses contractions like "Don't", so both spellings are
  matched.

Usage
-----
    python3 candidates.py [--min-candidates N] [--out candidates.csv]
"""

import argparse
import re

import pandas as pd

CSV_PATH = "bible-english.csv"
DEFAULT_OUT = "candidates.csv"
HEADER_ROWS_TO_SKIP = 4  # 3 header text lines + column-name row

# Verbs that, when used in divine first/third person, strongly signal a promise.
_PROMISE_VERBS = (
    r"bless|give|provide|protect|heal|be with|save|deliver|make|lead|cause|"
    r"redeem|restore|answer|guide|forgive|strengthen|uphold|comfort|show|do|"
    r"pour|put|receive|multiply|keep|crown|supply"
)

_PATTERNS = [
    # 1. Divine first-person promises ("I will ...")
    rf"\bI will\s+(?:{_PROMISE_VERBS}|\w+\s+\w+)",
    # 2. Divine self-identification ("I am the LORD your God")
    r"\bI am (?:the )?(?:LORD|Yahweh|God|your God)\b",
    # 3. "I am with you" (implied protection/presence promise)
    r"\bI am with you\b",
    # 4. The LORD / God "will ..."
    rf"\b(?:the LORD|Yahweh|God)\s+will\s+(?:{_PROMISE_VERBS}|\w+\s+\w+)",
    # 5. Prophetic "declares the LORD" / "says the LORD"
    r"\b(?:declares|says|saith) the (?:LORD|Yahweh)\b",
    # 6. Comfort/presence formula "do not be afraid"
    r"\b(?:do not be afraid|don'?t(?: you)? be afraid|fear not|be not afraid)\b",
    # 7. Blessing / covenant markers
    r"\bblessed (?:shall|will|is)\b|\bwill bless\b",
]


def build_mask(texts: pd.Series) -> pd.Series:
    """Return a boolean mask of candidate verses matching any pattern."""
    # Combine all patterns into one alternation for a single vectorized pass.
    combined = "|".join(f"(?:{p})" for p in _PATTERNS)
    rx = re.compile(combined, re.IGNORECASE)
    return texts.str.contains(rx)


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter candidate promise verses.")
    parser.add_argument(
        "--csv", default=CSV_PATH, help="Path to the English Bible CSV."
    )
    parser.add_argument(
        "--out", default=DEFAULT_OUT, help="Output CSV path for candidates."
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv, skiprows=HEADER_ROWS_TO_SKIP, encoding="utf-8")
    texts = df["Text"].fillna("")

    mask = build_mask(texts)
    candidates = df.loc[mask].copy()

    print(f"Total verses scanned : {len(df)}")
    print(f"Candidate verses    : {len(candidates)} "
          f"({len(candidates) / len(df) * 100:.2f}%)")

    candidates.to_csv(args.out, index=False)
    print(f"Candidates written to {args.out}")


if __name__ == "__main__":
    main()
