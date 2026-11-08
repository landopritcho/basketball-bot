package logging

import (
	"log/slog"
)

type Config struct {
	Level slog.Level
	Color bool // Whether to include terminal color codes
}

func New(cfg Config) *slog.Logger {
	return slog.New(newHandler(cfg))
}
