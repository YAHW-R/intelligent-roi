#!/usr/bin/env python3
"""LLM classifier (Fase 1, paso 3).

Takes the candidate verses produced by candidates.py, sends each one to a local
Ollama model (llama3.2:3b), decides whether it is a divine promise, and writes
only the promises into an SQLite database (promesas.db).

Reliability features
--------------------
- Uses only the Python standard library (urllib + sqlite3 + json): no extra deps.
- Progress is checkpointed to a `progreso` table after every `--batch-size`
  verses, so the run can be resumed after an interruption without restarting
  from the beginning.
- Parses the model's JSON defensively (extracts the first {...} block) and
  retries transient network errors.
- `--limit` runs only over the first N candidates for a smoke test; `--skip`
  resumes from a given offset.

Usage
-----
    # Smoke test on the first 30 candidates
    python3 classify.py --limit 30

    # Full run
    python3 classify.py

    # Resume from the last checkpoint
    python3 classify.py --resume
"""

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.request

from prompt import TAGS, build_prompt

ALLOWED_TAGS = set(TAGS)

CANDIDATES_CSV = "candidates.csv"
DB_PATH = "promesas.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
SAVE_EVERY = 50  # checkpoint every N verses
REQUEST_TIMEOUT = 120  # seconds
DELAY = 0.2  # small delay between calls to avoid saturating the machine

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS promesas (
            verse_id INTEGER PRIMARY KEY,
            book     TEXT NOT NULL,
            chapter  INTEGER NOT NULL,
            verse    INTEGER NOT NULL,
            text     TEXT NOT NULL,
            tags     TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS progreso (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
        """
    )
    conn.commit()
    return conn


def get_progress(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT valor FROM progreso WHERE clave = 'next_offset'"
    ).fetchone()
    return int(row[0]) if row and row[0] else 0


def set_progress(conn: sqlite3.Connection, offset: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO progreso (clave, valor) VALUES ('next_offset', ?)",
        (str(offset),),
    )
    conn.commit()


def call_ollama(text: str, reference: str, attempt: int = 1) -> dict:
    """Call Ollama and return the parsed JSON response. Retries on failure."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": build_prompt(text, reference)}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},  # deterministic classification
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
        content = data["message"]["content"]
        return parse_json(content)
    except Exception as e:  # noqa: BLE001 - classify errors are expected at scale
        if attempt >= 3:
            raise RuntimeError(f"Ollama call failed for {reference!r}: {e}") from e
        time.sleep(2 * attempt)
        return call_ollama(text, reference, attempt + 1)


def parse_json(content: str) -> dict:
    """Extract the first JSON object from the model's raw text output."""
    match = JSON_RE.search(content)
    if not match:
        raise ValueError(f"No JSON object found in response: {content!r}")
    obj = json.loads(match.group(0))
    # Normalize keys to the expected schema.
    if "is_promise" not in obj and "es_promesa" in obj:
        obj["is_promise"] = obj["es_promesa"]
    if "tags" not in obj and "etiquetas" in obj:
        obj["tags"] = obj["etiquetas"]
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify candidate verses.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Only process the first N candidates (0 = all).")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from the last checkpoint.")
    parser.add_argument("--db", default=DB_PATH, help="SQLite output path.")
    parser.add_argument("--batch", type=int, default=SAVE_EVERY,
                        help="Checkpoint interval (verse count).")
    args = parser.parse_args()

    import pandas as pd
    df = pd.read_csv(CANDIDATES_CSV)
    df["Text"] = df["Text"].fillna("")

    conn = make_conn(args.db)
    offset = get_progress(conn) if args.resume else 0
    if args.limit:
        df = df.iloc[: args.limit]
    if offset > 0:
        df = df.iloc[offset:]

    added = 0
    print(f"Model        : {MODEL}")
    print(f"Processing   : {len(df)} candidate(s) starting at offset {offset}")
    print(f"Checkpoint   : every {args.batch} verse(s) -> {args.db}")

    for i, (_, row) in enumerate(df.iterrows(), start=offset):
        verse_id = int(row["Verse ID"])
        book = str(row["Book Name"])
        chapter = int(row["Chapter"])
        verse = int(row["Verse"])
        text = str(row["Text"])
        reference = f"{book} {chapter}:{verse}"

        try:
            result = call_ollama(text, reference)
        except RuntimeError as e:
            print(f"  [{i}] ERROR {reference}: {e}", file=sys.stderr)
            continue

        is_promise = bool(result.get("is_promise", False))
        if is_promise:
            tags = result.get("tags", [])
            if not isinstance(tags, list) or not tags:
                tags = []
            # Keep only canonical tags; drop any the model invented.
            tags = [str(t).strip() for t in tags if str(t).strip() in ALLOWED_TAGS][:2]
            if not tags:
                tags = ["hope"]
            conn.execute(
                """INSERT OR REPLACE INTO promesas
                   (verse_id, book, chapter, verse, text, tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (verse_id, book, chapter, verse, text, json.dumps(tags)),
            )
            added += 1

        # Checkpoint periodically so an interruption doesn't lose everything.
        if (i + 1) % args.batch == 0:
            conn.commit()
            set_progress(conn, i + 1)
            print(f"  [{i + 1}] checkpoint saved "
                  f"({added} promise(s) so far)")

    conn.commit()
    # Reset progress so the next full run starts cleanly.
    set_progress(conn, 0)
    conn.close()
    print(f"Done. {added} promise(s) written to {args.db}")


if __name__ == "__main__":
    main()
