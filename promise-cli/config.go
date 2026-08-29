package main

import (
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

// Config holds the user preferences read from ~/.config/promesas/config.toml.
//
//	tags_preferidos are English tags (same tokens as in promesas.db) used to
//	prefer certain promises over the full pool. When empty or when no verse
//	matches them, the CLI falls back to the full promise pool.
type Config struct {
	Usuario        string   `toml:"usuario"`
	TagsPreferidos []string `toml:"tags_preferidos"`
	DBPath         string   `toml:"db_path"`
}

// DefaultDBPath returns the default location for the SQLite promises database.
func DefaultDBPath() string {
	if p := os.Getenv("PROMESAS_DB"); p != "" {
		return p
	}
	return filepath.Join(defaultConfigDir(), "promesas.db")
}

// defaultConfigDir resolves the config directory: $PROMESAS_CONFIG or
// $XDG_CONFIG_HOME/promesas, else ~/.config/promesas.
func defaultConfigDir() string {
	if d := os.Getenv("PROMESAS_CONFIG"); d != "" {
		return d
	}
	base := os.Getenv("XDG_CONFIG_HOME")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			home = "."
		}
		base = filepath.Join(home, ".config")
	}
	return filepath.Join(base, "promesas")
}

// ConfigPath returns the path to the TOML config file.
func ConfigPath() string {
	return filepath.Join(defaultConfigDir(), "config.toml")
}

// LoadConfig reads the TOML config file. Missing fields fall back to sane
// defaults and a missing file yields an empty Config (never an error).
func LoadConfig() (Config, error) {
	var cfg Config
	path := ConfigPath()
	// Defaults.
	cfg.DBPath = DefaultDBPath()
	cfg.Usuario = ""

	if _, err := os.Stat(path); os.IsNotExist(err) {
		return cfg, nil
	}

	// Preserve defaults across parse: use a copy that only assigns present keys.
	if _, err := toml.DecodeFile(path, &cfg); err != nil {
		return Config{}, err
	}
	if cfg.DBPath == "" {
		cfg.DBPath = DefaultDBPath()
	}
	return cfg, nil
}
