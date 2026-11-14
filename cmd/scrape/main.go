package main

import (
	"context"
	"fmt"

	"github.com/landopritcho/basketball-bot/internal/db"
)

// func main() {
// 	client := http.NewClient()
// 	team, err := espn.GetNonD1Team(client, "2027", "131625")
// 	if err != nil {
// 		fmt.Printf("error: %w", err)
// 	}
// 	fmt.Printf("Team Name: %s", team.DisplayName)
// }

func main() {
	database, _ := db.New("./basketball.db")
	ctx := context.Background()

	teams, err := db.GetTeams(ctx, database.DB)
	if err != nil {
		fmt.Printf("error: %w", err)
	}

	fmt.Printf("teams: %d", len(teams))
}
