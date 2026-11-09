package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/landopritcho/basketball-bot/internal/api"
	"github.com/landopritcho/basketball-bot/internal/db"
	"github.com/landopritcho/basketball-bot/internal/logging"
)

func main() {
	slog.SetDefault(logging.New(logging.Config{
		Level: slog.LevelInfo,
		Color: true,
	}))

	if err := run(); err != nil {
		slog.Error("Fatal", "error", err)
		os.Exit(1)
	}
}

func run() error {
	ctx, stop := signal.NotifyContext(
		context.Background(), os.Interrupt, syscall.SIGTERM,
	)
	defer stop()

	database, err := db.New("./basketball.db")
	if err != nil {
		return err
	}
	defer database.Close()

	handler, err := api.New(database.DB)
	if err != nil {
		return err
	}

	handler = logging.Middleware(slog.Default())(handler)
	return serve(ctx, handler)
}

func serve(ctx context.Context, handler http.Handler) error {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := &http.Server{
		Addr:              ":" + port,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}

	failed := make(chan error, 1)
	go func() {
		slog.Info("Listening", "address", server.Addr)
		failed <- server.ListenAndServe()
	}()

	select {
	case err := <-failed:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return fmt.Errorf("serving: %w", err)

	case <-ctx.Done():
		slog.Info("Shutting down")
	}

	shutdownCtx, cancel := context.WithTimeout(
		context.Background(), 10*time.Second,
	)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		_ = server.Close()
		return fmt.Errorf("shutdown: %w", err)
	}

	return nil
}
