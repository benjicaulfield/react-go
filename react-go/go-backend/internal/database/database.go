package database

import (
	"fmt"
	"log"

	"discogs-api/internal/config"
	"discogs-api/internal/models"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// Initialize creates a new database connection
func Initialize(cfg config.DatabaseConfig) (*gorm.DB, error) {
	dsn := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Name, cfg.SSLMode,
	)

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Get underlying sql.DB to configure connection pool
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get underlying sql.DB: %w", err)
	}

	// Configure connection pool
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)

	log.Println("Database connection established")
	return db, nil
}

// AutoMigrate runs database migrations
func AutoMigrate(db *gorm.DB) error {
	log.Println("Running database migrations...")

	// Note: We're not auto-migrating since we want to use existing Django tables
	// Instead, we'll just verify the connection works
	var count int64
	if err := db.Raw("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'").Scan(&count).Error; err != nil {
		return fmt.Errorf("failed to verify database connection: %w", err)
	}

	log.Printf("Database verified - found %d tables", count)
	return nil
}

// CreateTables creates all tables (for testing or fresh installs)
func CreateTables(db *gorm.DB) error {
	log.Println("Creating database tables...")

	err := db.AutoMigrate(
		&models.Record{},
		&models.Seller{},
		&models.Listing{},
		&models.RecommendationModel{},
		&models.RecommendationMetrics{},
		&models.RecordOfTheDay{},
		&models.RecordOfTheDayFeedback{},
	)
	if err != nil {
		return fmt.Errorf("failed to migrate database: %w", err)
	}

	log.Println("Database tables created successfully")
	return nil
}
