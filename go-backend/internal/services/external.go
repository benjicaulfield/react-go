package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"discogs-api/internal/config"
)

type ExternalService struct {
	config     *config.Config
	httpClient *http.Client
}

func NewExternalService(cfg *config.Config) *ExternalService {
	return &ExternalService{
		config: cfg,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// ScraperRequest represents a request to the scraper microservice
type ScraperRequest struct {
	SellerName string `json:"seller_name"`
}

// ScraperResponse represents a response from the scraper microservice
type ScraperResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Error   string `json:"error,omitempty"`
}

// TriggerScraper calls the Python scraper microservice
func (s *ExternalService) TriggerScraper(sellerName string) (*ScraperResponse, error) {
	url := fmt.Sprintf("%s/scrape", s.config.External.ScraperServiceURL)
	
	reqBody := ScraperRequest{
		SellerName: sellerName,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	resp, err := s.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call scraper service: %w", err)
	}
	defer resp.Body.Close()
	
	var scraperResp ScraperResponse
	if err := json.NewDecoder(resp.Body).Decode(&scraperResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &scraperResp, nil
}

// RecommendationRequest represents a request to the recommendation microservice
type RecommendationRequest struct {
	ListingIDs []int `json:"listing_ids"`
}

// RecommendationResponse represents a response from the recommendation microservice
type RecommendationResponse struct {
	Predictions []RecommendationPrediction `json:"predictions"`
	Error       string                     `json:"error,omitempty"`
}

// RecommendationPrediction represents a single prediction
type RecommendationPrediction struct {
	ID          int     `json:"id"`
	Prediction  bool    `json:"prediction"`
	Probability float64 `json:"probability"`
}

// GetRecommendations calls the Python recommendation microservice
func (s *ExternalService) GetRecommendations(listingIDs []int) (*RecommendationResponse, error) {
	url := fmt.Sprintf("%s/predict", s.config.External.RecommenderServiceURL)
	
	reqBody := RecommendationRequest{
		ListingIDs: listingIDs,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	resp, err := s.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call recommendation service: %w", err)
	}
	defer resp.Body.Close()
	
	var recResp RecommendationResponse
	if err := json.NewDecoder(resp.Body).Decode(&recResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &recResp, nil
}

// TrainingRequest represents a request to train the recommendation model
type TrainingRequest struct {
	ListingIDs []int `json:"listing_ids"`
	KeeperIDs  []int `json:"keeper_ids"`
}

// TrainingResponse represents a response from model training
type TrainingResponse struct {
	Success  bool    `json:"success"`
	Accuracy float64 `json:"accuracy,omitempty"`
	Message  string  `json:"message"`
	Error    string  `json:"error,omitempty"`
}

// TrainModel calls the Python recommendation microservice to train the model
func (s *ExternalService) TrainModel(listingIDs, keeperIDs []int) (*TrainingResponse, error) {
	url := fmt.Sprintf("%s/train", s.config.External.RecommenderServiceURL)
	
	reqBody := TrainingRequest{
		ListingIDs: listingIDs,
		KeeperIDs:  keeperIDs,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	resp, err := s.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call recommendation service: %w", err)
	}
	defer resp.Body.Close()
	
	var trainResp TrainingResponse
	if err := json.NewDecoder(resp.Body).Decode(&trainResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &trainResp, nil
}

// ThermodynamicRequest represents a request for thermodynamic record selection
type ThermodynamicRequest struct {
	ForceRefresh bool `json:"force_refresh"`
}

// ThermodynamicResponse represents a response from thermodynamic selection
type ThermodynamicResponse struct {
	ListingID   int                    `json:"listing_id"`
	Breakdown   map[string]interface{} `json:"breakdown"`
	Success     bool                   `json:"success"`
	Error       string                 `json:"error,omitempty"`
}

// GetThermodynamicSelection calls the Python thermodynamic recommendation service
func (s *ExternalService) GetThermodynamicSelection(forceRefresh bool) (*ThermodynamicResponse, error) {
	url := fmt.Sprintf("%s/thermodynamic", s.config.External.RecommenderServiceURL)
	
	reqBody := ThermodynamicRequest{
		ForceRefresh: forceRefresh,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	resp, err := s.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call thermodynamic service: %w", err)
	}
	defer resp.Body.Close()
	
	var thermoResp ThermodynamicResponse
	if err := json.NewDecoder(resp.Body).Decode(&thermoResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &thermoResp, nil
}
