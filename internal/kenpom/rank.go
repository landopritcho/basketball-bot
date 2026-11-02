// Package kenpom grabs rankings from Kenpom.com.
package kenpom

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"

	"github.com/landopritcho/basketball-bot/internal/http"
)

const (
	kenpomBaseUrl                = "https://kenpom.com"
	ratingsTableId               = "ratings-table"
	ratingsTableOverallRankClass = "hard_left"
	ratingsTableTeamClass        = "next_left"
)

type KenpomRank struct {
	Team            string
	OverallRating   float32
	OverallRank     int
	OffensiveRating float32
	OffensiveRank   int
	DefensiveRating float32
	DefensiveRank   int
}

func FetchKenpomRank(client http.ScrapingClient) ([]KenpomRank, error) {
	resp, err := client.Scrape(kenpomBaseUrl)
	if err != nil {
		return []KenpomRank{}, err
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return []KenpomRank{}, err
	}

	var teams []KenpomRank

	doc.Find(fmt.Sprintf("#%s tbody tr", ratingsTableId)).Each(func(_ int, row *goquery.Selection) {
		cells := row.ChildrenFiltered("td")
		overallRank, _ := strconv.Atoi(strings.TrimSpace(cells.Eq(0).Text()))
		team := strings.TrimSpace(cells.Eq(1).Text())
		overallRating, _ := strconv.ParseFloat(strings.TrimSpace(cells.Eq(4).Text()), 32)
		offensiveRating, _ := strconv.ParseFloat(strings.TrimSpace(cells.Eq(5).Text()), 32)
		offensiveRank, _ := strconv.Atoi(strings.TrimSpace(cells.Eq(6).Text()))
		defensiveRating, _ := strconv.ParseFloat(strings.TrimSpace(cells.Eq(7).Text()), 32)
		defensiveRank, _ := strconv.Atoi(strings.TrimSpace(cells.Eq(8).Text()))

		teams = append(teams, KenpomRank{
			Team:            team,
			OverallRating:   float32(overallRating),
			OverallRank:     overallRank,
			OffensiveRating: float32(offensiveRating),
			OffensiveRank:   offensiveRank,
			DefensiveRating: float32(defensiveRating),
			DefensiveRank:   defensiveRank,
		})
	})

	return teams, nil
}
