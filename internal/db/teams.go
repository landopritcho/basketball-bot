package db

import (
	"context"
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type Team struct {
	Id             string // "153"
	Location       string // "North Carolina"
	Name           string // "Tar Heels"
	Abbreviation   string // "UNC"
	DisplayName    string // "North Carolina Tar Heels"
	Slug           string // "north-carolina-tar-heels"
	PrimaryColor   string // "7bafd4"
	AlternateColor string // "13284b"
	Rank           *int   // "1"
}

func UpsertTeams(ctx context.Context, db *sql.DB, teams []Team) (int64, error) {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("upsert teams: %w", err)
	}
	defer func() {
		_ = tx.Rollback()
	}()

	query := `INSERT INTO teams (
		id,
		location,
		name,
		abbreviation,
		display_name,
		slug,
		primary_color,
		alternate_color,
		rank
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	ON CONFLICT (id)
	DO UPDATE SET
		location = excluded.location,
		name = excluded.name,
		abbreviation = excluded.abbreviation,
		display_name = excluded.display_name,
		slug = excluded.slug,
		primary_color = excluded.primary_color,
		alternate_color = excluded.alternate_color,
		rank = excluded.rank
	WHERE
		teams.location IS NOT excluded.location
		OR teams.name IS NOT excluded.name
		OR teams.abbreviation IS NOT excluded.abbreviation
		OR teams.display_name IS NOT excluded.display_name
		OR teams.slug IS NOT excluded.slug
		OR teams.primary_color IS NOT excluded.primary_color
		OR teams.alternate_color IS NOT excluded.alternate_color
		OR teams.rank IS NOT excluded.rank;`

	var rowsAffected int64
	for _, team := range teams {
		resp, err := tx.ExecContext(
			ctx,
			query,
			team.Id,
			team.Location,
			team.Name,
			team.Abbreviation,
			team.DisplayName,
			team.Slug,
			team.PrimaryColor,
			team.AlternateColor,
			team.Rank,
		)
		if err != nil {
			return 0, fmt.Errorf("upsert team %q: %w", team.Id, err)
		}
		count, err := resp.RowsAffected()
		if err != nil {
			return 0, fmt.Errorf("count affected rows: %w", err)
		}
		rowsAffected += count
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit teams refresh: %w", err)
	}

	return rowsAffected, nil
}
