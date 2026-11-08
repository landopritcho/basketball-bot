package logging

import (
	"log/slog"
	"net/http"
	"time"
)

type responseWriter struct {
	http.ResponseWriter
	status int
}

func (w *responseWriter) WriteHeader(status int) {
	if w.status != 0 {
		return
	}

	w.ResponseWriter.WriteHeader(status)

	if status >= 200 {
		w.status = status
	}
}

func (w *responseWriter) Write(body []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}

	return w.ResponseWriter.Write(body)
}

func (w *responseWriter) Unwrap() http.ResponseWriter {
	return w.ResponseWriter
}

func Middleware(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			wrapped := &responseWriter{ResponseWriter: w}

			next.ServeHTTP(wrapped, r)

			status := wrapped.status
			if status == 0 {
				status = http.StatusOK
			}

			level := slog.LevelInfo
			switch {
			case status >= 500:
				level = slog.LevelError
			case status >= 400:
				level = slog.LevelWarn
			}

			logger.Log(r.Context(), level, "HTTP request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", status,
				"duration", time.Since(start),
			)
		})
	}
}
