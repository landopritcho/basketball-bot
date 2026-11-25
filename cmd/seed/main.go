package main

import (
	"context"
	"fmt"
	"log"
	"slices"
	"strconv"
	"time"

	"github.com/landopritcho/basketball-bot/internal/date"
	"github.com/landopritcho/basketball-bot/internal/db"
	"github.com/landopritcho/basketball-bot/internal/espn"
	"github.com/landopritcho/basketball-bot/internal/http"
)

func main() {
	ctx := context.Background()
	database, err := db.New("./basketball.db")
	if err != nil {
		log.Panic()
	}
	client := http.NewClient()

	teams, err := espn.GetAllTeams(client)
	if err != nil {
		log.Panic()
	}

	var formattedTeams []db.Team
	var teamIds []string
	for _, team := range teams {
		formattedTeams = append(formattedTeams, db.Team{
			Id:             team.Id,
			Location:       team.SchoolName,
			Name:           team.TeamName,
			Abbreviation:   team.Abbreviation,
			DisplayName:    team.DisplayName,
			Slug:           team.InternalSlug,
			PrimaryColor:   team.PrimaryColor,
			AlternateColor: team.AlternateColor,
			Rank:           nil,
		})
		teamIds = append(teamIds, team.Id)
	}
	count, err := db.UpsertTeams(ctx, database.DB, formattedTeams)
	if err != nil {
		fmt.Printf("error: %w", err)
	}
	fmt.Printf("upserted %d teams\n", count)

	games, err := espn.GetUpcomingDaySchedule(client)
	if err != nil {
		log.Panic()
	}

	var formattedGames []db.UpcomingGame
	var nonD1TeamIds []string
	for _, game := range games {
		tipoff, _ := date.ConvertCentralDatetimeToUnix(game.Datetime)
		homeTeamId, _ := strconv.Atoi(game.HomeTeam.Details.Id)
		awayTeamId, _ := strconv.Atoi(game.AwayTeam.Details.Id)
		formattedGames = append(formattedGames, db.UpcomingGame{
			Id:                     game.Id,
			Tipoff:                 tipoff,
			LongDescription:        game.LongDescription,
			AbbreviatedDescription: game.AbbreviatedDescription,
			Venue:                  game.Venue,
			Title:                  game.Title,
			BroadcastChannel:       game.BroadcastChannel,
			HomeTeamId:             homeTeamId,
			AwayTeamId:             awayTeamId,
		})

		if !slices.Contains(teamIds, game.HomeTeam.Details.Id) {
			nonD1TeamIds = append(nonD1TeamIds, game.HomeTeam.Details.Id)
		}
		if !slices.Contains(teamIds, game.AwayTeam.Details.Id) {
			nonD1TeamIds = append(nonD1TeamIds, game.AwayTeam.Details.Id)
		}
	}
	count, err = db.UpdateUpcomingGames(ctx, database.DB, formattedGames)
	if err != nil {
		fmt.Printf("error: %w", err)
	}
	fmt.Printf("updated %d games\n", count)

	var nonD1Teams []db.Team
	for _, id := range nonD1TeamIds {
		team, err := espn.GetNonD1Team(client, "2027", id)
		if err != nil {
			fmt.Printf("scraping non d1 team details: %w", err)
		}
		primaryColor := ""
		alternateColor := ""
		if team.PrimaryColor == "000000" {
			primaryColor = ""
			alternateColor = ""
		} else {
			primaryColor = team.PrimaryColor
			alternateColor = team.AlternateColor
		}
		nonD1Teams = append(nonD1Teams, db.Team{
			Id:             team.Id,
			Location:       team.SchoolName,
			Name:           team.TeamName,
			Abbreviation:   team.Abbreviation,
			DisplayName:    team.DisplayName,
			Slug:           team.InternalSlug,
			PrimaryColor:   primaryColor,
			AlternateColor: alternateColor,
			Rank:           nil,
		})
		fmt.Printf("adding %s (non D1 team)\n", team.SchoolName)
		time.Sleep(1 * time.Second)
	}
	count, err = db.UpsertTeams(ctx, database.DB, nonD1Teams)
	if err != nil {
		fmt.Printf("error: %w", err)
	}
	fmt.Printf("upserted %d non D1-teams\n", count)

	liveGames, err := espn.GetCurrentLiveGames(client)
	if err != nil {
		log.Panic()
	}

	var formattedLiveGames []db.LiveGame
	for _, game := range liveGames {
		homeTeamId, _ := strconv.Atoi(game.HomeTeam.Details.Id)
		awayTeamId, _ := strconv.Atoi(game.AwayTeam.Details.Id)
		homeTeamScore, _ := strconv.Atoi(game.HomeTeam.GameScore)
		awayTeamScore, _ := strconv.Atoi(game.AwayTeam.GameScore)
		half := strconv.Itoa(game.Status.Period)
		formattedLiveGames = append(formattedLiveGames, db.LiveGame{
			Id:                game.Id,
			Venue:             game.Venue,
			Title:             game.Title,
			BroadcastChannel:  game.BroadcastChannel,
			HomeTeamId:        homeTeamId,
			AwayTeamId:        awayTeamId,
			HomeTeamScore:     homeTeamScore,
			AwayTeamScore:     awayTeamScore,
			DisplayClock:      game.Status.DisplayClock,
			Half:              half,
			StatusDescription: game.Status.Details.Description,
			StatusDetail:      game.Status.Details.Detail,
			StatusShortDetail: game.Status.Details.ShortDetail,
		})
	}
	count, err = db.UpdateLiveGames(ctx, database.DB, formattedLiveGames)
	if err != nil {
		fmt.Printf("error: %w", err)
	}
	fmt.Printf("updated %d live games\n", count)
}
