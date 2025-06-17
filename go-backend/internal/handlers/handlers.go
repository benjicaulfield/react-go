package handlers

import (
	"encoding/csv"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"discogs-api/internal/config"
	"discogs-api/internal/models"
	"discogs-api/internal/services"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type Handler struct {
	db              *gorm.DB
	config          *config.Config
	externalService *services.ExternalService
	scraperService  *services.ScraperService
}

func New(db *gorm.DB, cfg *config.Config) *Handler {
	scraperService, err := services.NewScraperService(db, cfg)
	if err != nil {
		log.Printf("Warning: Failed to initialize Go scraper service: %v", err)
	}

	return &Handler{
		db:              db,
		config:          cfg,
		externalService: services.NewExternalService(cfg),
		scraperService:  scraperService,
	}
}

// DashboardStats represents the dashboard statistics response
type DashboardStats struct {
	NumRecords       int64                  `json:"num_records"`
	NumListings      int64                  `json:"num_listings"`
	Accuracy         float64                `json:"accuracy"`
	Unevaluated      int64                  `json:"unevaluated"`
	RecordOfTheDay   *models.Listing        `json:"record_of_the_day"`
	RecordOfTheDayObj *models.RecordOfTheDay `json:"record_of_the_day_obj"`
	Breakdown        map[string]interface{} `json:"breakdown"`
}

// GetDashboard handles GET /dashboard/
func (h *Handler) GetDashboard(c *gin.Context) {
	var numRecords, numListings, unevaluated int64

	// Get counts
	h.db.Model(&models.Record{}).Count(&numRecords)
	h.db.Model(&models.Listing{}).Count(&numListings)
	h.db.Model(&models.Listing{}).Where("evaluated = ?", false).Count(&unevaluated)

	// Get model accuracy
	var accuracy float64
	var model models.RecommendationModel
	if err := h.db.Order("updated_at DESC").First(&model).Error; err == nil {
		accuracy = model.LastAccuracy * 100
	}

	// Get or create today's Record of the Day
	today := time.Now().Format("2006-01-02")
	forceRefresh := c.Query("force_refresh") == "1"

	var recordOfTheDayObj models.RecordOfTheDay
	var recordOfTheDay *models.Listing
	breakdown := make(map[string]interface{})

	// Try to get existing record of the day
	err := h.db.Preload("Listing.Record").Preload("Listing.Seller").
		Where("date = ?", today).First(&recordOfTheDayObj).Error

	if err != nil || forceRefresh {
		// If not found or force refresh, try to get from thermodynamic service
		if forceRefresh {
			h.db.Where("date = ?", today).Delete(&models.RecordOfTheDay{})
		}

		thermoResp, err := h.externalService.GetThermodynamicSelection(forceRefresh)
		if err != nil {
			log.Printf("Error getting thermodynamic selection: %v", err)
			// Fallback to highest score listing
			var fallbackListing models.Listing
			if err := h.db.Preload("Record").Preload("Seller").
				Where("score > ?", 0).Order("score DESC").First(&fallbackListing).Error; err == nil {
				recordOfTheDay = &fallbackListing
				breakdown["selection_method"] = "fallback_highest_score"
				breakdown["error"] = "external service unavailable"
			}
		} else if thermoResp != nil && thermoResp.Success {
			// Get the listing from the database
			var listing models.Listing
			if err := h.db.Preload("Record").Preload("Seller").
				First(&listing, thermoResp.ListingID).Error; err == nil {
				recordOfTheDay = &listing
				breakdown = thermoResp.Breakdown

				// Save to database
				recordOfTheDayObj = models.RecordOfTheDay{
					Date:      time.Now(),
					ListingID: uint(thermoResp.ListingID),
					Listing:   listing,
				}
				// Extract breakdown values
				if val, ok := thermoResp.Breakdown["model_score"].(float64); ok {
					recordOfTheDayObj.ModelScore = val
				}
				if val, ok := thermoResp.Breakdown["entropy_measure"].(float64); ok {
					recordOfTheDayObj.EntropyMeasure = val
				}
				if val, ok := thermoResp.Breakdown["system_temperature"].(float64); ok {
					recordOfTheDayObj.SystemTemperature = val
				}
				if val, ok := thermoResp.Breakdown["selection_method"].(string); ok {
					recordOfTheDayObj.SelectionMethod = val
				}

				h.db.Create(&recordOfTheDayObj)
			}
		}
	} else {
		// Use existing record
		recordOfTheDay = &recordOfTheDayObj.Listing
		breakdown = map[string]interface{}{
			"model_score":          recordOfTheDayObj.ModelScore,
			"entropy_measure":      recordOfTheDayObj.EntropyMeasure,
			"system_temperature":   recordOfTheDayObj.SystemTemperature,
			"utility_term":         recordOfTheDayObj.UtilityTerm,
			"entropy_term":         recordOfTheDayObj.EntropyTerm,
			"free_energy":          recordOfTheDayObj.FreeEnergy,
			"selection_probability": recordOfTheDayObj.SelectionProbability,
			"total_candidates":     recordOfTheDayObj.TotalCandidates,
			"cluster_count":        recordOfTheDayObj.ClusterCount,
			"selection_method":     recordOfTheDayObj.SelectionMethod,
		}
	}

	var recordOfTheDayObjPtr *models.RecordOfTheDay
	if recordOfTheDay != nil {
		recordOfTheDayObjPtr = &recordOfTheDayObj
	}

	response := DashboardStats{
		NumRecords:        numRecords,
		NumListings:       numListings,
		Accuracy:          accuracy,
		Unevaluated:       unevaluated,
		RecordOfTheDay:    recordOfTheDay,
		RecordOfTheDayObj: recordOfTheDayObjPtr,
		Breakdown:         breakdown,
	}

	c.Header("Access-Control-Allow-Origin", "http://localhost:5173")
	c.JSON(http.StatusOK, response)
}

// GetDashboardListings handles GET /api/dashboard/listings/
func (h *Handler) GetDashboardListings(c *gin.Context) {
	var listings []models.Listing

	// Get top 10 by score and 10 random listings
	var topListings []models.Listing
	h.db.Preload("Record").Preload("Seller").
		Order("score DESC").Limit(10).Find(&topListings)

	var randomListings []models.Listing
	h.db.Preload("Record").Preload("Seller").
		Order("RANDOM()").Limit(10).Find(&randomListings)

	// Combine and shuffle
	listings = append(topListings, randomListings...)

	c.JSON(http.StatusOK, listings)
}

// RefreshRecordOfTheDay handles POST /api/refresh-record-of-the-day/
func (h *Handler) RefreshRecordOfTheDay(c *gin.Context) {
	today := time.Now().Format("2006-01-02")

	// Delete existing record for today
	h.db.Where("date = ?", today).Delete(&models.RecordOfTheDay{})

	// Get new selection from thermodynamic service
	thermoResp, err := h.externalService.GetThermodynamicSelection(true)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get thermodynamic selection: " + err.Error(),
		})
		return
	}

	if !thermoResp.Success {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Thermodynamic selection failed: " + thermoResp.Error,
		})
		return
	}

	// Get the listing and save new record of the day
	var listing models.Listing
	if err := h.db.Preload("Record").Preload("Seller").
		First(&listing, thermoResp.ListingID).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to find selected listing",
		})
		return
	}

	recordOfTheDayObj := models.RecordOfTheDay{
		Date:      time.Now(),
		ListingID: uint(thermoResp.ListingID),
		Listing:   listing,
	}

	// Extract breakdown values
	if val, ok := thermoResp.Breakdown["model_score"].(float64); ok {
		recordOfTheDayObj.ModelScore = val
	}
	if val, ok := thermoResp.Breakdown["entropy_measure"].(float64); ok {
		recordOfTheDayObj.EntropyMeasure = val
	}
	if val, ok := thermoResp.Breakdown["system_temperature"].(float64); ok {
		recordOfTheDayObj.SystemTemperature = val
	}
	if val, ok := thermoResp.Breakdown["selection_method"].(string); ok {
		recordOfTheDayObj.SelectionMethod = val
	}

	if err := h.db.Create(&recordOfTheDayObj).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to save new record of the day",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Record of the Day refreshed successfully",
	})
}

// SearchListings handles GET /search/results/
func (h *Handler) SearchListings(c *gin.Context) {
	query := h.db.Preload("Record").Preload("Seller")

	// Text search
	if q := c.Query("q"); q != "" {
		query = query.Where(
			"discogs_record.artist ILIKE ? OR discogs_record.title ILIKE ? OR discogs_record.label ILIKE ?",
			"%"+q+"%", "%"+q+"%", "%"+q+"%",
		).Joins("JOIN discogs_record ON discogs_listing.record_id = discogs_record.id")
	}

	// Genre/Style filter
	if genreStyle := c.Query("genre_style"); genreStyle != "" {
		query = query.Where(
			"discogs_record.genres::text ILIKE ? OR discogs_record.styles::text ILIKE ?",
			"%"+genreStyle+"%", "%"+genreStyle+"%",
		).Joins("JOIN discogs_record ON discogs_listing.record_id = discogs_record.id")
	}

	// Year range filter
	if minYear := c.Query("min_year"); minYear != "" {
		if maxYear := c.Query("max_year"); maxYear != "" {
			if minYearInt, err := strconv.Atoi(minYear); err == nil {
				if maxYearInt, err := strconv.Atoi(maxYear); err == nil {
					query = query.Where(
						"discogs_record.year BETWEEN ? AND ?", minYearInt, maxYearInt,
					).Joins("JOIN discogs_record ON discogs_listing.record_id = discogs_record.id")
				}
			}
		}
	}

	// Price range filter
	if minPrice := c.Query("min_price"); minPrice != "" {
		if maxPrice := c.Query("max_price"); maxPrice != "" {
			if minPriceFloat, err := strconv.ParseFloat(minPrice, 64); err == nil {
				if maxPriceFloat, err := strconv.ParseFloat(maxPrice, 64); err == nil {
					query = query.Where("record_price BETWEEN ? AND ?", minPriceFloat, maxPriceFloat)
				}
			}
		}
	}

	// Condition filter
	if condition := c.Query("condition"); condition != "" {
		query = query.Where("media_condition ILIKE ?", condition)
	}

	// Seller filter
	if seller := c.Query("seller"); seller != "" {
		query = query.Where(
			"discogs_seller.name ILIKE ?", "%"+seller+"%",
		).Joins("JOIN discogs_seller ON discogs_listing.seller_id = discogs_seller.id")
	}

	// Sorting
	sort := c.DefaultQuery("sort", "score_desc")
	switch sort {
	case "price_asc":
		query = query.Order("record_price ASC")
	case "price_desc":
		query = query.Order("record_price DESC")
	case "year_asc":
		query = query.Joins("JOIN discogs_record ON discogs_listing.record_id = discogs_record.id").
			Order("discogs_record.year ASC")
	case "year_desc":
		query = query.Joins("JOIN discogs_record ON discogs_listing.record_id = discogs_record.id").
			Order("discogs_record.year DESC")
	default:
		query = query.Order("score DESC")
	}

	// Pagination
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}
	limit := 20
	offset := (page - 1) * limit

	var listings []models.Listing
	var total int64

	query.Count(&total)
	query.Limit(limit).Offset(offset).Find(&listings)

	// Calculate pagination info
	hasNext := int64(offset+limit) < total
	hasPrev := page > 1

	var nextPage, prevPage *int
	if hasNext {
		next := page + 1
		nextPage = &next
	}
	if hasPrev {
		prev := page - 1
		prevPage = &prev
	}

	response := gin.H{
		"count":    total,
		"next":     nextPage,
		"previous": prevPage,
		"results":  listings,
	}

	c.JSON(http.StatusOK, response)
}

// GetGenreAutocomplete handles GET /autocomplete/genre/
func (h *Handler) GetGenreAutocomplete(c *gin.Context) {
	term := strings.ToLower(c.Query("term"))
	if term == "" {
		c.JSON(http.StatusOK, []string{})
		return
	}

	var records []models.Record
	h.db.Select("genres, styles").Where(
		"genres::text ILIKE ? OR styles::text ILIKE ?",
		"%"+term+"%", "%"+term+"%",
	).Limit(100).Find(&records)

	genreSet := make(map[string]bool)
	for _, record := range records {
		for _, genre := range record.Genres {
			if strings.Contains(strings.ToLower(genre), term) {
				genreSet[genre] = true
			}
		}
		for _, style := range record.Styles {
			if strings.Contains(strings.ToLower(style), term) {
				genreSet[style] = true
			}
		}
	}

	var suggestions []string
	for genre := range genreSet {
		suggestions = append(suggestions, genre)
		if len(suggestions) >= 10 {
			break
		}
	}

	c.JSON(http.StatusOK, suggestions)
}

// GetConditionAutocomplete handles GET /autocomplete/condition/
func (h *Handler) GetConditionAutocomplete(c *gin.Context) {
	term := strings.ToLower(c.Query("term"))
	if term == "" {
		c.JSON(http.StatusOK, []string{})
		return
	}

	var conditions []string
	h.db.Model(&models.Listing{}).
		Select("DISTINCT media_condition").
		Where("media_condition ILIKE ?", "%"+term+"%").
		Limit(10).
		Pluck("media_condition", &conditions)

	c.JSON(http.StatusOK, conditions)
}

// GetStylesAutocomplete handles GET /autocomplete/styles/
func (h *Handler) GetStylesAutocomplete(c *gin.Context) {
	term := strings.ToLower(c.Query("term"))
	if term == "" {
		c.JSON(http.StatusOK, []string{})
		return
	}

	var records []models.Record
	h.db.Select("styles").Where("styles::text ILIKE ?", "%"+term+"%").Limit(100).Find(&records)

	styleSet := make(map[string]bool)
	for _, record := range records {
		for _, style := range record.Styles {
			if strings.Contains(strings.ToLower(style), term) {
				styleSet[style] = true
			}
		}
	}

	var suggestions []string
	for style := range styleSet {
		suggestions = append(suggestions, style)
		if len(suggestions) >= 10 {
			break
		}
	}

	c.JSON(http.StatusOK, suggestions)
}

// SearchSellerListings handles POST /by-seller/search/
func (h *Handler) SearchSellerListings(c *gin.Context) {
	var req struct {
		Seller string `json:"seller"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request format"})
		return
	}

	if req.Seller == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Seller name is required"})
		return
	}

	var listings []models.Listing
	h.db.Preload("Record").Preload("Seller").
		Joins("JOIN discogs_seller ON discogs_listing.seller_id = discogs_seller.id").
		Where("discogs_seller.name = ?", req.Seller).
		Find(&listings)

	c.JSON(http.StatusOK, listings)
}

// TriggerSellerScrape handles POST /data/:seller
func (h *Handler) TriggerSellerScrape(c *gin.Context) {
	sellerName := c.Param("seller")
	if sellerName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Seller name is required"})
		return
	}

	// Call the scraper microservice
	resp, err := h.externalService.TriggerScraper(sellerName)
	if err != nil {
		log.Printf("Error calling scraper service: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to trigger scraper: " + err.Error(),
		})
		return
	}

	if !resp.Success {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": resp.Error,
		})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": resp.Message,
	})
}

// GetRecordsBySeller handles GET /records/seller/:seller/
func (h *Handler) GetRecordsBySeller(c *gin.Context) {
	sellerName := c.Param("seller")
	if sellerName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Seller name is required"})
		return
	}

	var records []models.Record
	h.db.Joins("JOIN discogs_listing ON discogs_record.id = discogs_listing.record_id").
		Joins("JOIN discogs_seller ON discogs_listing.seller_id = discogs_seller.id").
		Where("discogs_seller.name = ?", sellerName).
		Find(&records)

	c.JSON(http.StatusOK, records)
}

// GetRecommendationPredictions handles GET /recommendation-predictions/
func (h *Handler) GetRecommendationPredictions(c *gin.Context) {
	listingIDStrs := c.QueryArray("listing_ids")
	if len(listingIDStrs) == 0 {
		c.JSON(http.StatusOK, []gin.H{})
		return
	}

	var listingIDs []int
	for _, idStr := range listingIDStrs {
		if id, err := strconv.Atoi(idStr); err == nil {
			listingIDs = append(listingIDs, id)
		}
	}

	// Call the recommendation microservice
	resp, err := h.externalService.GetRecommendations(listingIDs)
	if err != nil {
		log.Printf("Error calling recommendation service: %v", err)
		// Return default predictions on error
		var predictions []gin.H
		for _, id := range listingIDs {
			predictions = append(predictions, gin.H{
				"id":          id,
				"prediction":  true,
				"probability": 0.5,
			})
		}
		c.JSON(http.StatusOK, predictions)
		return
	}

	// Convert to expected format
	var predictions []gin.H
	for _, pred := range resp.Predictions {
		predictions = append(predictions, gin.H{
			"id":          pred.ID,
			"prediction":  pred.Prediction,
			"probability": pred.Probability,
		})
	}

	c.JSON(http.StatusOK, predictions)
}

// SubmitRecommendations handles POST /submit-scoring-selections/
func (h *Handler) SubmitRecommendations(c *gin.Context) {
	listingIDStrs := c.PostFormArray("listing_ids")
	keeperIDStrs := c.PostFormArray("keeper_ids")

	var listingIDs, keeperIDs []int

	for _, idStr := range listingIDStrs {
		if id, err := strconv.Atoi(idStr); err == nil {
			listingIDs = append(listingIDs, id)
		}
	}

	for _, idStr := range keeperIDStrs {
		if id, err := strconv.Atoi(idStr); err == nil {
			keeperIDs = append(keeperIDs, id)
		}
	}

	// Update listings in database
	for _, id := range listingIDs {
		updates := map[string]interface{}{
			"evaluated": true,
			"kept":      false,
		}
		for _, keeperID := range keeperIDs {
			if id == keeperID {
				updates["kept"] = true
				break
			}
		}
		h.db.Model(&models.Listing{}).Where("id = ?", id).Updates(updates)
	}

	// Call the recommendation microservice to train the model
	_, err := h.externalService.TrainModel(listingIDs, keeperIDs)
	if err != nil {
		log.Printf("Error training model: %v", err)
		// Continue even if training fails
	}

	c.JSON(http.StatusOK, gin.H{"success": true})
}

// GetModelPerformanceStats handles GET /model-performance-stats/
func (h *Handler) GetModelPerformanceStats(c *gin.Context) {
	var model models.RecommendationModel
	var accuracy float64
	if err := h.db.Order("updated_at DESC").First(&model).Error; err == nil {
		accuracy = model.LastAccuracy
	}

	var metrics []models.RecommendationMetrics
	h.db.Order("session_date DESC").Find(&metrics)

	var sessions []gin.H
	for _, metric := range metrics {
		sessions = append(sessions, gin.H{
			"session_date": metric.SessionDate.Format("2006-01-02T15:04:05Z"),
			"accuracy":     metric.Accuracy,
			"precision":    metric.Precision,
			"num_samples":  metric.NumSamples,
		})
	}

	response := gin.H{
		"accuracy":      accuracy,
		"total_sessions": len(sessions),
		"sessions":      sessions,
	}

	c.JSON(http.StatusOK, response)
}

// ExportListingsCsv handles GET /export-listings
func (h *Handler) ExportListingsCsv(c *gin.Context) {
	var listings []models.Listing
	h.db.Preload("Record").Preload("Seller").
		Order("id DESC").Limit(5000).Find(&listings)

	c.Header("Content-Type", "text/csv")
	c.Header("Content-Disposition", "attachment; filename=listings_export.csv")

	writer := csv.NewWriter(c.Writer)
	defer writer.Flush()

	// Write headers
	headers := []string{
		"Listing ID", "Record Artist", "Record Title", "Record Label",
		"Record Format", "Record Year", "Seller", "Record Price",
		"Media Condition", "Score", "Kept", "Evaluated",
	}
	writer.Write(headers)

	// Write data
	for _, listing := range listings {
		year := ""
		if listing.Record.Year != nil {
			year = strconv.Itoa(*listing.Record.Year)
		}

		row := []string{
			strconv.Itoa(int(listing.ID)),
			listing.Record.Artist,
			listing.Record.Title,
			listing.Record.Label,
			listing.Record.Format,
			year,
			listing.Seller.Name,
			fmt.Sprintf("%.2f", listing.RecordPrice),
			listing.MediaCondition,
			fmt.Sprintf("%.2f", listing.Score),
			strconv.FormatBool(listing.Kept),
			strconv.FormatBool(listing.Evaluated),
		}
		writer.Write(row)
	}
}

// AddToWantlist handles POST /add-to-wantlist/
func (h *Handler) AddToWantlist(c *gin.Context) {
	recordID := c.PostForm("record_id")
	if recordID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "No record ID provided"})
		return
	}

	// This would typically call the Discogs API
	// For now, we'll just return a success message
	c.JSON(http.StatusOK, gin.H{"message": "Added to wantlist!"})
}

// VoteRecordOfTheDay handles POST /vote-record-of-the-day/:id/
func (h *Handler) VoteRecordOfTheDay(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid record ID"})
		return
	}

	desirabilityStr := c.PostForm("desirability")
	noveltyStr := c.PostForm("novelty")

	desirability, err := strconv.ParseFloat(desirabilityStr, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid desirability rating"})
		return
	}

	novelty, err := strconv.ParseFloat(noveltyStr, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid novelty rating"})
		return
	}

	// Get the record of the day
	var record models.RecordOfTheDay
	if err := h.db.First(&record, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Record of the day not found"})
		return
	}

	// Add votes
	record.DesirabilityVotes = append(record.DesirabilityVotes, desirability)
	record.NoveltyVotes = append(record.NoveltyVotes, novelty)

	// Calculate averages
	var desirabilitySum, noveltySum float64
	for _, vote := range record.DesirabilityVotes {
		desirabilitySum += vote
	}
	for _, vote := range record.NoveltyVotes {
		noveltySum += vote
	}

	record.AverageDesirability = desirabilitySum / float64(len(record.DesirabilityVotes))
	record.AverageNovelty = noveltySum / float64(len(record.NoveltyVotes))

	// Save to database
	if err := h.db.Save(&record).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save vote"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Vote submitted! Thanks for your feedback."})
}

// Go Scraper Endpoints

// TriggerGoScraper handles POST /api/scraper/go/:seller
func (h *Handler) TriggerGoScraper(c *gin.Context) {
	sellerName := c.Param("seller")
	if sellerName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Seller name is required"})
		return
	}

	if h.scraperService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Go scraper service is not available",
		})
		return
	}

	// Scrape the user's inventory
	result, err := h.scraperService.ScrapeUserInventory(sellerName)
	if err != nil {
		log.Printf("Error scraping inventory with Go scraper: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to scrape inventory: " + err.Error(),
		})
		return
	}

	if !result.Success {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": result.Error,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success":       true,
		"message":       fmt.Sprintf("Successfully scraped %d listings for %s", result.TotalRecords, sellerName),
		"username":      result.Username,
		"total_records": result.TotalRecords,
		"new_records":   result.NewRecords,
	})
}

// GetScraperStats handles GET /api/scraper/stats
func (h *Handler) GetScraperStats(c *gin.Context) {
	if h.scraperService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Go scraper service is not available",
		})
		return
	}

	stats, err := h.scraperService.GetScrapingStats()
	if err != nil {
		log.Printf("Error getting scraper stats: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get scraper stats: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, stats)
}

// TestScraperConnection handles GET /api/scraper/test
func (h *Handler) TestScraperConnection(c *gin.Context) {
	if h.scraperService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Go scraper service is not available",
		})
		return
	}

	err := h.scraperService.TestConnection()
	if err != nil {
		log.Printf("Scraper connection test failed: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"error":   "Connection test failed: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "Discogs API connection successful",
	})
}
