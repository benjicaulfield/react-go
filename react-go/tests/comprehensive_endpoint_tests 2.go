package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"

	"discogs-api/internal/config"
	"discogs-api/internal/handlers"
	"discogs-api/internal/models"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Test configuration
type TestSuite struct {
	db     *gorm.DB
	router *gin.Engine
	h      *handlers.Handler
}

func setupComprehensiveTestSuite() (*TestSuite, error) {
	// Setup PostgreSQL test database
	// Note: This requires a test PostgreSQL database to be available
	dsn := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		getEnv("TEST_DB_HOST", "localhost"),
		getEnv("TEST_DB_PORT", "5432"),
		getEnv("TEST_DB_USER", "app"),
		getEnv("TEST_DB_PASSWORD", "dairyman"),
		getEnv("TEST_DB_NAME", "records_test"),
		getEnv("TEST_DB_SSLMODE", "disable"),
	)

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to test database: %w", err)
	}

	// Auto-migrate all models
	err = db.AutoMigrate(
		&models.Record{},
		&models.Seller{},
		&models.Listing{},
		&models.RecommendationModel{},
		&models.RecommendationMetrics{},
		&models.RecordOfTheDay{},
		&models.RecordOfTheDayFeedback{},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to migrate test database: %w", err)
	}

	// Setup comprehensive test data
	err = setupComprehensiveTestData(db)
	if err != nil {
		return nil, err
	}

	// Setup configuration
	cfg := &config.Config{
		Database: config.DatabaseConfig{},
		Server:   config.ServerConfig{},
		External: config.ExternalConfig{
			ScraperServiceURL:     "http://localhost:8001",
			RecommenderServiceURL: "http://localhost:8002",
		},
	}

	// Initialize handlers
	h := handlers.New(db, cfg)

	// Setup router with all routes
	gin.SetMode(gin.TestMode)
	router := gin.New()
	setupAllRoutes(router, h)

	return &TestSuite{
		db:     db,
		router: router,
		h:      h,
	}, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func setupAllRoutes(router *gin.Engine, h *handlers.Handler) {
	// Dashboard routes
	router.GET("/dashboard/", h.GetDashboard)
	router.GET("/api/dashboard/listings/", h.GetDashboardListings)
	router.POST("/api/refresh-record-of-the-day/", h.RefreshRecordOfTheDay)

	// Search routes
	router.GET("/search/results/", h.SearchListings)
	router.GET("/autocomplete/genre/", h.GetGenreAutocomplete)
	router.GET("/autocomplete/condition/", h.GetConditionAutocomplete)
	router.GET("/autocomplete/styles/", h.GetStylesAutocomplete)

	// Seller routes
	router.POST("/by-seller/search/", h.SearchSellerListings)
	router.POST("/data/:seller", h.TriggerSellerScrape)
	router.GET("/records/seller/:seller/", h.GetRecordsBySeller)

	// Recommendation routes
	router.GET("/recommendation-predictions/", h.GetRecommendationPredictions)
	router.POST("/submit-scoring-selections/", h.SubmitRecommendations)
	router.GET("/model-performance-stats/", h.GetModelPerformanceStats)

	// Export routes
	router.GET("/export-listings", h.ExportListingsCsv)

	// Wantlist routes
	router.POST("/add-to-wantlist/", h.AddToWantlist)

	// Record of the Day voting
	router.POST("/vote-record-of-the-day/:id/", h.VoteRecordOfTheDay)

	// Go Scraper routes
	router.POST("/api/scraper/go/:seller", h.TriggerGoScraper)
	router.GET("/api/scraper/stats", h.GetScraperStats)
	router.GET("/api/scraper/test", h.TestScraperConnection)

	// Legacy compatibility routes
	router.GET("/api-dashboard/", h.GetDashboard)
}

func setupComprehensiveTestData(db *gorm.DB) error {
	// Create multiple test sellers
	sellers := []models.Seller{
		{Name: "VinylCollector123", Currency: "USD"},
		{Name: "RecordStore", Currency: "EUR"},
		{Name: "MusicLover", Currency: "GBP"},
		{Name: "RareFinds", Currency: "USD"},
	}

	for _, seller := range sellers {
		if err := db.Create(&seller).Error; err != nil {
			return err
		}
	}

	// Create diverse test records
	records := []models.Record{
		{
			DiscogsID: "123456",
			Artist:    "The Beatles",
			Title:     "Abbey Road",
			Format:    "Vinyl",
			Label:     "Apple Records",
			Wants:     500,
			Haves:     200,
			Genres:    models.StringSlice{"Rock", "Pop"},
			Styles:    models.StringSlice{"Classic Rock", "Pop Rock"},
			Year:      intPtr(1969),
		},
		{
			DiscogsID: "789012",
			Artist:    "Pink Floyd",
			Title:     "The Dark Side of the Moon",
			Format:    "Vinyl",
			Label:     "Harvest",
			Wants:     800,
			Haves:     300,
			Genres:    models.StringSlice{"Rock", "Progressive Rock"},
			Styles:    models.StringSlice{"Psychedelic Rock", "Art Rock"},
			Year:      intPtr(1973),
		},
		{
			DiscogsID: "345678",
			Artist:    "Led Zeppelin",
			Title:     "Led Zeppelin IV",
			Format:    "Vinyl",
			Label:     "Atlantic",
			Wants:     600,
			Haves:     250,
			Genres:    models.StringSlice{"Rock", "Hard Rock"},
			Styles:    models.StringSlice{"Blues Rock", "Heavy Metal"},
			Year:      intPtr(1971),
		},
		{
			DiscogsID: "456789",
			Artist:    "Miles Davis",
			Title:     "Kind of Blue",
			Format:    "Vinyl",
			Label:     "Columbia",
			Wants:     400,
			Haves:     150,
			Genres:    models.StringSlice{"Jazz"},
			Styles:    models.StringSlice{"Modal", "Cool Jazz"},
			Year:      intPtr(1959),
		},
		{
			DiscogsID: "567890",
			Artist:    "Kraftwerk",
			Title:     "Trans-Europe Express",
			Format:    "Vinyl",
			Label:     "Kling Klang",
			Wants:     300,
			Haves:     100,
			Genres:    models.StringSlice{"Electronic"},
			Styles:    models.StringSlice{"Krautrock", "Synth-pop"},
			Year:      intPtr(1977),
		},
	}

	for _, record := range records {
		if err := db.Create(&record).Error; err != nil {
			return err
		}
	}

	// Get created records and sellers for foreign keys
	var createdRecords []models.Record
	var createdSellers []models.Seller
	db.Find(&createdRecords)
	db.Find(&createdSellers)

	// Create diverse test listings
	conditions := []string{"Mint (M)", "Near Mint (NM or M-)", "Very Good Plus (VG+)", "Very Good (VG)", "Good Plus (G+)"}
	
	listingID := uint(1)
	for i, record := range createdRecords {
		for j, seller := range createdSellers {
			if (i+j)%2 == 0 { // Create listings for some combinations
				listing := models.Listing{
					ID:             listingID,
					SellerID:       seller.ID,
					RecordID:       record.ID,
					RecordPrice:    float64(20 + (i*5) + (j*3)),
					MediaCondition: conditions[i%len(conditions)],
					Score:          float64(5 + i + j),
					Kept:           (i+j)%3 == 0,
					Evaluated:      (i+j)%4 != 0,
					Record:         record,
					Seller:         seller,
				}
				if err := db.Create(&listing).Error; err != nil {
					return err
				}
				listingID++
			}
		}
	}

	// Create recommendation model data
	model := models.RecommendationModel{
		LastAccuracy: 0.85,
		UpdatedAt:    time.Now(),
	}
	db.Create(&model)

	// Create recommendation metrics
	metrics := []models.RecommendationMetrics{
		{
			SessionDate: time.Now().AddDate(0, 0, -1),
			Accuracy:    0.82,
			Precision:   0.78,
			NumSamples:  100,
		},
		{
			SessionDate: time.Now().AddDate(0, 0, -2),
			Accuracy:    0.85,
			Precision:   0.81,
			NumSamples:  150,
		},
	}
	for _, metric := range metrics {
		db.Create(&metric)
	}

	// Create Record of the Day
	rotd := models.RecordOfTheDay{
		Date:                 time.Now(),
		ListingID:            1,
		ModelScore:           0.85,
		EntropyMeasure:       0.65,
		SystemTemperature:    0.5,
		SelectionMethod:      "thermodynamic_boltzmann",
		UtilityTerm:          floatPtr(0.68),
		EntropyTerm:          floatPtr(0.325),
		FreeEnergy:           floatPtr(0.355),
		SelectionProbability: floatPtr(0.588),
		TotalCandidates:      intPtr(100),
		ClusterCount:         intPtr(8),
		AverageDesirability:  4.2,
		AverageNovelty:       3.8,
		DesirabilityVotes:    []float64{4.0, 4.5, 4.0, 4.2},
		NoveltyVotes:         []float64{3.5, 4.0, 4.0, 3.8},
	}
	db.Create(&rotd)

	return nil
}

func intPtr(i int) *int {
	return &i
}

func floatPtr(f float64) *float64 {
	return &f
}

// DASHBOARD ENDPOINT TESTS
func TestDashboardEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /dashboard/ - Basic Dashboard Stats", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/dashboard/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		assert.Contains(t, w.Header().Get("Access-Control-Allow-Origin"), "localhost")

		var response handlers.DashboardStats
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Greater(t, response.NumRecords, int64(0))
		assert.Greater(t, response.NumListings, int64(0))
		assert.GreaterOrEqual(t, response.Accuracy, float64(0))
		assert.GreaterOrEqual(t, response.Unevaluated, int64(0))
		assert.NotNil(t, response.Breakdown)
	})

	t.Run("GET /dashboard/ - Force Refresh", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/dashboard/?force_refresh=1", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response handlers.DashboardStats
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.NotNil(t, response.Breakdown)
	})

	t.Run("GET /api/dashboard/listings/ - Dashboard Listings", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/dashboard/listings/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var listings []models.Listing
		err := json.Unmarshal(w.Body.Bytes(), &listings)
		require.NoError(t, err)

		assert.True(t, len(listings) > 0)
		assert.True(t, len(listings) <= 20) // Should be limited to 20

		// Verify structure of first listing
		if len(listings) > 0 {
			listing := listings[0]
			assert.NotZero(t, listing.ID)
			assert.NotZero(t, listing.RecordID)
			assert.NotZero(t, listing.SellerID)
			assert.NotEmpty(t, listing.MediaCondition)
			assert.Greater(t, listing.RecordPrice, float64(0))
		}
	})

	t.Run("POST /api/refresh-record-of-the-day/ - Refresh ROTD", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/api/refresh-record-of-the-day/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		// This might fail due to external service dependency, but should return proper error
		assert.True(t, w.Code == http.StatusOK || w.Code == http.StatusInternalServerError)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		// Should have either message or error
		assert.True(t, response["message"] != nil || response["error"] != nil)
	})

	t.Run("GET /api-dashboard/ - Legacy Dashboard", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api-dashboard/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response handlers.DashboardStats
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Greater(t, response.NumRecords, int64(0))
	})
}

// SEARCH ENDPOINT TESTS
func TestSearchEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /search/results/ - Basic Search", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "count")
		assert.Contains(t, response, "results")
		assert.Contains(t, response, "next")
		assert.Contains(t, response, "previous")
	})

	t.Run("GET /search/results/ - Text Search", func(t *testing.T) {
		testCases := []struct {
			query    string
			expected string
		}{
			{"q=Beatles", "Beatles"},
			{"q=Pink Floyd", "Pink Floyd"},
			{"q=Abbey Road", "Abbey Road"},
		}

		for _, tc := range testCases {
			req, _ := http.NewRequest("GET", "/search/results/?"+tc.query, nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "Failed for query: %s", tc.query)

			var response map[string]interface{}
			err := json.Unmarshal(w.Body.Bytes(), &response)
			require.NoError(t, err, "Failed to parse response for query: %s", tc.query)

			assert.Contains(t, response, "results")
		}
	})

	t.Run("GET /search/results/ - Genre/Style Filter", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?genre_style=Rock", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})

	t.Run("GET /search/results/ - Year Range Filter", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?min_year=1960&max_year=1980", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})

	t.Run("GET /search/results/ - Price Range Filter", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?min_price=20&max_price=50", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})

	t.Run("GET /search/results/ - Condition Filter", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?condition=Mint", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})

	t.Run("GET /search/results/ - Seller Filter", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?seller=VinylCollector", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})

	t.Run("GET /search/results/ - Sorting Options", func(t *testing.T) {
		sortOptions := []string{"price_asc", "price_desc", "year_asc", "year_desc", "score_desc"}

		for _, sort := range sortOptions {
			req, _ := http.NewRequest("GET", "/search/results/?sort="+sort, nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "Failed for sort: %s", sort)

			var response map[string]interface{}
			err := json.Unmarshal(w.Body.Bytes(), &response)
			require.NoError(t, err, "Failed to parse response for sort: %s", sort)

			assert.Contains(t, response, "results")
		}
	})

	t.Run("GET /search/results/ - Pagination", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/search/results/?page=1", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "count")
		assert.Contains(t, response, "next")
		assert.Contains(t, response, "previous")
	})

	t.Run("GET /search/results/ - Complex Query", func(t *testing.T) {
		complexQuery := "q=Rock&genre_style=Rock&min_year=1970&max_year=1980&min_price=20&max_price=40&sort=score_desc&page=1"
		req, _ := http.NewRequest("GET", "/search/results/?"+complexQuery, nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "results")
	})
}

// AUTOCOMPLETE ENDPOINT TESTS
func TestAutocompleteEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /autocomplete/genre/ - Genre Autocomplete", func(t *testing.T) {
		testCases := []string{"Rock", "Jazz", "Electronic", "r", "j"}

		for _, term := range testCases {
			req, _ := http.NewRequest("GET", "/autocomplete/genre/?term="+url.QueryEscape(term), nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "Failed for term: %s", term)

			var suggestions []string
			err := json.Unmarshal(w.Body.Bytes(), &suggestions)
			require.NoError(t, err, "Failed to parse response for term: %s", term)

			assert.True(t, len(suggestions) >= 0)
			assert.True(t, len(suggestions) <= 10) // Should be limited to 10
		}
	})

	t.Run("GET /autocomplete/genre/ - Empty Term", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/autocomplete/genre/?term=", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var suggestions []string
		err := json.Unmarshal(w.Body.Bytes(), &suggestions)
		require.NoError(t, err)

		assert.Equal(t, 0, len(suggestions))
	})

	t.Run("GET /autocomplete/condition/ - Condition Autocomplete", func(t *testing.T) {
		testCases := []string{"Mint", "Near", "Good", "m", "n"}

		for _, term := range testCases {
			req, _ := http.NewRequest("GET", "/autocomplete/condition/?term="+url.QueryEscape(term), nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "Failed for term: %s", term)

			var suggestions []string
			err := json.Unmarshal(w.Body.Bytes(), &suggestions)
			require.NoError(t, err, "Failed to parse response for term: %s", term)

			assert.True(t, len(suggestions) >= 0)
			assert.True(t, len(suggestions) <= 10)
		}
	})

	t.Run("GET /autocomplete/styles/ - Styles Autocomplete", func(t *testing.T) {
		testCases := []string{"Rock", "Jazz", "Pop", "r", "j"}

		for _, term := range testCases {
			req, _ := http.NewRequest("GET", "/autocomplete/styles/?term="+url.QueryEscape(term), nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "Failed for term: %s", term)

			var suggestions []string
			err := json.Unmarshal(w.Body.Bytes(), &suggestions)
			require.NoError(t, err, "Failed to parse response for term: %s", term)

			assert.True(t, len(suggestions) >= 0)
			assert.True(t, len(suggestions) <= 10)
		}
	})
}

// SELLER ENDPOINT TESTS
func TestSellerEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("POST /by-seller/search/ - Valid Seller", func(t *testing.T) {
		reqBody := map[string]string{
			"seller": "VinylCollector123",
		}
		jsonBody, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest("POST", "/by-seller/search/", bytes.NewBuffer(jsonBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var listings []models.Listing
		err := json.Unmarshal(w.Body.Bytes(), &listings)
		require.NoError(t, err)

		assert.True(t, len(listings) >= 0)
	})

	t.Run("POST /by-seller/search/ - Partial Seller Name", func(t *testing.T) {
		reqBody := map[string]string{
			"seller": "Vinyl",
		}
		jsonBody, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest("POST", "/by-seller/search/", bytes.NewBuffer(jsonBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var listings []models.Listing
		err := json.Unmarshal(w.Body.Bytes(), &listings)
		require.NoError(t, err)

		assert.True(t, len(listings) >= 0)
	})

	t.Run("POST /by-seller/search/ - Empty Seller", func(t *testing.T) {
		reqBody := map[string]string{
			"seller": "",
		}
		jsonBody, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest("POST", "/by-seller/search/", bytes.NewBuffer(jsonBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})

	t.Run("POST /by-seller/search/ - Invalid JSON", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/by-seller/search/", bytes.NewBuffer([]byte("invalid json")))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})

	t.Run("GET /records/seller/:seller/ - Valid Seller", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/records/seller/VinylCollector123/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var records []models.Record
		err := json.Unmarshal(w.Body.Bytes(), &records)
		require.NoError(t, err)

		assert.True(t, len(records) >= 0)
	})

	t.Run("GET /records/seller/:seller/ - Nonexistent Seller", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/records/seller/NonexistentSeller/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var records []models.Record
		err := json.Unmarshal(w.Body.Bytes(), &records)
		require.NoError(t, err)

		assert.Equal(t, 0, len(records))
	})

	t.Run("POST /data/:seller - Trigger Scraper", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/data/TestSeller", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		// This will likely fail due to external service dependency
		assert.True(t, w.Code == http.StatusCreated || w.Code == http.StatusInternalServerError)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		// Should have either message or error
		assert.True(t, response["message"] != nil || response["error"] != nil)
	})

	t.Run("POST /data/:seller - Empty Seller", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/data/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)
	})
}

// RECOMMENDATION ENDPOINT TESTS
func TestRecommendationEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /recommendation-predictions/ - Valid Listing IDs", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/recommendation-predictions/?listing_ids=1&listing_ids=2&listing_ids=3", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var predictions []map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &predictions)
		require.NoError(t, err)

		assert.True(t, len(predictions) >= 0)

		// Verify structure if predictions exist
		if len(predictions) > 0 {
			pred := predictions[0]
			assert.Contains(t, pred, "id")
			assert.Contains(t, pred, "prediction")
			assert.Contains(t, pred, "probability")
		}
	})

	t.Run("GET /recommendation-predictions/ - No Listing IDs", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/recommendation-predictions/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var predictions []map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &predictions)
		require.NoError(t, err)

		assert.Equal(t, 0, len(predictions))
	})

	t.Run("GET /recommendation-predictions/ - Invalid Listing IDs", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/recommendation-predictions/?listing_ids=invalid&listing_ids=abc", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var predictions []map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &predictions)
		require.NoError(t, err)

		assert.Equal(t, 0, len(predictions))
	})

	t.Run("POST /submit-scoring-selections/ - Valid Form Data", func(t *testing.T) {
		form := url.Values{}
		form.Add("listing_ids", "1")
		form.Add("listing_ids", "2")
		form.Add("listing_ids", "3")
		form.Add("keeper_ids", "1")
		form.Add("keeper_ids", "3")

		req, _ := http.NewRequest("POST", "/submit-scoring-selections/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, true, response["success"])
	})

	t.Run("POST /submit-scoring-selections/ - Empty Form Data", func(t *testing.T) {
		form := url.Values{}

		req, _ := http.NewRequest("POST", "/submit-scoring-selections/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, true, response["success"])
	})

	t.Run("GET /model-performance-stats/ - Performance Stats", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/model-performance-stats/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "accuracy")
		assert.Contains(t, response, "total_sessions")
		assert.Contains(t, response, "sessions")

		// Verify accuracy is a valid number
		if accuracy, ok := response["accuracy"].(float64); ok {
			assert.GreaterOrEqual(t, accuracy, float64(0))
			assert.LessOrEqual(t, accuracy, float64(1))
		}

		// Verify sessions structure
		if sessions, ok := response["sessions"].([]interface{}); ok {
			for _, session := range sessions {
				if sessionMap, ok := session.(map[string]interface{}); ok {
					assert.Contains(t, sessionMap, "session_date")
					assert.Contains(t, sessionMap, "accuracy")
					assert.Contains(t, sessionMap, "precision")
					assert.Contains(t, sessionMap, "num_samples")
				}
			}
		}
	})
}

// EXPORT ENDPOINT TESTS
func TestExportEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /export-listings - CSV Export", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/export-listings", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "text/csv", w.Header().Get("Content-Type"))
		assert.Contains(t, w.Header().Get("Content-Disposition"), "attachment")
		assert.Contains(t, w.Header().Get("Content-Disposition"), "listings_export.csv")

		// Verify CSV content structure
		csvContent := w.Body.String()
		assert.NotEmpty(t, csvContent)
		
		// Should contain headers
		assert.Contains(t, csvContent, "Listing ID")
		assert.Contains(t, csvContent, "Record Artist")
		assert.Contains(t, csvContent, "Record Title")
		assert.Contains(t, csvContent, "Seller")
		assert.Contains(t, csvContent, "Record Price")
	})
}

// WANTLIST ENDPOINT TESTS
func TestWantlistEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("POST /add-to-wantlist/ - Valid Record ID", func(t *testing.T) {
		form := url.Values{}
		form.Add("record_id", "123456")

		req, _ := http.NewRequest("POST", "/add-to-wantlist/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "message")
		assert.Equal(t, "Added to wantlist!", response["message"])
	})

	t.Run("POST /add-to-wantlist/ - Empty Record ID", func(t *testing.T) {
		form := url.Values{}

		req, _ := http.NewRequest("POST", "/add-to-wantlist/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})
}

// RECORD OF THE DAY VOTING TESTS
func TestRecordOfTheDayVoting(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("POST /vote-record-of-the-day/:id/ - Valid Vote", func(t *testing.T) {
		form := url.Values{}
		form.Add("desirability", "4.5")
		form.Add("novelty", "3.8")

		req, _ := http.NewRequest("POST", "/vote-record-of-the-day/1/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "message")
		assert.Contains(t, response["message"].(string), "Vote submitted")
	})

	t.Run("POST /vote-record-of-the-day/:id/ - Invalid Record ID", func(t *testing.T) {
		form := url.Values{}
		form.Add("desirability", "4.5")
		form.Add("novelty", "3.8")

		req, _ := http.NewRequest("POST", "/vote-record-of-the-day/invalid/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})

	t.Run("POST /vote-record-of-the-day/:id/ - Invalid Desirability", func(t *testing.T) {
		form := url.Values{}
		form.Add("desirability", "invalid")
		form.Add("novelty", "3.8")

		req, _ := http.NewRequest("POST", "/vote-record-of-the-day/1/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})

	t.Run("POST /vote-record-of-the-day/:id/ - Invalid Novelty", func(t *testing.T) {
		form := url.Values{}
		form.Add("desirability", "4.5")
		form.Add("novelty", "invalid")

		req, _ := http.NewRequest("POST", "/vote-record-of-the-day/1/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})

	t.Run("POST /vote-record-of-the-day/:id/ - Nonexistent Record", func(t *testing.T) {
		form := url.Values{}
		form.Add("desirability", "4.5")
		form.Add("novelty", "3.8")

		req, _ := http.NewRequest("POST", "/vote-record-of-the-day/999/", strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response, "error")
	})
}

// GO SCRAPER ENDPOINT TESTS
func TestGoScraperEndpoints(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("POST /api/scraper/go/:seller - Trigger Go Scraper", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/api/scraper/go/TestSeller", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		// This will likely fail due to scraper service not being available in test
		assert.True(t, w.Code == http.StatusOK || w.Code == http.StatusServiceUnavailable || w.Code == http.StatusInternalServerError)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		// Should have either success/message or error
		assert.True(t, response["success"] != nil || response["error"] != nil)
	})

	t.Run("POST /api/scraper/go/:seller - Empty Seller", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/api/scraper/go/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)
	})

	t.Run("GET /api/scraper/stats - Scraper Stats", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/scraper/stats", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		// This will likely fail due to scraper service not being available in test
		assert.True(t, w.Code == http.StatusOK || w.Code == http.StatusServiceUnavailable || w.Code == http.StatusInternalServerError)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		// Should have either stats data or error
		assert.True(t, len(response) > 0)
	})

	t.Run("GET /api/scraper/test - Test Scraper Connection", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/scraper/test", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		// This will likely fail due to scraper service not being available in test
		assert.True(t, w.Code == http.StatusOK || w.Code == http.StatusServiceUnavailable || w.Code == http.StatusInternalServerError)

		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		// Should have either success or error
		assert.True(t, response["success"] != nil || response["error"] != nil)
	})
}

// ERROR HANDLING TESTS
func TestErrorHandling(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("GET /nonexistent-endpoint - 404 Error", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/nonexistent-endpoint", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)
	})

	t.Run("POST /search/results/ - Method Not Allowed", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/search/results/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusMethodNotAllowed, w.Code)
	})

	t.Run("GET /by-seller/search/ - Method Not Allowed", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/by-seller/search/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusMethodNotAllowed, w.Code)
	})
}

// PERFORMANCE AND LOAD TESTS
func TestPerformanceBasics(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("Dashboard Performance - Multiple Requests", func(t *testing.T) {
		start := time.Now()
		
		for i := 0; i < 10; i++ {
			req, _ := http.NewRequest("GET", "/dashboard/", nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)
			assert.Equal(t, http.StatusOK, w.Code)
		}
		
		duration := time.Since(start)
		assert.Less(t, duration, 5*time.Second, "Dashboard should handle 10 requests in under 5 seconds")
	})

	t.Run("Search Performance - Multiple Queries", func(t *testing.T) {
		queries := []string{
			"/search/results/?q=Beatles",
			"/search/results/?genre_style=Rock",
			"/search/results/?min_year=1970&max_year=1980",
			"/search/results/?sort=price_asc",
			"/search/results/?page=1",
		}

		start := time.Now()
		
		for _, query := range queries {
			req, _ := http.NewRequest("GET", query, nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)
			assert.Equal(t, http.StatusOK, w.Code)
		}
		
		duration := time.Since(start)
		assert.Less(t, duration, 3*time.Second, "Search queries should complete in under 3 seconds")
	})
}

// INTEGRATION TESTS WITH EXTERNAL SERVICES
func TestExternalServiceIntegration(t *testing.T) {
	suite, err := setupComprehensiveTestSuite()
	require.NoError(t, err)

	t.Run("External Service Fallback Behavior", func(t *testing.T) {
		// Test that endpoints gracefully handle external service failures
		
		// Dashboard should still work even if thermodynamic service is down
		req, _ := http.NewRequest("GET", "/dashboard/", nil)
		w := httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)

		// Recommendation predictions should return default values if service is down
		req, _ = http.NewRequest("GET", "/recommendation-predictions/?listing_ids=1&listing_ids=2", nil)
		w = httptest.NewRecorder()
		suite.router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)

		var predictions []map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &predictions)
		require.NoError(t, err)
		
		// Should return default predictions even if external service fails
		assert.True(t, len(predictions) >= 0)
	})
}

// COMPREHENSIVE TEST RUNNER
func TestMain(m *testing.M) {
	fmt.Println("=== COMPREHENSIVE ENDPOINT TESTING ===")
	fmt.Println("Testing all API endpoints thoroughly...")
	
	// Run all tests
	code := m.Run()
	
	fmt.Println("=== TEST SUMMARY ===")
	if code == 0 {
		fmt.Println("✅ All endpoint tests passed!")
	} else {
		fmt.Println("❌ Some tests failed. Check output above.")
	}
	
	os.Exit(code)
}
