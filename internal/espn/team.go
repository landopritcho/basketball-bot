package espn

import (
	"encoding/json"
	"fmt"
	"io"

	"github.com/landopritcho/basketball-bot/internal/http"
)

const (
	teamsUrl string = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
)

type TeamsResponse struct {
	Sports []Sport `json:"sports"`
}

type Sport struct {
	Leagues []League `json:"leagues"`
}

type League struct {
	Teams []IntermediateTeam `json:"teams"`
}

type IntermediateTeam struct {
	Team InternalTeam `json:"team"`
}

type InternalTeam struct {
	Id               string `json:"id"`
	Abbreviation     string `json:"abbreviation"`
	DisplayName      string `json:"displayName"`
	ShortDisplayName string `json:"shortDisplayName"`
	SchoolName       string `json:"location"`
	TeamName         string `json:"name"`
	Nickname         string `json:"nickname"`
	PrimaryColor     string `json:"color"`
	AlternateColor   string `json:"alternateColor"`
	InternalSlug     string `json:"slug"`
}

func GetAllTeams(client http.ScrapingClient) ([]InternalTeam, error) {
	urlArguments := fmt.Sprintf("?groups=%s&limit=%s", allTeamsGroup, defaultResponseLimit)
	useUserAgent := false
	resp, err := client.Scrape(teamsUrl+urlArguments, &useUserAgent)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var teamsResponse TeamsResponse
	err = json.Unmarshal(body, &teamsResponse)
	if err != nil {
		return nil, err
	}

	var teamList []InternalTeam
	for _, team := range teamsResponse.Sports[0].Leagues[0].Teams {
		teamList = append(teamList, team.Team)
	}

	return teamList, nil
}
