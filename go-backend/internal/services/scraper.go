package services

import (
	"fmt"
	"log"
	"time"

	"discogs-api/internal/config"
	"discogs-api/internal/models"
	"discogs-api/internal/scraper"
	"gorm.io/gorm"
)

// ScraperService handles scraping operations and database persistence
type ScraperService struct {
	db      *gorm.DB
	config  *config.Config
	scraper *scraper.Scraper
}

// NewScraperService creates a new scraper service
func NewScraperService(db *gorm.DB, cfg *config.Config) (*ScraperService, error) {
	scraperInstance, err := scraper.NewScraper(
		cfg.External.DiscogsConsumerKey,
		cfg.External.DiscogsConsumerSecret,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create scraper: %w", err)
	}

	return &ScraperService{
		db:      db,
		config:  cfg,
		scraper: scraperInstance,
	}, nil
}

// ScrapeUserInventory scrapes a user's inventory and saves to database
func (s *ScraperService) ScrapeUserInventory(username string) (*scraper.ScraperResult, error) {
	log.Printf("Starting scrape for user: %s", username)

	// Scrape the inventory
	result, err := s.scraper.GetInventory(username)
	if err != nil {
		return nil, fmt.Errorf("failed to scrape inventory: %w", err)
	}

	if !result.Success {
		return result, nil
	}

	// Save listings to database
	if err := s.saveListingsToDatabase(result.Listings); err != nil {
		log.Printf("Warning: failed to save some listings to database: %v", err)
		// Don't return error here, as scraping was successful
	}

	log.Printf("Successfully scraped %d listings for user %s", len(result.Listings), username)
	return result, nil
}

// saveListingsToDatabase saves parsed listings to the database
func (s *ScraperService) saveListingsToDatabase(listings []scraper.ParsedListing) error {
	for _, listing := range listings {
		if err := s.saveListing(listing); err != nil {
			log.Printf("Failed to save listing %d: %v", listing.DiscogsID, err)
			continue
		}
	}
	return nil
}

// saveListing saves a single listing to the database
func (s *ScraperService) saveListing(listing scraper.ParsedListing) error {
	// Start a transaction
	tx := s.db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	// Create or get the record
	record, err := s.createOrGetRecord(tx, listing)
	if err != nil {
		tx.Rollback()
		return fmt.Errorf("failed to create/get record: %w", err)
	}

	// Create or get the seller
	seller, err := s.createOrGetSeller(tx, listing.Seller, listing.Currency)
	if err != nil {
		tx.Rollback()
		return fmt.Errorf("failed to create/get seller: %w", err)
	}

	// Create the listing
	dbListing := models.Listing{
		SellerID:       seller.ID,
		RecordID:       record.ID,
		RecordPrice:    listing.RecordPrice,
		MediaCondition: listing.MediaCondition,
		Score:          0.0, // Will be calculated later
		Kept:           true, // Since we only save "keeper" listings
		Evaluated:      false,
		PredictedKeeper: false,
	}

	// Check if listing already exists
	var existingListing models.Listing
	result := tx.Where("seller_id = ? AND record_id = ? AND record_price = ? AND media_condition = ?",
		seller.ID, record.ID, listing.RecordPrice, listing.MediaCondition).First(&existingListing)

	if result.Error == gorm.ErrRecordNotFound {
		// Create new listing
		if err := tx.Create(&dbListing).Error; err != nil {
			tx.Rollback()
			return fmt.Errorf("failed to create listing: %w", err)
		}
	} else if result.Error != nil {
		tx.Rollback()
		return fmt.Errorf("failed to check existing listing: %w", result.Error)
	}
	// If listing exists, we don't need to do anything

	return tx.Commit().Error
}

// createOrGetRecord creates a new record or returns existing one
func (s *ScraperService) createOrGetRecord(tx *gorm.DB, listing scraper.ParsedListing) (*models.Record, error) {
	var record models.Record

	// Try to find existing record
	result := tx.Where("discogs_id = ?", fmt.Sprintf("%d", listing.DiscogsID)).First(&record)
	if result.Error == nil {
		// Update existing record with latest data
		record.Artist = listing.Artist
		record.Title = listing.Title
		record.Format = listing.Format
		record.Label = listing.Label
		record.Catno = &listing.Catno
		record.Wants = listing.Wants
		record.Haves = listing.Haves
		record.Genres = models.StringSlice(listing.Genres)
		record.Styles = models.StringSlice(listing.Styles)
		record.SuggestedPrice = listing.SuggestedPrice
		if listing.Year > 0 {
			record.Year = &listing.Year
		}

		if err := tx.Save(&record).Error; err != nil {
			return nil, fmt.Errorf("failed to update record: %w", err)
		}
		return &record, nil
	}

	if result.Error != gorm.ErrRecordNotFound {
		return nil, fmt.Errorf("failed to query record: %w", result.Error)
	}

	// Create new record
	record = models.Record{
		DiscogsID:      fmt.Sprintf("%d", listing.DiscogsID),
		Artist:         listing.Artist,
		Title:          listing.Title,
		Format:         listing.Format,
		Label:          listing.Label,
		Catno:          &listing.Catno,
		Wants:          listing.Wants,
		Haves:          listing.Haves,
		Added:          time.Now(),
		Genres:         models.StringSlice(listing.Genres),
		Styles:         models.StringSlice(listing.Styles),
		SuggestedPrice: listing.SuggestedPrice,
	}

	if listing.Year > 0 {
		record.Year = &listing.Year
	}

	if err := tx.Create(&record).Error; err != nil {
		return nil, fmt.Errorf("failed to create record: %w", err)
	}

	return &record, nil
}

// createOrGetSeller creates a new seller or returns existing one
func (s *ScraperService) createOrGetSeller(tx *gorm.DB, sellerName, currency string) (*models.Seller, error) {
	var seller models.Seller

	// Try to find existing seller
	result := tx.Where("name = ?", sellerName).First(&seller)
	if result.Error == nil {
		// Update currency if different
		if seller.Currency != currency {
			seller.Currency = currency
			if err := tx.Save(&seller).Error; err != nil {
				return nil, fmt.Errorf("failed to update seller: %w", err)
			}
		}
		return &seller, nil
	}

	if result.Error != gorm.ErrRecordNotFound {
		return nil, fmt.Errorf("failed to query seller: %w", result.Error)
	}

	// Create new seller
	seller = models.Seller{
		Name:     sellerName,
		Currency: currency,
	}

	if err := tx.Create(&seller).Error; err != nil {
		return nil, fmt.Errorf("failed to create seller: %w", err)
	}

	return &seller, nil
}

// GetScrapingStats returns statistics about the scraping process
func (s *ScraperService) GetScrapingStats() (map[string]interface{}, error) {
	var totalListings int64
	var totalRecords int64
	var totalSellers int64

	if err := s.db.Model(&models.Listing{}).Count(&totalListings).Error; err != nil {
		return nil, fmt.Errorf("failed to count listings: %w", err)
	}

	if err := s.db.Model(&models.Record{}).Count(&totalRecords).Error; err != nil {
		return nil, fmt.Errorf("failed to count records: %w", err)
	}

	if err := s.db.Model(&models.Seller{}).Count(&totalSellers).Error; err != nil {
		return nil, fmt.Errorf("failed to count sellers: %w", err)
	}

	// Get rate limiting info
	requests, sleepTime := s.scraper.GetRateInfo()

	stats := map[string]interface{}{
		"total_listings":     totalListings,
		"total_records":      totalRecords,
		"total_sellers":      totalSellers,
		"current_requests":   requests,
		"current_sleep_time": sleepTime.String(),
	}

	return stats, nil
}

// TestConnection tests the Discogs API connection
func (s *ScraperService) TestConnection() error {
	// Try to get a small inventory page to test connection
	testResult, err := s.scraper.GetInventory("discogs") // Use Discogs official account for testing
	if err != nil {
		return fmt.Errorf("connection test failed: %w", err)
	}

	if !testResult.Success {
		return fmt.Errorf("connection test failed: %s", testResult.Error)
	}

	return nil
}
