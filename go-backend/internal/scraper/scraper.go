package scraper

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"strings"
	"time"

	"github.com/dghubble/oauth1"
)

// Scraper handles Discogs inventory scraping with concurrent processing
type Scraper struct {
	config      *ScraperConfig
	oauthConfig *oauth1.Config
	token       *oauth1.Token
	httpClient  *http.Client
	rateLimiter *RateLimitTracker
}

// NewScraper creates a new scraper instance
func NewScraper(consumerKey, consumerSecret string) (*Scraper, error) {
	config := &ScraperConfig{
		ConsumerKey:    consumerKey,
		ConsumerSecret: consumerSecret,
		MaxPages:       5, // Reduced for debugging
		PerPage:        100,
		BaseURL:        "https://api.discogs.com",
		UserAgent:      "wantlist/1.0",
	}

	oauthConfig, token, err := AuthenticateClient(consumerKey, consumerSecret)
	if err != nil {
		return nil, fmt.Errorf("failed to authenticate: %w", err)
	}

	httpClient := oauthConfig.Client(oauth1.NoContext, token)
	httpClient.Timeout = 30 * time.Second

	return &Scraper{
		config:      config,
		oauthConfig: oauthConfig,
		token:       token,
		httpClient:  httpClient,
		rateLimiter: NewRateLimitTracker(),
	}, nil
}

// GetInventory scrapes a user's inventory with concurrent processing
func (s *Scraper) GetInventory(username string) (*ScraperResult, error) {
	log.Printf("=== Starting inventory fetch for %s ===", username)

	// Load previous inventory data
	previousInventory, err := GetUserInventory(username)
	if err != nil {
		return nil, fmt.Errorf("failed to load previous inventory: %w", err)
	}

	previousIDs := make(map[int]bool)
	for _, id := range previousInventory.RecordIDs {
		previousIDs[id] = true
	}

	log.Printf("Found %d previous records for %s", len(previousIDs), username)

	// Get total pages
	totalPages, err := s.getTotalPages(username)
	if err != nil {
		return nil, fmt.Errorf("failed to get total pages: %w", err)
	}

	maxPages := totalPages
	if maxPages > s.config.MaxPages {
		maxPages = s.config.MaxPages
	}

	log.Printf("Will process %d pages (total: %d)", maxPages, totalPages)

	// Process pages sequentially to avoid rate limits and 404s
	// const maxConcurrency = 1 // Disable concurrency for debugging
	// semaphore := make(chan struct{}, maxConcurrency)
	
	var allListings []ParsedListing
	var currentIDs []int

	// Process pages sequentially from page 1 to avoid 404s and rate limits
	for page := 1; page <= maxPages; page++ {
		log.Printf("Processing page %d of %d", page, maxPages)
		
		pageListings, pageIDs, shouldStop, err := s.processPage(username, page, previousIDs)
		if err != nil {
			log.Printf("Error processing page %d: %v", page, err)
			// Continue to next page instead of stopping
			continue
		}

		if shouldStop {
			log.Printf("Found previously seen record on page %d, stopping", page)
			break
		}
		
		allListings = append(allListings, pageListings...)
		currentIDs = append(currentIDs, pageIDs...)
		log.Printf("Processed page %d: %d listings, total so far: %d", page, len(pageListings), len(allListings))
		
		// Add delay between pages to respect rate limits
		time.Sleep(1 * time.Second)
	}

	// Update inventory tracking
	if err := UpdateUserInventory(username, currentIDs); err != nil {
		log.Printf("Warning: failed to update inventory: %v", err)
	}

	result := &ScraperResult{
		Username:     username,
		TotalRecords: len(allListings),
		NewRecords:   len(allListings),
		Listings:     allListings,
		Success:      true,
	}

	log.Printf("=== Finished fetching inventory for %s, total records: %d ===", username, len(allListings))
	return result, nil
}

// processPage processes a single page of inventory
func (s *Scraper) processPage(username string, page int, previousIDs map[int]bool) ([]ParsedListing, []int, bool, error) {
	// Apply rate limiting
	s.rateLimiter.AddRequest(fmt.Sprintf("inventory_page_%d", page))
	s.rateLimiter.Sleep()

	url := fmt.Sprintf("%s/users/%s/inventory?page=%d&per_page=%d", 
		s.config.BaseURL, username, page, s.config.PerPage)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, nil, false, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", s.config.UserAgent)

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, nil, false, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, nil, false, fmt.Errorf("API returned status %d", resp.StatusCode)
	}

	var inventoryResp DiscogsInventoryResponse
	if err := json.NewDecoder(resp.Body).Decode(&inventoryResp); err != nil {
		return nil, nil, false, fmt.Errorf("failed to decode response: %w", err)
	}

	var pageListings []ParsedListing
	var pageIDs []int
	shouldStop := false

	log.Printf("=== Processing page %d for %s: %d listings found ===", page, username, len(inventoryResp.Listings))

	for i, listing := range inventoryResp.Listings {
		log.Printf("Processing listing %d/%d on page %d", i+1, len(inventoryResp.Listings), page)
		
		// Check if we've seen this record before
		if previousIDs[listing.Release.ID] {
			shouldStop = true
			log.Printf("Found previously seen record %d, stopping", listing.Release.ID)
			break
		}

		pageIDs = append(pageIDs, listing.Release.ID)

		// Check if this is a "keeper" (LP, good condition, wanted > haves)
		if s.isKeeper(listing) {
			parsed, err := s.parseListing(listing)
			if err != nil {
				log.Printf("Warning: failed to parse listing %d: %v", listing.ID, err)
				continue
			}
			pageListings = append(pageListings, *parsed)
		}
	}

	log.Printf("=== Page %d complete: %d keepers found out of %d total listings ===", page, len(pageListings), len(inventoryResp.Listings))

	return pageListings, pageIDs, shouldStop, nil
}

// getTotalPages gets the total number of pages for a user's inventory
func (s *Scraper) getTotalPages(username string) (int, error) {
	s.rateLimiter.AddRequest("inventory_total_pages")
	s.rateLimiter.Sleep()

	url := fmt.Sprintf("%s/users/%s/inventory?page=1&per_page=1", s.config.BaseURL, username)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return 0, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", s.config.UserAgent)

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return 0, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("API returned status %d", resp.StatusCode)
	}

	var inventoryResp DiscogsInventoryResponse
	if err := json.NewDecoder(resp.Body).Decode(&inventoryResp); err != nil {
		return 0, fmt.Errorf("failed to decode response: %w", err)
	}

	return inventoryResp.Pagination.Pages, nil
}

// Helper function to convert interface{} to []string
func interfaceToStringSlice(data interface{}) []string {
	if data == nil {
		return []string{}
	}
	
	switch v := data.(type) {
	case string:
		return []string{v}
	case []string:
		return v
	case []interface{}:
		result := make([]string, len(v))
		for i, item := range v {
			if str, ok := item.(string); ok {
				result[i] = str
			}
		}
		return result
	default:
		return []string{}
	}
}

// isKeeper determines if a listing meets the "keeper" criteria
func (s *Scraper) isKeeper(listing DiscogsListing) bool {
	log.Printf("=== DEBUG: Checking listing %d ===", listing.Release.ID)
	log.Printf("Artist: %s", listing.Release.Artist)
	log.Printf("Title: %s", listing.Release.Title)
	log.Printf("Formats: %v", listing.Release.Format)
	log.Printf("Condition: %s", listing.Condition)
	log.Printf("Wants: %d, Haves: %d", listing.Release.Stats.Community.InWantlist, listing.Release.Stats.Community.InCollection)
	
	// Convert format to string slice
	formats := interfaceToStringSlice(listing.Release.Format)
	log.Printf("Parsed formats: %v", formats)
	
	// Check LP format
	isLP := false
	for _, format := range formats {
		if strings.Contains(format, "LP") {
			isLP = true
			break
		}
	}
	log.Printf("Is LP: %v", isLP)
	if !isLP {
		log.Printf("REJECTED: Not LP format")
		return false
	}

	// Check condition
	goodConditions := map[string]bool{
		"Near Mint (NM or M-)": true,
		"Very Good Plus (VG+)": true,
		"Very Good (VG)":       true,
		"Good Plus (G+)":       true,
	}
	isGoodCondition := goodConditions[listing.Condition]
	log.Printf("Is good condition: %v", isGoodCondition)
	if !isGoodCondition {
		log.Printf("REJECTED: Poor condition (%s)", listing.Condition)
		return false
	}

	// Check wants vs haves
	wantsGreaterThanHaves := listing.Release.Stats.Community.InWantlist > listing.Release.Stats.Community.InCollection
	log.Printf("Wants > Haves: %v", wantsGreaterThanHaves)
	if !wantsGreaterThanHaves {
		log.Printf("REJECTED: Wants (%d) not greater than haves (%d)", 
			listing.Release.Stats.Community.InWantlist, listing.Release.Stats.Community.InCollection)
		return false
	}

	log.Printf("ACCEPTED: All criteria met")
	return true
}

// parseListing converts a Discogs listing to our internal format
func (s *Scraper) parseListing(listing DiscogsListing) (*ParsedListing, error) {
	// Add small delay to avoid overwhelming the API
	time.Sleep(time.Duration(rand.Intn(500)+500) * time.Millisecond)

	// Get suggested price if available
	suggestedPrice := ""
	if listing.Release.PriceSuggestions != nil && listing.Release.PriceSuggestions.VeryGoodPlus != nil {
		suggestedPrice = fmt.Sprintf("%.2f %s", 
			listing.Release.PriceSuggestions.VeryGoodPlus.Value,
			listing.Release.PriceSuggestions.VeryGoodPlus.Currency)
	}

	// Convert interface{} fields to string slices
	labels := interfaceToStringSlice(listing.Release.Label)
	genres := interfaceToStringSlice(listing.Release.Genres)
	styles := interfaceToStringSlice(listing.Release.Styles)

	// Join labels into a single string
	label := ""
	if len(labels) > 0 {
		label = strings.Join(labels, ", ")
	}

	return &ParsedListing{
		DiscogsID:       listing.Release.ID,
		MediaCondition:  listing.Condition,
		RecordPrice:     listing.Price.Value,
		Currency:        listing.Price.Currency,
		Seller:          listing.Seller.Username,
		Artist:          listing.Release.Artist,
		Title:           listing.Release.Title,
		Format:          "LP",
		Label:           label,
		Catno:           listing.Release.CatalogNumber,
		Wants:           listing.Release.Stats.Community.InWantlist,
		Haves:           listing.Release.Stats.Community.InCollection,
		Genres:          genres,
		Styles:          styles,
		Year:            listing.Release.Year,
		SuggestedPrice:  suggestedPrice,
		ScrapedAt:       time.Now(),
	}, nil
}

// GetRateInfo returns current rate limiting information
func (s *Scraper) GetRateInfo() (int, time.Duration) {
	return s.rateLimiter.GetCurrentRate()
}
