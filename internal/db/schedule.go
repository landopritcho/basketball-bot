package db

import (
	"database/sql"

	"github.com/landopritcho/basketball-bot/internal/date"
	"github.com/landopritcho/basketball-bot/internal/espn"

	_ "modernc.org/sqlite"
)

func InsertUpcomingScheduleRecord(d *sql.DB, s espn.ScheduledGame) (int64, error) {
	sql := `INSERT INTO upcoming_schedule (id, tipoff, long_description, abbreviated_description, venue, title, broadcast_channel, home_team_id, away_team_id)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);`
	convertedDatetime, err := date.ConvertCentralDatetimeToUnix(s.Datetime)
	if err != nil {
		return 0, err
	}
	result, err := d.Exec(
		sql,
		s.Id,
		convertedDatetime,
		s.LongDescription,
		s.AbbreviatedDescription,
		s.Venue,
		s.Title,
		s.BroadcastChannel,
		s.HomeTeam.Details.Id,
		s.AwayTeam.Details.Id,
	)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}

type upcomingGame struct {
	Id                     string
	Datetime               string
	LongDescription        string
	AbbreviatedDescription string
	Venue                  string
	Title                  string
	BroadcastChannel       string
	HomeTeamId             int
	AwayTeamId             int
}

func GetUpcomingSchedule(d *sql.DB) ([]upcomingGame, error) {
	sql := `SELECT * FROM upcoming_schedule`
	rows, err := d.Query(sql)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var games []upcomingGame
	var datetime int64
	for rows.Next() {
		game := &upcomingGame{}
		err := rows.Scan(
			&game.Id,
			&datetime,
			&game.LongDescription,
			&game.AbbreviatedDescription,
			&game.Venue,
			&game.Title,
			&game.BroadcastChannel,
			&game.HomeTeamId,
			&game.AwayTeamId,
		)
		if err != nil {
			return nil, err
		}
		game.Datetime, err = date.ConvertUnixToCentralDatetime(datetime)
		if err != nil {
			return nil, err
		}
		games = append(games, *game)
	}

	return games, nil
}
