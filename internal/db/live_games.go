package db

import (
	"context"
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type LiveGame struct {
	Id                string // "401913099"
	Venue             string // "Dean E. Smith Center"
	Title             string // "Orion180 Tipoff Classic"
	BroadcastChannel  string // "ACC Network"
	HomeTeamId        int    // 153
	AwayTeamId        int    // 496
	HomeTeamScore     int    // 3
	AwayTeamScore     int    // 4
	DisplayClock      string // "17:23"
	Half              string // "1"
	StatusDescription string // "In Progress"
	StatusDetail      string // "17:23 - 1st Half"
	StatusShortDetail string // "17:23 - 1st"
}

type LiveGameDetails struct {
	Id                   string
	Venue                string
	Title                string
	HomeTeamSchoolName   string
	HomeTeamName         string
	HomeTeamAbbreviation string
	HomeTeamRank         *int
	HomeTeamScore        int
	AwayTeamSchoolName   string
	AwayTeamName         string
	AwayTeamAbbreviation string
	AwayTeamRank         *int
	AwayTeamScore        int
	DisplayClock         string
	Half                 string
	StatusDescription    string
}

func UpdateLiveGames(ctx context.Context, db *sql.DB, games []LiveGame) (int64, error) {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin live games refresh: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	if _, err := tx.ExecContext(ctx, "DELETE FROM live_games"); err != nil {
		return 0, fmt.Errorf("clear live_games: %w", err)
	}

	query := `INSERT INTO live_games (
		id,
		venue,
		title,
		broadcast_channel,
		home_team_id,
		away_team_id,
		home_team_score,
		away_team_score,
		display_clock,
		half,
		status_description,
		status_detail,
		status_short_detail
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	for _, game := range games {
		_, err := tx.ExecContext(
			ctx,
			query,
			game.Id,
			game.Venue,
			game.Title,
			game.BroadcastChannel,
			game.HomeTeamId,
			game.AwayTeamId,
			game.HomeTeamScore,
			game.AwayTeamScore,
			game.DisplayClock,
			game.Half,
			game.StatusDescription,
			game.StatusDetail,
			game.StatusShortDetail,
		)
		if err != nil {
			return 0, fmt.Errorf("insert live game %q: %w", game.Id, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit live games refresh: %w", err)
	}

	return int64(len(games)), nil
}

func GetLiveGames(ctx context.Context, db *sql.DB) ([]LiveGameDetails, error) {
	sql := `
	SELECT
		games.id,
		games.venue,
		games.title,
		home.location AS home_team_school_name,
		home.name AS home_team_name,
		home.abbreviation AS home_team_abbreviation,
		games.home_team_score,
		home.rank AS home_team_rank,
		away.location AS away_team_school_name,
		away.name AS away_team_name,
		away.abbreviation AS away_team_abbreviation,
		games.away_team_score,
		away.rank AS away_team_rank,
		games.display_clock,
		games.half,
		games.status_description
	FROM live_games AS games
	LEFT JOIN teams AS home ON games.home_team_id = home.id
	LEFT JOIN teams AS away ON games.away_team_id = away.id
	ORDER BY games.half ASC, games.id ASC;`
	rows, err := db.QueryContext(ctx, sql)
	if err != nil {
		return nil, fmt.Errorf("get live_games: %w", err)
	}
	defer rows.Close()

	var games []LiveGameDetails
	for rows.Next() {
		game := &LiveGameDetails{}
		err := rows.Scan(
			&game.Id,
			&game.Venue,
			&game.Title,
			&game.HomeTeamSchoolName,
			&game.HomeTeamName,
			&game.HomeTeamAbbreviation,
			&game.HomeTeamScore,
			&game.HomeTeamRank,
			&game.AwayTeamSchoolName,
			&game.AwayTeamName,
			&game.AwayTeamAbbreviation,
			&game.AwayTeamScore,
			&game.AwayTeamRank,
			&game.DisplayClock,
			&game.Half,
			&game.StatusDescription,
		)
		if err != nil {
			return nil, fmt.Errorf("reading live_games: %w", err)
		}
		games = append(games, *game)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate live_games: %w", err)
	}

	return games, nil
}
