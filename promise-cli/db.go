package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// Verse is a single stored promise row.
type Verse struct {
	Book    string   `json:"book"`
	Chapter int      `json:"chapter"`
	Verse   int      `json:"verse"`
	Text    string   `json:"text"`
	Tags    []string `json:"tags"`
}

// Reference returns the human-readable citation, e.g. "Jeremiah 29:11".
func (v Verse) Reference() string {
	return fmt.Sprintf("%s %d:%d", v.Book, v.Chapter, v.Verse)
}

// openDB opens the SQLite database read-only.
func openDB(path string) (*sql.DB, error) {
	dsn := "file:" + path + "?mode=ro"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	return db, nil
}

// queryVerse picks the daily promise. It prefers verses matching the user's
// preferred tags; otherwise it falls back to the full pool.
func queryVerse(db *sql.DB, tags []string, seed int64) (Verse, error) {
	// Prefer matching at least one preferred tag.
	if len(tags) > 0 {
		if v, ok := queryByTags(db, tags, seed); ok {
			return v, nil
		}
	}
	// Fallback: any promise.
	return queryAll(db, seed)
}

// queryByTags selects a pseudo-random verse (seeded by the day) that matches
// any of the preferred tags. Returns false if no verse matches.
func queryByTags(db *sql.DB, tags []string, seed int64) (Verse, bool) {
	rows, err := db.Query(
		`SELECT book, chapter, verse, text, tags FROM promesas
		 ORDER BY verse_id`)
	if err != nil {
		return Verse{}, false
	}
	defer rows.Close()

	var candidates []Verse
	for rows.Next() {
		var v Verse
		var tagsJSON string
		if err := rows.Scan(&v.Book, &v.Chapter, &v.Verse, &v.Text, &tagsJSON); err != nil {
			continue
		}
		if err := json.Unmarshal([]byte(tagsJSON), &v.Tags); err != nil {
			v.Tags = nil
		}
		if intersects(v.Tags, tags) {
			candidates = append(candidates, v)
		}
	}
	if len(candidates) == 0 {
		return Verse{}, false
	}
	return candidates[pick(seed, len(candidates))], true
}

// queryAll selects a pseudo-random verse from the whole promise pool.
func queryAll(db *sql.DB, seed int64) (Verse, error) {
	rows, err := db.Query(
		`SELECT book, chapter, verse, text, tags FROM promesas
		 ORDER BY verse_id`)
	if err != nil {
		return Verse{}, err
	}
	defer rows.Close()

	var candidates []Verse
	for rows.Next() {
		var v Verse
		var tagsJSON string
		if err := rows.Scan(&v.Book, &v.Chapter, &v.Verse, &v.Text, &tagsJSON); err != nil {
			continue
		}
		if err := json.Unmarshal([]byte(tagsJSON), &v.Tags); err != nil {
			v.Tags = nil
		}
		candidates = append(candidates, v)
	}
	if len(candidates) == 0 {
		return Verse{}, errors.New("no promises found in database")
	}
	return candidates[pick(seed, len(candidates))], nil
}

// intersects reports whether any tag in a is also present in b.
func intersects(a, b []string) bool {
	for _, x := range a {
		for _, y := range b {
			if x == y {
				return true
			}
		}
	}
	return false
}
