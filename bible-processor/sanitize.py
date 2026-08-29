#!/usr/bin/env python3
"""Post-processing sanitizer (run once, after classify.py completes).

The small LLM sometimes invents tags that are not in the canonical set (e.g.
"land", "covenant", "companionhip"). This script walks the whole promesas.db and
drops any tag outside the canonical English list, falling back to "hope" like
the classifier does. It is idempotent and safe to re-run.

Usage
-----
    python3 sanitize.py [--db promesas.db]
"""

import argparse
import json
import sqlite3

from prompt import TAGS

ALLOWED = set(TAGS)


def sanitize(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT verse_id, tags FROM promesas").fetchall()

    updated = 0
    for verse_id, tags_json in rows:
        try:
            tags = json.loads(tags_json)
        except (TypeError, ValueError):
            tags = []
        clean = [t for t in tags if t in ALLOWED][:2]
        if not clean:
            clean = ["hope"]
        clean_json = json.dumps(clean)
        if clean_json != tags_json:
            conn.execute(
                "UPDATE promesas SET tags = ? WHERE verse_id = ?",
                (clean_json, verse_id),
            )
            updated += 1

    conn.commit()
    conn.close()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize promise tags.")
    parser.add_argument("--db", default="promesas.db", help="SQLite database path.")
    args = parser.parse_args()

    updated = sanitize(args.db)
    print(f"Sanitized {updated} verse(s) in {args.db}.")


if __name__ == "__main__":
    main()
