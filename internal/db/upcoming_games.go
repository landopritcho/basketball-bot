package db

import (
	"context"
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type UpcomingGame struct {
	Id                     string // "401913099"
	Tipoff                 int64  // Unix timestamp, 1794164400
	LongDescription        string // "Western Carolina Catamounts at North Carolina Tar Heels"
	AbbreviatedDescription string // "WCU @ UNC"
	Venue                  string // "Dean E. Smith Center"
	Title                  string // "Orion180 Tipoff Classic"
	BroadcastChannel       string // "ACC Network"
	HomeTeamId             int    // 153
	AwayTeamId             int    // 496
}

func UpdateUpcomingGames(ctx context.Context, db *sql.DB, games []UpcomingGame) (int64, error) {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin upcoming games refresh: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	if _, err := tx.ExecContext(ctx, "DELETE FROM upcoming_games"); err != nil {
		return 0, fmt.Errorf("clear upcoming_games: %w", err)
	}

	query := `INSERT INTO upcoming_games (
		id,
		tipoff,
		long_description,
		abbreviated_description,
		venue,
		title,
		broadcast_channel,
		home_team_id,
		away_team_id
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`

	for _, game := range games {
		_, err := tx.ExecContext(
			ctx,
			query,
			game.Id,
			game.Tipoff,
			game.LongDescription,
			game.AbbreviatedDescription,
			game.Venue,
			game.Title,
			game.BroadcastChannel,
			game.HomeTeamId,
			game.AwayTeamId,
		)
		if err != nil {
			return 0, fmt.Errorf("insert upcoming game %q: %w", game.Id, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit upcoming games refresh: %w", err)
	}

	return int64(len(games)), nil
}

func GetUpcomingGames(db *sql.DB) ([]UpcomingGame, error) {
	sql := "SELECT * FROM upcoming_games"
	rows, err := db.Query(sql)
	if err != nil {
		return nil, fmt.Errorf("get upcoming_games: %w", err)
	}
	defer rows.Close()

	var games []UpcomingGame
	for rows.Next() {
		game := &UpcomingGame{}
		err := rows.Scan(
			&game.Id,
			&game.Tipoff,
			&game.LongDescription,
			&game.AbbreviatedDescription,
			&game.Venue,
			&game.Title,
			&game.BroadcastChannel,
			&game.HomeTeamId,
			&game.AwayTeamId,
		)
		if err != nil {
			return nil, fmt.Errorf("reading upcoming_games: %w", err)
		}
		games = append(games, *game)
	}

	return games, nil
}
