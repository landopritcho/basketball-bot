// Package fetch allows clients to retrieve data.
package fetch

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/landopritcho/basketball-bot/internal/fetch/team"
)

// FetchTeams returns a list of all active Division 1 Men's NCAA basketball schools (active as of the current season).
func FetchTeams() ([]team.Team, error) {
	var teamResponse team.EspnTeamResponse

	response, err := http.Get(team.EspnTeamUrl())
	if err != nil {
		return []team.Team{}, err
	}
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		return []team.Team{}, err
	}

	err = json.Unmarshal(body, &teamResponse)
	if err != nil {
		return []team.Team{}, err
	}

	teams := teamResponse.Sports[0].Leagues[0].Teams
	teamList := make([]team.Team, len(teams))

	for i, team := range teams {
		teamList[i] = team.Team
	}

	return teamList, nil
}
