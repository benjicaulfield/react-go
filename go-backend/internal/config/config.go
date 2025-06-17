package config

import (
	"os"
)

type Config struct {
	Database DatabaseConfig
	Server   ServerConfig
	External ExternalConfig
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Name     string
	SSLMode  string
}

type ServerConfig struct {
	Port string
	Host string
}

type ExternalConfig struct {
	ScraperServiceURL      string
	RecommenderServiceURL  string
	ExchangeRateAPIKey     string
	DiscogsConsumerKey     string
	DiscogsConsumerSecret  string
}

func Load() *Config {
	return &Config{
		Database: DatabaseConfig{
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			User:     getEnv("DB_USER", "app"),
			Password: getEnv("DB_PASSWORD", "dairyman"),
			Name:     getEnv("DB_NAME", "records"),
			SSLMode:  getEnv("DB_SSLMODE", "disable"),
		},
		Server: ServerConfig{
			Port: getEnv("PORT", "8000"),
			Host: getEnv("HOST", "localhost"),
		},
		External: ExternalConfig{
			ScraperServiceURL:      getEnv("SCRAPER_SERVICE_URL", "http://localhost:8001"),
			RecommenderServiceURL:  getEnv("RECOMMENDER_SERVICE_URL", "http://localhost:8002"),
			ExchangeRateAPIKey:     getEnv("EXCHANGE_RATE_API_KEY", ""),
			DiscogsConsumerKey:     getEnv("DISCOGS_CONSUMER_KEY", ""),
			DiscogsConsumerSecret:  getEnv("DISCOGS_CONSUMER_SECRET", ""),
		},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
