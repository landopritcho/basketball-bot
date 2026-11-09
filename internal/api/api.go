package api

import (
	"database/sql"
	"net/http"
)

const basePath = "/landolytics/api"

func New(database *sql.DB) (http.Handler, error) {
	mux := http.NewServeMux()

	mux.HandleFunc("GET "+basePath+"/health", health())
	mux.HandleFunc("GET "+basePath+"/upcomingGames", GetUpcomingGames(database))

	return mux, nil
}

func health() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("OK"))
	}
}
