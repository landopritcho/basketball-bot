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

type UpcomingGameDetails struct {
	Id                     string
	Tipoff                 int64
	LongDescription        string
	AbbreviatedDescription string
	Venue                  string
	Title                  string
	BroadcastChannel       string
	HomeTeamName           *string
	HomeTeamAbbreviation   *string
	HomeTeamRank           *int
	AwayTeamName           *string
	AwayTeamAbbreviation   *string
	AwayTeamRank           *int
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

func GetUpcomingGames(ctx context.Context, db *sql.DB) ([]UpcomingGameDetails, error) {
	sql := `
	SELECT
		games.id,
		games.tipoff,
		games.long_description,
		games.abbreviated_description,
		games.venue,
		games.title,
		games.broadcast_channel,
		home.display_name AS home_team_name,
		home.abbreviation AS home_team_abbreviation,
		home.rank AS home_team_rank,
		away.display_name AS away_team_name,
		away.abbreviation AS away_team_abbreviation,
		away.rank AS away_team_rank
	FROM upcoming_games AS games
	LEFT JOIN teams AS home ON games.home_team_id = home.id
	LEFT JOIN teams AS away ON games.away_team_id = away.id
	ORDER BY games.tipoff ASC, games.id ASC;`
	rows, err := db.QueryContext(ctx, sql)
	if err != nil {
		return nil, fmt.Errorf("get upcoming_games: %w", err)
	}
	defer rows.Close()

	var games []UpcomingGameDetails
	for rows.Next() {
		game := &UpcomingGameDetails{}
		err := rows.Scan(
			&game.Id,
			&game.Tipoff,
			&game.LongDescription,
			&game.AbbreviatedDescription,
			&game.Venue,
			&game.Title,
			&game.BroadcastChannel,
			&game.HomeTeamName,
			&game.HomeTeamAbbreviation,
			&game.HomeTeamRank,
			&game.AwayTeamName,
			&game.AwayTeamAbbreviation,
			&game.AwayTeamRank,
		)
		if err != nil {
			return nil, fmt.Errorf("reading upcoming_games: %w", err)
		}
		games = append(games, *game)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate upcoming_games: %w", err)
	}

	return games, nil
}
