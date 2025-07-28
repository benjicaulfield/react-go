package scraper

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

const InventoryFileName = "user_inventories.json"

// InventoryFile represents the structure of the inventory JSON file
type InventoryFile map[string]UserInventoryData

// LoadInventoryJSON loads the inventory tracking file
func LoadInventoryJSON() (InventoryFile, error) {
	if _, err := os.Stat(InventoryFileName); os.IsNotExist(err) {
		return make(InventoryFile), nil
	}

	data, err := os.ReadFile(InventoryFileName)
	if err != nil {
		return nil, fmt.Errorf("failed to read inventory file: %w", err)
	}

	var inventory InventoryFile
	if err := json.Unmarshal(data, &inventory); err != nil {
		return nil, fmt.Errorf("failed to unmarshal inventory: %w", err)
	}

	return inventory, nil
}

// SaveInventoryJSON saves the inventory tracking file
func SaveInventoryJSON(inventory InventoryFile) error {
	data, err := json.MarshalIndent(inventory, "", "    ")
	if err != nil {
		return fmt.Errorf("failed to marshal inventory: %w", err)
	}

	if err := os.WriteFile(InventoryFileName, data, 0644); err != nil {
		return fmt.Errorf("failed to write inventory file: %w", err)
	}

	return nil
}

// UpdateUserInventory updates the inventory tracking for a specific user
func UpdateUserInventory(username string, recordIDs []int) error {
	inventory, err := LoadInventoryJSON()
	if err != nil {
		return fmt.Errorf("failed to load inventory: %w", err)
	}

	today := time.Now().Format("2006-01-02")

	if existingData, exists := inventory[username]; exists {
		// Merge new IDs with existing ones, keeping only unique IDs
		existingIDs := existingData.RecordIDs
		allIDs := recordIDs

		// Add existing IDs that aren't in the new list
		for _, existingID := range existingIDs {
			found := false
			for _, newID := range recordIDs {
				if existingID == newID {
					found = true
					break
				}
			}
			if !found {
				allIDs = append(allIDs, existingID)
			}
		}

		// Keep only the last 50 IDs
		if len(allIDs) > 50 {
			allIDs = allIDs[:50]
		}

		inventory[username] = UserInventoryData{
			LastInventory: today,
			RecordIDs:     allIDs,
		}
	} else {
		// New user
		inventory[username] = UserInventoryData{
			LastInventory: today,
			RecordIDs:     recordIDs,
		}
	}

	return SaveInventoryJSON(inventory)
}

// GetUserInventory retrieves the inventory data for a specific user
func GetUserInventory(username string) (*UserInventoryData, error) {
	inventory, err := LoadInventoryJSON()
	if err != nil {
		return nil, fmt.Errorf("failed to load inventory: %w", err)
	}

	if data, exists := inventory[username]; exists {
		return &data, nil
	}

	return &UserInventoryData{
		LastInventory: "",
		RecordIDs:     []int{},
	}, nil
}

// HasSeenRecord checks if a record ID has been seen before for a user
func HasSeenRecord(username string, recordID int) (bool, error) {
	userData, err := GetUserInventory(username)
	if err != nil {
		return false, err
	}

	for _, id := range userData.RecordIDs {
		if id == recordID {
			return true, nil
		}
	}

	return false, nil
}
