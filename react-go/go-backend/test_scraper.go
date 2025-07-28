package main

import (
	"fmt"
	"log"

	"discogs-api/internal/scraper"
)

func main() {
	// Test with placeholder keys (these won't work but will show if initialization works)
	consumerKey := "your_discogs_consumer_key_here"
	consumerSecret := "your_discogs_consumer_secret_here"
	
	scraperInstance, err := scraper.NewScraper(consumerKey, consumerSecret)
	if err != nil {
		log.Fatalf("Failed to create scraper: %v", err)
	}
	
	fmt.Println("Scraper created successfully!")
	// Test a simple API call
	result, err := scraperInstance.GetInventory("discogs") // Use official Discogs account for testing
	if err != nil {
		log.Printf("Failed to get inventory: %v", err)
	} else {
		fmt.Printf("Successfully got %d listings\n", len(result.Listings))
	}
}
