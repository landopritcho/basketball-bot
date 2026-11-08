package db

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	_ "modernc.org/sqlite"
)

func Migrate(ctx context.Context, d Database, path string) error {
	entries, err := os.ReadDir(path)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".sql") {
			continue
		}

		scriptPath := filepath.Join(path, entry.Name())

		script, err := os.ReadFile(scriptPath)
		if err != nil {
			return fmt.Errorf("migrate: %w", err)
		}

		if _, err := d.DB.ExecContext(ctx, string(script)); err != nil {
			return fmt.Errorf("execute SQL: %w", err)
		}
	}

	return nil
}
