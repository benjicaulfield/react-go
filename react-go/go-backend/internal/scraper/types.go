package scraper

import (
	"time"
)

// DiscogsListing represents a listing from the Discogs API
type DiscogsListing struct {
	ID        int                    `json:"id"`
	Price     DiscogsPrice          `json:"price"`
	Condition string                `json:"condition"`
	Seller    DiscogsSeller         `json:"seller"`
	Release   DiscogsRelease        `json:"release"`
	URI       string                `json:"uri"`
	Status    string                `json:"status"`
}

// DiscogsPrice represents price information
type DiscogsPrice struct {
	Value    float64 `json:"value"`
	Currency string  `json:"currency"`
}

// DiscogsSeller represents seller information
type DiscogsSeller struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	URI      string `json:"uri"`
}

// DiscogsRelease represents release information
type DiscogsRelease struct {
	ID             int                    `json:"id"`
	Title          string                 `json:"title"`
	Artist         string                 `json:"artist"`
	Year           int                    `json:"year"`
	Format         interface{}            `json:"format"` // Can be string or []string
	Label          interface{}            `json:"label"`  // Can be string or []string
	CatalogNumber  string                 `json:"catno"`
	Genres         interface{}            `json:"genre"`  // Can be string or []string
	Styles         interface{}            `json:"style"`  // Can be string or []string
	Stats          DiscogsStats           `json:"stats"`
	PriceSuggestions *DiscogsPriceSuggestions `json:"price_suggestions,omitempty"`
	URI            string                 `json:"uri"`
}

// DiscogsStats represents community statistics
type DiscogsStats struct {
	Community DiscogsCommunityStats `json:"community"`
}

// DiscogsCommunityStats represents community want/have statistics
type DiscogsCommunityStats struct {
	InWantlist   int `json:"in_wantlist"`
	InCollection int `json:"in_collection"`
}

// DiscogsPriceSuggestions represents price suggestions
type DiscogsPriceSuggestions struct {
	VeryGoodPlus *DiscogsPrice `json:"Very Good Plus (VG+)"`
	NearMint     *DiscogsPrice `json:"Near Mint (NM or M-)"`
}

// DiscogsInventoryResponse represents the API response for inventory
type DiscogsInventoryResponse struct {
	Listings   []DiscogsListing `json:"listings"`
	Pagination DiscogsPagination `json:"pagination"`
}

// DiscogsPagination represents pagination information
type DiscogsPagination struct {
	Page    int                `json:"page"`
	Pages   int                `json:"pages"`
	PerPage int                `json:"per_page"`
	Items   int                `json:"items"`
	URLs    DiscogsPaginationURLs `json:"urls"`
}

// DiscogsPaginationURLs represents pagination URLs
type DiscogsPaginationURLs struct {
	Last string `json:"last,omitempty"`
	Next string `json:"next,omitempty"`
	Prev string `json:"prev,omitempty"`
	First string `json:"first,omitempty"`
}

// ParsedListing represents a processed listing ready for database storage
type ParsedListing struct {
	DiscogsID       int       `json:"discogs_id"`
	MediaCondition  string    `json:"media_condition"`
	RecordPrice     float64   `json:"record_price"`
	Currency        string    `json:"currency"`
	Seller          string    `json:"seller"`
	Artist          string    `json:"artist"`
	Title           string    `json:"title"`
	Format          string    `json:"format"`
	Label           string    `json:"label"`
	Catno           string    `json:"catno"`
	Wants           int       `json:"wants"`
	Haves           int       `json:"haves"`
	Genres          []string  `json:"genres"`
	Styles          []string  `json:"styles"`
	Year            int       `json:"year"`
	SuggestedPrice  string    `json:"suggested_price"`
	ScrapedAt       time.Time `json:"scraped_at"`
}

// UserInventoryData represents stored inventory data for a user
type UserInventoryData struct {
	LastInventory string `json:"last_inventory"`
	RecordIDs     []int  `json:"record_ids"`
}


// ScraperConfig holds configuration for the scraper
type ScraperConfig struct {
	ConsumerKey    string
	ConsumerSecret string
	MaxPages       int
	PerPage        int
	BaseURL        string
	UserAgent      string
}

// ScraperResult represents the result of a scraping operation
type ScraperResult struct {
	Username      string          `json:"username"`
	TotalRecords  int             `json:"total_records"`
	NewRecords    int             `json:"new_records"`
	Listings      []ParsedListing `json:"listings"`
	Error         string          `json:"error,omitempty"`
	Success       bool            `json:"success"`
}
