package main

import (
	"log"
	"os"

	"discogs-api/internal/config"
	"discogs-api/internal/database"
	"discogs-api/internal/handlers"
	"discogs-api/internal/middleware"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load environment variables
	if err := godotenv.Load("../.env"); err != nil {
		log.Println("Warning: .env file not found, using system environment variables")
	}

	// Initialize configuration
	cfg := config.Load()

	// Initialize database
	db, err := database.Initialize(cfg.Database)
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}

	// Auto-migrate database tables
	if err := database.AutoMigrate(db); err != nil {
		log.Fatal("Failed to migrate database:", err)
	}

	// Initialize Gin router
	router := gin.Default()

	// Configure CORS
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowOrigins = []string{
		"http://localhost:3000",
		"http://localhost:5173",
		"http://localhost:5174",
	}
	corsConfig.AllowCredentials = true
	corsConfig.AllowHeaders = []string{
		"Origin",
		"Content-Length",
		"Content-Type",
		"Authorization",
		"X-Requested-With",
		"X-CSRF-Token",
	}
	corsConfig.AllowMethods = []string{
		"GET",
		"POST",
		"PUT",
		"PATCH",
		"DELETE",
		"OPTIONS",
	}
	router.Use(cors.New(corsConfig))

	// Add logging middleware
	router.Use(middleware.Logger())

	// Initialize handlers
	h := handlers.New(db, cfg)

	// Setup routes
	setupRoutes(router, h)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	log.Printf("Server starting on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}

func setupRoutes(router *gin.Engine, h *handlers.Handler) {
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
