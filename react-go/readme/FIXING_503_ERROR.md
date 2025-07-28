"# Fixing the 503 Error in Seller Trigger

## Problem
The seller trigger is returning a 503 error when submitting a user name. This is caused by invalid or missing Discogs API credentials.

## Root Cause
The error occurs because:
1. The Discogs API keys in `.env` are placeholders (`your_discogs_consumer_key_here`)
2. The scraper cannot authenticate with the Discogs API
3. This results in a 503 Service Unavailable error

## Solution

### Step 1: Get Discogs API Keys
1. Go to https://www.discogs.com/developers
2. Create a Discogs account if you don't have one
3. Create a new application to get your Consumer Key and Consumer Secret
4. Note: You may need to wait for approval (usually quick)

### Step 2: Update .env File
Update the `.env` file with your real Discogs API keys:

```env
# Replace these placeholders with your real keys
DISCOGS_CONSUMER_KEY=your_actual_consumer_key_here
DISCOGS_CONSUMER_SECRET=your_actual_consumer_secret_here
```

### Step 3: Restart the Server
1. Stop the current server: `pkill -f 'go run main.go'`
2. Restart the server: `cd go-backend && go run main.go &`

### Step 4: Test the Fix
1. Test the API: `curl -X POST http://localhost:8000/api/scraper/go/testuser`
2. If it works, you should see a success message instead of the 503 error

## Troubleshooting

### Common Issues
1. **Invalid Consumer Error**: Your API keys are invalid. Double-check them.
2. **Rate Limiting**: Discogs has rate limits. If you get 429 errors, wait and try again.
3. **Network Issues**: Ensure you have internet access and Discogs API is reachable.

### Testing the Scraper
You can test the scraper directly:
```bash
cd go-backend
go run test_scraper.go
```

If you still get errors:
- Check your internet connection
- Verify your API keys are correct
- Ensure you're not being rate limited

## Expected Behavior
Once fixed, the seller trigger should:
1. Accept a seller name
2. Scrape the seller's inventory from Discogs
3. Filter listings based on criteria (LP format, good condition, wants > haves)
4. Stop when it finds a previously seen listing or reaches the end
5. Save new listings to the database
6. Display the results on the seller trigger page

## Additional Notes
- The scraper respects Discogs rate limits (1 request per second)
- It uses OAuth 1.0 authentication
- It maintains an inventory tracking file to avoid duplicates
- The frontend will show a loading spinner during scraping

If you continue to have issues, check the server logs for more detailed error messages."
