package api

import (
	"database/sql"
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/landopritcho/basketball-bot/internal/date"
	"github.com/landopritcho/basketball-bot/internal/db"
)

type UpcomingGamesResponse struct {
	Games []UpcomingGame `json:"games"`
	Count int            `json:"count"`
}

type UpcomingGame struct {
	Tipoff                 string  `json:"tipoff"`
	LongDescription        string  `json:"long_description"`
	AbbreviatedDescription string  `json:"abbreviated_description"`
	Venue                  string  `json:"venue"`
	EventTitle             *string `json:"event_title,omitempty"`
	BroadcastChannel       string  `json:"broadcast_channel"`
	HomeTeamName           *string `json:"home_team_name"`
	HomeTeamAbbreviation   *string `json:"home_team_abbreviation"`
	HomeTeamRank           *int    `json:"home_team_rank"`
	AwayTeamName           *string `json:"away_team_name"`
	AwayTeamAbbreviation   *string `json:"away_team_abbreviation"`
	AwayTeamRank           *int    `json:"away_team_rank"`
}

func GetUpcomingGames(database *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		games, err := db.GetUpcomingGames(r.Context(), database)
		if err != nil {
			slog.ErrorContext(r.Context(), "get upcoming games", "error", err)
			http.Error(w, "Unable to retrieve upcoming games", http.StatusInternalServerError)
			return
		}

		response := UpcomingGamesResponse{
			Games: make([]UpcomingGame, 0, len(games)),
		}

		for _, game := range games {
			tipoff, err := date.ConvertUnixToCentralDatetime(game.Tipoff)
			if err != nil {
				slog.ErrorContext(r.Context(), "format upcoming game tipoff", "game_id", game.Id, "error", err)
				http.Error(w, "Unable to prepare upcoming games", http.StatusInternalServerError)
				return
			}

			var eventTitle *string
			if game.Title != "" {
				eventTitle = &game.Title
			}

			response.Games = append(response.Games, UpcomingGame{
				Tipoff:                 tipoff,
				LongDescription:        game.LongDescription,
				AbbreviatedDescription: game.AbbreviatedDescription,
				Venue:                  game.Venue,
				EventTitle:             eventTitle,
				BroadcastChannel:       game.BroadcastChannel,
				HomeTeamName:           game.HomeTeamName,
				HomeTeamAbbreviation:   game.HomeTeamAbbreviation,
				HomeTeamRank:           game.HomeTeamRank,
				AwayTeamName:           game.AwayTeamName,
				AwayTeamAbbreviation:   game.AwayTeamAbbreviation,
				AwayTeamRank:           game.AwayTeamRank,
			})
		}

		response.Count = len(response.Games)

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(response); err != nil {
			slog.ErrorContext(r.Context(), "write upcoming games response", "error", err)
		}
	}
}
