// Package espn contains all scraping logic related to data from ESPN's API and frontend.
package espn

import (
	"encoding/json"
	"fmt"
	"io"

	"github.com/landopritcho/basketball-bot/internal/date"
	"github.com/landopritcho/basketball-bot/internal/http"
)

const (
	scheduleUrl          string = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
	allTeamsGroup        string = "50"
	defaultResponseLimit string = "1000"
)

type ScheduleResponse struct {
	Events []Event `json:"events"`
}

type Event struct {
	Id                     string         `json:"id"`        // "401913099"
	Datetime               string         `json:"date"`      // "2026-11-03T00:00Z"
	LongDescription        string         `json:"name"`      // "Western Carolina Catamounts at North Carolina Tar Heels"
	AbbreviatedDescription string         `json:"shortName"` // "WCU @ UNC"
	Details                []EventDetails `json:"competitions"`
}

type EventDetails struct {
	Attendance       int          `json:"attendance"`            // 15735
	IsNeutralSite    bool         `json:"neutralSite"`           // false
	IsConferenceGame bool         `json:"conferenceCompetition"` // false
	Venue            VenueDetails `json:"venue"`
	Teams            []Team       `json:"competitors"`
	Note             []GameNote   `json:"notes"`
	Status           Status       `json:"status"`
	BroadcastChannel string       `json:"broadcast"` // "ACC Network"
}

type VenueDetails struct {
	Id      string `json:"id"`       // "207"
	Name    string `json:"fullName"` // "Dean E. Smith Center"
	Address struct {
		City  string `json:"city"`  // "Chapel Hill"
		State string `json:"state"` // "NC"
	} `json:"address"`
}

type Team struct {
	HomeAway        string           `json:"homeAway"` // "home"
	GameScore       string           `json:"score"`    // "80"
	GameScoreByHalf []ScoreBreakdown `json:"linescores"`
	Details         TeamDetails      `json:"team"`
	CuratedRank     CuratedRank      `json:"curatedRank"`
}

type ScoreBreakdown struct {
	DisplayValue string `json:"displayValue"` // "41"
	Period       int    `json:"period"`       // 2
}

type TeamDetails struct {
	Id               string `json:"id"`               // "153"
	Location         string `json:"location"`         // "North Carolina"
	Name             string `json:"name"`             // "Tar Heels"
	Abbreviation     string `json:"abbreviation"`     // "UNC"
	DisplayName      string `json:"displayName"`      // "North Carolina Tar Heels"
	ShortDisplayName string `json:"shortDisplayName"` // "North Carolina"
	PrimaryColor     string `json:"color"`            // "7bafd4"
	AlternateColor   string `json:"alternateColor"`   // "13294b"
	ConferenceId     string `json:"conferenceId"`     // "2"
}

type CuratedRank struct {
	Rank int `json:"current"` // 99
}

type GameNote struct {
	Type     string `json:"type"`     // "event"
	Headline string `json:"headline"` // "Orion180 Tipoff Classic"
}

type Status struct {
	DisplayClock string        `json:"displayClock"` // "0:00"
	Period       int           `json:"period"`       // 2
	Details      StatusDetails `json:"type"`
}

type StatusDetails struct {
	Name        string `json:"name"`        // "STATUS_FINAL"
	State       string `json:"state"`       // "post"
	IsCompleted bool   `json:"completed"`   // true
	Description string `json:"description"` // "Final"
	Detail      string `json:"detail"`      // "Final"
	ShortDetail string `json:"shortDetail"` // "Final"
}

func GetAllGamesForDate(client http.ScrapingClient, date string) ([]Event, error) {
	urlArguments := fmt.Sprintf("?dates=%s&groups=%s&limit=%s", date, allTeamsGroup, defaultResponseLimit)
	useUserAgent := false
	resp, err := client.Scrape(scheduleUrl+urlArguments, &useUserAgent)
	if err != nil {
		return []Event{}, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return []Event{}, err
	}

	var gamesResponse ScheduleResponse
	err = json.Unmarshal(body, &gamesResponse)
	if err != nil {
		return []Event{}, err
	}

	return gamesResponse.Events, nil
}

type ScheduledGame struct {
	Id                     string // "401913099"
	Datetime               string // "Nov 2, 2026 6:00 PM CST"
	LongDescription        string // "Western Carolina Catamonuts at North Carolina Tar Heels"
	AbbreviatedDescription string // "WCU @ UNC"
	Venue                  string // "Dean E. Smith Center"
	Title                  string // "Orion180 Tipoff Classic"
	BroadcastChannel       string // "ACC Network"
}

func GetUpcomingDaySchedule(client http.ScrapingClient) ([]ScheduledGame, error) {
	upcomingDayCondensedDate := date.GetTomorrowsCondensedDate()
	upcomingDayGames, err := GetAllGamesForDate(client, upcomingDayCondensedDate)
	if err != nil {
		return nil, err
	}

	var scheduledGames []ScheduledGame
	for _, game := range upcomingDayGames {
		convertedDatetime, err := date.ConvertUTCDatetimeToCentralDatetime(game.Datetime)
		if err != nil {
			return nil, err
		}
		gameDetails := game.Details[0]
		title := ""
		if len(gameDetails.Note) == 0 {
			title = ""
		}
		scheduledGames = append(scheduledGames, ScheduledGame{
			Id:                     game.Id,
			Datetime:               convertedDatetime,
			LongDescription:        game.LongDescription,
			AbbreviatedDescription: game.AbbreviatedDescription,
			Venue:                  gameDetails.Venue.Name,
			Title:                  title,
			BroadcastChannel:       gameDetails.BroadcastChannel,
		})
	}
	return scheduledGames, nil
}
