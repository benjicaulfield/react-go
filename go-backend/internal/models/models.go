package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"
)

// StringSlice is a custom type for handling JSON arrays in PostgreSQL
type StringSlice []string

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
		return json.Unmarshal(v, s)
	case string:
		return json.Unmarshal([]byte(v), s)
	default:
		return errors.New("cannot scan into StringSlice")
	}
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
	CreatedAt      time.Time   `json:"created_at"`
	UpdatedAt      time.Time   `json:"updated_at"`
}

// Seller represents a record seller
type Seller struct {
	ID        uint      `json:"id" gorm:"primaryKey"`
	Name      string    `json:"name" gorm:"not null"`
	Currency  string    `json:"currency" gorm:"not null"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Listing represents a record listing by a seller
type Listing struct {
	ID               uint    `json:"id" gorm:"primaryKey"`
	SellerID         uint    `json:"seller_id" gorm:"not null"`
	Seller           Seller  `json:"seller" gorm:"foreignKey:SellerID"`
	RecordID         uint    `json:"record_id" gorm:"not null"`
	Record           Record  `json:"record" gorm:"foreignKey:RecordID"`
	RecordPrice      float64 `json:"record_price" gorm:"type:decimal(6,2);not null"`
	MediaCondition   string  `json:"media_condition" gorm:"not null"`
	Score            float64 `json:"score" gorm:"type:decimal(6,2);default:0.00"`
	Kept             bool    `json:"kept" gorm:"default:false"`
	Evaluated        bool    `json:"evaluated" gorm:"default:false"`
	PredictedKeeper  bool    `json:"predicted_keeper" gorm:"default:false"`
	CreatedAt        time.Time `json:"created_at"`
	UpdatedAt        time.Time `json:"updated_at"`
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
