// Package team provides access to team data scraped from ESPN.
package team

const espnTeamBaseUrl = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
const espnTeamUrlDefaultLimit = "1000"
const espnTeamUrlDefaultGroups = "50"

func EspnTeamUrl() string {
	return espnTeamBaseUrl + "?limit=" + espnTeamUrlDefaultLimit + "&groups=" + espnTeamUrlDefaultGroups
}

type EspnTeamResponse struct {
	Sports []struct {
		Leagues []struct {
			Season struct {
				DisplayName string `json:"displayName"`
				Year        int    `json:"year"`
			} `json:"season"`
			Teams []struct {
				Team Team `json:"team"`
			} `json:"teams"`
		} `json:"leagues"`
	} `json:"sports"`
}

// Team is the primary container for relevant team information
type Team struct {
	// Ex: "153"
	Id string `json:"id"`
	// Ex: "UNC"
	Abbreviation string `json:"abbreviation"`
	// Ex: "13294b"
	PrimaryColor string `json:"color"`
	// Ex: "7bafd4"
	AlternateColor string `json:"alternateColor"`
	// Ex: "North Carolina Tar Heels"
	DisplayName string `json:"displayName"`
	// Ex: "North Carolina"
	ShortDisplayName string `json:"shortDisplayName"`
	// Ex: "North Carolina"
	SchoolName string `json:"location"`
	// Ex: "Tar Heels"
	TeamName string `json:"name"`
	// Ex: "North Carolina"
	Nickname string `json:"nickname"`
	// Ex: "north-carolina-tar-heels"
	EspnInternalSlug string `json:"slug"`
}
