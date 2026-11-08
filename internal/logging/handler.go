package logging

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type terminalHandler struct {
	level  slog.Level
	color  bool
	mu     *sync.Mutex // Prevents background processes and API logs from getting mixed together
	attrs  []scopedAttr
	groups []string
}

type scopedAttr struct {
	attr   slog.Attr
	groups []string
}

func newHandler(cfg Config) slog.Handler {
	return &terminalHandler{
		level: cfg.Level,
		color: cfg.Color,
		mu:    &sync.Mutex{},
	}
}

func (h *terminalHandler) Enabled(_ context.Context, level slog.Level) bool {
	return level >= h.level
}

func (h *terminalHandler) Handle(_ context.Context, record slog.Record) error {
	// At some point I'd like to replace Time.Local() with a location from a shared Config
	timestamp := record.Time.Local().Format("2006-01-02 03:04:05 PM")
	message := record.Message
	labelText := record.Level.String()
	isRequest := record.Message == "HTTP request"

	if isRequest {
		labelText, message = requestDetails(record)
	}

	label := fmt.Sprintf("%-7s", "["+labelText+"]")

	if h.color {
		timestamp = "\x1b[90m" + timestamp + "\x1b[0m"
		label = levelColor(record.Level) + label + "\x1b[0m"
	}

	line := fmt.Sprintf("%s %s %s", timestamp, label, message)

	for _, attr := range h.attrs {
		line += formatAttr(attr.attr, attr.groups)
	}

	record.Attrs(func(attr slog.Attr) bool {
		if isRequest {
			switch attr.Key {
			case "method", "path", "status", "duration":
				return true
			}
		}

		line += formatAttr(attr, h.groups)
		return true
	})

	h.mu.Lock()
	defer h.mu.Unlock()

	_, err := fmt.Fprintln(os.Stderr, line)
	return err
}

func (h *terminalHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	clone := *h
	clone.attrs = make([]scopedAttr, len(h.attrs), len(h.attrs)+len(attrs))
	copy(clone.attrs, h.attrs)

	for _, attr := range attrs {
		clone.attrs = append(clone.attrs, scopedAttr{
			attr:   attr,
			groups: h.groups,
		})
	}

	return &clone
}

func (h *terminalHandler) WithGroup(name string) slog.Handler {
	if name == "" {
		return h
	}

	clone := *h
	clone.groups = make([]string, len(h.groups)+1)
	copy(clone.groups, h.groups)
	clone.groups[len(h.groups)] = name

	return &clone
}

func requestDetails(record slog.Record) (method, message string) {
	var path string
	var status int
	var duration time.Duration

	record.Attrs(func(attr slog.Attr) bool {
		switch attr.Key {
		case "method":
			method = attr.Value.String()
		case "path":
			path = attr.Value.String()
		case "status":
			status = int(attr.Value.Int64())
		case "duration":
			duration = attr.Value.Duration()
		}
		return true
	})

	message = fmt.Sprintf("%s %d %s",
		path, status, duration.Round(time.Millisecond),
	)
	return method, message
}

func formatAttr(attr slog.Attr, groups []string) string {
	attr.Value = attr.Value.Resolve()
	if attr.Equal(slog.Attr{}) {
		return ""
	}

	key := attr.Key
	if len(groups) > 0 {
		key = strings.Join(groups, ".") + "." + key
	}

	if attr.Value.Kind() == slog.KindGroup {
		nestedGroups := groups
		if attr.Key != "" {
			nestedGroups = []string{key}
		}

		var result string
		for _, child := range attr.Value.Group() {
			result += formatAttr(child, nestedGroups)
		}
		return result
	}

	value := attr.Value.String()
	if value == "" || strings.ContainsAny(value, " \t\r\n\"=\\") {
		value = strconv.Quote(value)
	}

	return " " + key + "=" + value
}

func levelColor(level slog.Level) string {
	switch {
	case level >= slog.LevelError:
		return "\x1b[31m" // Red
	case level >= slog.LevelWarn:
		return "\x1b[33m" // Yellow
	case level >= slog.LevelInfo:
		return "\x1b[32m" // Green
	default:
		return "\x1b[36m" // Cyan
	}
}
