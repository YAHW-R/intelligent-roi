package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"hash/fnv"
	"math/rand"
	"os"
	"time"
)

// REF: daily promise engine. The "seed" is derived from the current date so
// that the same promise is shown all day (useful for desktop widgets) and only
// changes the next day.

const gracefulMessage = "Descansa en Dios"

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(args []string) int {
	fs := flag.NewFlagSet("promesas-cli", flag.ContinueOnError)
	showToday := fs.Bool("hoy", false, "Show the promise of the day")
	asJSON := fs.Bool("json", false, "Output as JSON")
	asText := fs.Bool("texto", false, "Output as plain text")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	if *showToday {
		return today(*asJSON, *asText)
	}
	fs.Usage()
	fmt.Fprintln(os.Stderr, "(default) Use --hoy to show the promise of the day.")
	return 0
}

// today prints the daily promise and returns an exit code.
func today(asJSON, asText bool) int {
	cfg, err := LoadConfig()
	if err != nil {
		return fail()
	}

	db, err := openDB(cfg.DBPath)
	if err != nil {
		return fail()
	}
	defer db.Close()

	seed := daySeed(time.Now())
	v, err := queryVerse(db, cfg.TagsPreferidos, seed)
	if err != nil {
		return fail()
	}

	switch {
	case asJSON:
		out, _ := json.Marshal(map[string]any{
			"text":      v.Text,
			"reference": v.Reference(),
			"tags":      v.Tags,
			"usuario":   cfg.Usuario,
		})
		fmt.Println(string(out))
	default:
		// Both --texto and the default print a readable line.
		prefix := ""
		if cfg.Usuario != "" {
			prefix = cfg.Usuario + ": "
		}
		fmt.Printf("%s%s (%s)%s",
			prefix, v.Text, v.Reference(), "\n")
	}
	return 0
}

// fail prints a graceful fallback and returns exit code 0 so a status bar is
// never broken by a stack trace.
func fail() int {
	fmt.Println(gracefulMessage)
	return 0
}

// daySeed returns a deterministic pseudo-random seed derived from the date. The
// same seed is returned all day, regardless of the current time.
func daySeed(now time.Time) int64 {
	date := now.Format("2006-01-02")
	h := fnv.New64a()
	_, _ = h.Write([]byte(date))
	return int64(h.Sum64())
}

// pick returns an index into [0, n) using the seeded PRNG. Deterministic for a
// given seed; stable across runs on the same day.
func pick(seed int64, n int) int {
	if n <= 1 {
		return 0
	}
	r := rand.New(rand.NewSource(seed))
	return r.Intn(n)
}
