package main

import (
	"context"
	"log"

	"github.com/landopritcho/basketball-bot/internal/db"
)

func main() {
	database, err := db.New("./basketball.db")
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	ctx := context.Background()
	if err := db.Migrate(ctx, database, "./migrations"); err != nil {
		log.Fatalf("migrate database: %v", err)
	}
}
