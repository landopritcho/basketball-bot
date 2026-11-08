package api

import "net/http"

const basePath = "/landolytics/api"

func New() (http.Handler, error) {
	mux := http.NewServeMux()

	mux.HandleFunc("GET "+basePath+"/health", health())

	return mux, nil
}

func health() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("OK"))
	}
}
