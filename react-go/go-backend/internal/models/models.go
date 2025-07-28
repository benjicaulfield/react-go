package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"strings"
	"time"
	"gorm.io/gorm"
)

// StringSlice is a custom type for handling JSON arrays in PostgreSQL
type StringSlice []string

// MarshalJSON implements the json.Marshaler interface
func (s StringSlice) MarshalJSON() ([]byte, error) {
	if s == nil {
		return []byte("[]"), nil
	}
	return json.Marshal([]string(s))
}

// UnmarshalJSON implements the json.Unmarshaler interface
func (s *StringSlice) UnmarshalJSON(data []byte) error {
	var slice []string
	if err := json.Unmarshal(data, &slice); err != nil {
		return err
	}
	*s = StringSlice(slice)
	return nil
}

func (s StringSlice) Value() (driver.Value, error) {
	if len(s) == 0 {
		return "[]", nil
	}
	return json.Marshal(s)
}

func (s *StringSlice) Scan(value interface{}) error {
	if value == nil {
		*s = StringSlice{}
		return nil
	}

	switch v := value.(type) {
	case []byte:
		return s.unmarshalValue(v)
	case string:
		return s.unmarshalValue([]byte(v))
	default:
		return errors.New("cannot scan into StringSlice")
	}
}

// unmarshalValue handles both JSON format and Python-style list format
func (s *StringSlice) unmarshalValue(data []byte) error {
	// Handle empty or null data
	if len(data) == 0 {
		*s = StringSlice{}
		return nil
	}
	
	// First try standard JSON unmarshaling
	if err := json.Unmarshal(data, s); err == nil {
		return nil
	}

	// If that fails, check if it's a Python-style list string
	str := string(data)
	
	// Handle various string formats
	// Remove outer quotes if present (double or single)
	if len(str) >= 2 {
		if (str[0] == '"' && str[len(str)-1] == '"') || (str[0] == '\'' && str[len(str)-1] == '\'') {
			str = str[1 : len(str)-1]
		}
	}
	
	// Handle empty string cases
	if str == "" || str == "[]" || str == "'[]'" || str == "\"[]\"" {
		*s = StringSlice{}
		return nil
	}
	
	// Check if it looks like a Python list
	if len(str) >= 2 && str[0] == '[' && str[len(str)-1] == ']' {
		// Convert Python-style single quotes to JSON double quotes
		// But be careful not to replace quotes inside strings
		converted := convertPythonListToJSON(str)
		
		// Try to unmarshal the converted string
		if err := json.Unmarshal([]byte(converted), s); err == nil {
			return nil
		}
	}
	
	// If it's not a list format, try to treat it as a single string value
	if !strings.HasPrefix(str, "[") {
		*s = StringSlice{str}
		return nil
	}
	
	// If all else fails, return empty slice to avoid breaking the application
	*s = StringSlice{}
	return nil
}

// convertPythonListToJSON converts Python-style list strings to JSON format
func convertPythonListToJSON(pythonList string) string {
	// Simple conversion: replace single quotes with double quotes
	// This is a basic implementation - for production, you might want a more robust parser
	result := strings.ReplaceAll(pythonList, "'", "\"")
	return result
}

// FloatSlice is a custom type for handling JSON arrays of floats
type FloatSlice []float64

func (f FloatSlice) Value() (driver.Value, error) {
	if len(f) == 0 {
		return "[]", nil
	}
	return json.Marshal(f)
}

func (f *FloatSlice) Scan(value interface{}) error {
	if value == nil {
		*f = FloatSlice{}
		return nil
	}

	switch v := value.(type) {
	case []byte:
		return json.Unmarshal(v, f)
	case string:
		return json.Unmarshal([]byte(v), f)
	default:
		return errors.New("cannot scan into FloatSlice")
	}
}

// Record represents a music record
type Record struct {
	ID             uint        `json:"id" gorm:"primaryKey"`
	DiscogsID      string      `json:"discogs_id" gorm:"uniqueIndex;not null"`
	Artist         string      `json:"artist" gorm:"not null"`
	Title          string      `json:"title" gorm:"not null"`
	Format         string      `json:"format" gorm:"default:''"`
	Label          string      `json:"label" gorm:"type:text"`
	Catno          *string     `json:"catno"`
	Wants          int         `json:"wants" gorm:"default:0"`
	Haves          int         `json:"haves" gorm:"default:0"`
	Added          time.Time   `json:"added" gorm:"default:CURRENT_TIMESTAMP"`
	Genres         StringSlice `json:"genres" gorm:"type:jsonb;default:'[]'"`
	Styles         StringSlice `json:"styles" gorm:"type:jsonb;default:'[]'"`
	SuggestedPrice string      `json:"suggested_price" gorm:"default:''"`
	Year           *int        `json:"year"`
}

// BeforeCreate prevents GORM from adding timestamp fields
func (r *Record) BeforeCreate(tx *gorm.DB) error {
	tx.Statement.Omit("created_at", "updated_at")
	return nil
}

// BeforeUpdate prevents GORM from adding timestamp fields
func (r *Record) BeforeUpdate(tx *gorm.DB) error {
	tx.Statement.Omit("created_at", "updated_at")
	return nil
}

// Seller represents a record seller
type Seller struct {
	ID       uint   `json:"id" gorm:"primaryKey"`
	Name     string `json:"name" gorm:"not null"`
	Currency string `json:"currency" gorm:"not null"`
}

// Listing represents a record listing by a seller
type Listing struct {
	ID              uint    `json:"id" gorm:"primaryKey"`
	SellerID        uint    `json:"seller_id" gorm:"not null"`
	Seller          Seller  `json:"seller" gorm:"foreignKey:SellerID"`
	RecordID        uint    `json:"record_id" gorm:"not null"`
	Record          Record  `json:"record" gorm:"foreignKey:RecordID"`
	RecordPrice     float64 `json:"record_price" gorm:"type:decimal(6,2);not null"`
	MediaCondition  string  `json:"media_condition" gorm:"not null"`
	Score           float64 `json:"score" gorm:"type:decimal(6,2);default:0.00"`
	Kept            bool    `json:"kept" gorm:"default:false"`
	Evaluated       bool    `json:"evaluated" gorm:"default:false"`
	PredictedKeeper bool    `json:"predicted_keeper" gorm:"default:false"`
}

// RecommendationModel stores ML model data
type RecommendationModel struct {
	ID              uint      `json:"id" gorm:"primaryKey"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
	ModelData       []byte    `json:"-" gorm:"type:bytea"`
	VectorizerData  []byte    `json:"-" gorm:"type:bytea"`
	ScalerData      []byte    `json:"-" gorm:"type:bytea"`
	FeatureNames    StringSlice `json:"feature_names" gorm:"type:jsonb;default:'[]'"`
	LastAccuracy    float64   `json:"last_accuracy" gorm:"default:0.0"`
	ModelVersion    string    `json:"model_version" gorm:"default:'v1.0'"`
}

// RecommendationMetrics tracks performance metrics
type RecommendationMetrics struct {
	ID          uint      `json:"id" gorm:"primaryKey"`
	SessionDate time.Time `json:"session_date" gorm:"autoCreateTime"`
	Accuracy    float64   `json:"accuracy"`
	Precision   float64   `json:"precision"`
	NumSamples  int       `json:"num_samples"`
	Notes       string    `json:"notes"`
}

// RecordOfTheDay tracks daily record selections
type RecordOfTheDay struct {
	ID                   uint       `json:"id" gorm:"primaryKey"`
	Date                 time.Time  `json:"date" gorm:"uniqueIndex;type:date"`
	ListingID            uint       `json:"listing_id" gorm:"not null"`
	Listing              Listing    `json:"listing" gorm:"foreignKey:ListingID"`
	CreatedAt            time.Time  `json:"created_at"`
	ModelScore           float64    `json:"model_score"`
	EntropyMeasure       float64    `json:"entropy_measure"`
	SystemTemperature    float64    `json:"system_temperature"`
	UtilityTerm          *float64   `json:"utility_term"`
	EntropyTerm          *float64   `json:"entropy_term"`
	FreeEnergy           *float64   `json:"free_energy"`
	SelectionProbability *float64   `json:"selection_probability"`
	TotalCandidates      *int       `json:"total_candidates"`
	ClusterCount         *int       `json:"cluster_count"`
	SelectionMethod      string     `json:"selection_method" gorm:"default:'thermodynamic_boltzmann'"`
	DesirabilityVotes    FloatSlice `json:"desirability_votes" gorm:"type:jsonb;default:'[]'"`
	NoveltyVotes         FloatSlice `json:"novelty_votes" gorm:"type:jsonb;default:'[]'"`
	AverageDesirability  float64    `json:"average_desirability" gorm:"default:0.0"`
	AverageNovelty       float64    `json:"average_novelty" gorm:"default:0.0"`
}

// RecordOfTheDayFeedback stores user feedback
type RecordOfTheDayFeedback struct {
	ID                 uint           `json:"id" gorm:"primaryKey"`
	RecordOfTheDayID   uint           `json:"record_of_the_day_id" gorm:"not null"`
	RecordOfTheDay     RecordOfTheDay `json:"record_of_the_day" gorm:"foreignKey:RecordOfTheDayID"`
	DesirabilityRating int            `json:"desirability_rating" gorm:"check:desirability_rating >= 1 AND desirability_rating <= 5"`
	NoveltyRating      int            `json:"novelty_rating" gorm:"check:novelty_rating >= 1 AND novelty_rating <= 5"`
	CreatedAt          time.Time      `json:"created_at"`
}

// TableName methods for custom table names to match Django
func (Record) TableName() string {
	return "discogs_record"
}

func (Seller) TableName() string {
	return "discogs_seller"
}

func (Listing) TableName() string {
	return "discogs_listing"
}

func (RecommendationModel) TableName() string {
	return "discogs_recommendationmodel"
}

func (RecommendationMetrics) TableName() string {
	return "discogs_recommendationmetrics"
}

func (RecordOfTheDay) TableName() string {
	return "discogs_recordoftheday"
}

func (RecordOfTheDayFeedback) TableName() string {
	return "discogs_recordofthedayfeedback"
}
