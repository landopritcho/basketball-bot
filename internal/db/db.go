// Package db holds the logic for interacting with the backend SQLite database
package db

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type Database struct {
	DB *sql.DB
}

func New(path string) (Database, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return Database{}, err
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return Database{}, fmt.Errorf("create or connect to new database: %w", err)
	}

	return Database{DB: db}, nil
}

func (d *Database) Close() error {
	return d.DB.Close()
}
