package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"discogs-api/internal/config"
	"discogs-api/internal/database"
	"discogs-api/internal/services"

	"github.com/joho/godotenv"
)

func main() {
	// Command line flags
	var (
		username = flag.String("user", "", "Discogs username to scrape")
		test     = flag.Bool("test", false, "Test connection to Discogs API")
		stats    = flag.Bool("stats", false, "Show scraper statistics")
	)
	flag.Parse()

	// Load environment variables
	if err := godotenv.Load("../../.env"); err != nil {
		log.Println("Warning: .env file not found, using system environment variables")
	}

	// Initialize configuration
	cfg := config.Load()

	// Check if required environment variables are set
	if cfg.External.DiscogsConsumerKey == "" || cfg.External.DiscogsConsumerSecret == "" {
		log.Fatal("DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET must be set in environment variables")
	}

	// Initialize database (optional for CLI tool)
	var scraperService *services.ScraperService
	if !*test {
		db, err := database.Initialize(cfg.Database)
		if err != nil {
			log.Printf("Warning: Failed to initialize database: %v", err)
			log.Println("Running without database persistence")
		} else {
			scraperService, err = services.NewScraperService(db, cfg)
			if err != nil {
				log.Fatal("Failed to initialize scraper service:", err)
			}
		}
	}

	// Handle different commands
	switch {
	case *test:
		testConnection(cfg)
	case *stats:
		showStats(scraperService)
	case *username != "":
		scrapeUser(*username, scraperService)
	default:
		fmt.Println("Discogs Go Scraper CLI")
		fmt.Println("Usage:")
		fmt.Println("  -user <username>  Scrape a user's inventory")
		fmt.Println("  -test             Test connection to Discogs API")
		fmt.Println("  -stats            Show scraper statistics")
		fmt.Println()
		fmt.Println("Examples:")
		fmt.Println("  go run main.go -test")
		fmt.Println("  go run main.go -user someuser")
		fmt.Println("  go run main.go -stats")
	}
}

func testConnection(cfg *config.Config) {
	fmt.Println("Testing connection to Discogs API...")
	
	// Create a temporary scraper service without database
	scraperService, err := services.NewScraperService(nil, cfg)
	if err != nil {
		log.Fatal("Failed to create scraper service:", err)
	}

	if err := scraperService.TestConnection(); err != nil {
		fmt.Printf("❌ Connection test failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("✅ Connection to Discogs API successful!")
}

func showStats(scraperService *services.ScraperService) {
	if scraperService == nil {
		log.Fatal("Database connection required for stats")
	}

	fmt.Println("Fetching scraper statistics...")
	
	stats, err := scraperService.GetScrapingStats()
	if err != nil {
		log.Fatal("Failed to get stats:", err)
	}

	fmt.Println("\n📊 Scraper Statistics:")
	fmt.Printf("  Total Listings: %v\n", stats["total_listings"])
	fmt.Printf("  Total Records: %v\n", stats["total_records"])
	fmt.Printf("  Total Sellers: %v\n", stats["total_sellers"])
	fmt.Printf("  Current Requests: %v\n", stats["current_requests"])
	fmt.Printf("  Current Sleep Time: %v\n", stats["current_sleep_time"])
}

func scrapeUser(username string, scraperService *services.ScraperService) {
	if scraperService == nil {
		log.Fatal("Database connection required for scraping")
	}

	fmt.Printf("🎵 Starting scrape for user: %s\n", username)
	fmt.Println("This may take several minutes depending on inventory size...")
	
	result, err := scraperService.ScrapeUserInventory(username)
	if err != nil {
		log.Fatal("Scraping failed:", err)
	}

	if !result.Success {
		log.Fatal("Scraping failed:", result.Error)
	}

	fmt.Println("\n✅ Scraping completed successfully!")
	fmt.Printf("  Username: %s\n", result.Username)
	fmt.Printf("  Total Records Found: %d\n", result.TotalRecords)
	fmt.Printf("  New Records: %d\n", result.NewRecords)
	
	if len(result.Listings) > 0 {
		fmt.Println("\n🎯 Sample of scraped listings:")
		for i, listing := range result.Listings {
			if i >= 5 { // Show only first 5
				break
			}
			fmt.Printf("  • %s - %s (%s) - $%.2f\n", 
				listing.Artist, listing.Title, listing.MediaCondition, listing.RecordPrice)
		}
		if len(result.Listings) > 5 {
			fmt.Printf("  ... and %d more listings\n", len(result.Listings)-5)
		}
	}
}
