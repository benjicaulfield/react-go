package scraper

import (
	"log"
	"sync"
	"time"
)

// RateLimitTracker implements sliding window rate limiting for Discogs API
type RateLimitTracker struct {
	mu                  sync.Mutex
	windows             []int
	currentWindowStart  time.Time
	currentCount        int
	sleepTime           time.Duration
	targetRate          float64
	windowDuration      time.Duration
	maxWindowCount      int
}

// NewRateLimitTracker creates a new rate limit tracker
// Discogs allows 60 requests per minute, so we use 15-second windows with max 15 requests per window
func NewRateLimitTracker() *RateLimitTracker {
	return &RateLimitTracker{
		windows:        make([]int, 0, 4), // Keep last 4 windows (1 minute)
		targetRate:     0.9,               // 90% of the limit to be safe
		windowDuration: 15 * time.Second,  // 15-second windows
		maxWindowCount: 15,                // Max 15 requests per 15-second window
		sleepTime:      0,
		currentWindowStart: time.Now(),
	}
}

// AddRequest records a new request and applies rate limiting
func (r *RateLimitTracker) AddRequest(endpoint string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	currentTime := time.Now()

	// Check if we need to start a new window
	if currentTime.Sub(r.currentWindowStart) >= r.windowDuration {
		// Add current window to history
		r.windows = append(r.windows, r.currentCount)
		
		// Keep only the last 4 windows (1 minute total)
		if len(r.windows) > 4 {
			r.windows = r.windows[1:]
		}

		// Calculate total requests in the last minute
		total := r.currentCount
		for _, count := range r.windows {
			total += count
		}

		log.Printf("Window complete - Total requests in last minute: %d", total)

		// Adjust sleep time based on total requests
		if total > 45 { // 75% of 60 requests per minute
			r.sleepTime += 100 * time.Millisecond
		} else if total < 40 { // Less than 67% of limit
			r.sleepTime = maxDuration(0, r.sleepTime-100*time.Millisecond)
		}

		// Reset for new window
		r.currentCount = 0
		r.currentWindowStart = currentTime
	}

	r.currentCount++
}

// Sleep applies the current sleep duration
func (r *RateLimitTracker) Sleep() {
	r.mu.Lock()
	sleepDuration := r.sleepTime
	r.mu.Unlock()

	if sleepDuration > 0 {
		time.Sleep(sleepDuration)
	}
}

// GetCurrentRate returns the current request rate information
func (r *RateLimitTracker) GetCurrentRate() (int, time.Duration) {
	r.mu.Lock()
	defer r.mu.Unlock()

	total := r.currentCount
	for _, count := range r.windows {
		total += count
	}

	return total, r.sleepTime
}

func maxDuration(a, b time.Duration) time.Duration {
	if a > b {
		return a
	}
	return b
}
