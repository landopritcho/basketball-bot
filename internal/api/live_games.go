package api

import (
	"database/sql"
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/landopritcho/basketball-bot/internal/db"
)

type LiveGamesResponse struct {
	Games []LiveGame `json:"games"`
	Count int        `json:"count"`
}

type LiveGame struct {
	Venue                string  `json:"venue"`
	EventTitle           *string `json:"event_title,omitempty"`
	HomeTeamSchoolName   string  `json:"home_team_school_name"`
	HomeTeamName         string  `json:"home_team_name"`
	HomeTeamAbbreviation string  `json:"home_team_abbreviation"`
	HomeTeamRank         *int    `json:"home_team_rank,omitempty"`
	HomeTeamScore        int     `json:"home_team_score"`
	AwayTeamSchoolName   string  `json:"away_team_school_name"`
	AwayTeamName         string  `json:"away_team_name"`
	AwayTeamAbbreviation string  `json:"away_team_abbreviation"`
	AwayTeamRank         *int    `json:"away_team_rank,omitempty"`
	AwayTeamScore        int     `json:"away_team_score"`
	DisplayClock         string  `json:"display_clock"`
	Half                 string  `json:"half"`
	StatusDescription    string  `json:"status_description"`
}

func GetLiveGames(database *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		games, err := db.GetLiveGames(r.Context(), database)
		if err != nil {
			slog.ErrorContext(r.Context(), "get live games", "error", err)
			http.Error(w, "Unable to retrieve upcoming games", http.StatusInternalServerError)
			return
		}

		response := LiveGamesResponse{
			Games: make([]LiveGame, 0, len(games)),
		}

		for _, game := range games {
			var eventTitle *string
			if game.Title != "" {
				eventTitle = &game.Title
			}

			response.Games = append(response.Games, LiveGame{
				Venue:                game.Venue,
				EventTitle:           eventTitle,
				HomeTeamSchoolName:   game.HomeTeamSchoolName,
				HomeTeamName:         game.HomeTeamName,
				HomeTeamAbbreviation: game.HomeTeamAbbreviation,
				HomeTeamRank:         game.HomeTeamRank,
				HomeTeamScore:        game.HomeTeamScore,
				AwayTeamSchoolName:   game.AwayTeamSchoolName,
				AwayTeamName:         game.AwayTeamName,
				AwayTeamAbbreviation: game.AwayTeamAbbreviation,
				AwayTeamRank:         game.AwayTeamRank,
				AwayTeamScore:        game.AwayTeamScore,
				DisplayClock:         game.DisplayClock,
				Half:                 game.Half,
				StatusDescription:    game.StatusDescription,
			})
		}

		response.Count = len(response.Games)

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(response); err != nil {
			slog.ErrorContext(r.Context(), "write live games response", "error", err)
		}
	}
}
