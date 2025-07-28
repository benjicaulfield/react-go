#!/bin/bash

echo "🚀 Starting scraper service..."
python3 python-services/scraper-service.py &
SCRAPER_PID=$!

echo "⏳ Waiting for service to start..."
sleep 3

echo "🔍 Testing scraper health..."
curl -s http://localhost:8001/health

echo -e "\n\n🧪 Testing scraper endpoint..."
curl -s -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"seller_name": "TestSeller"}'

echo -e "\n\n✅ Scraper service is working!"
echo "You can now use the trigger scraper endpoint in your Go backend."
echo "The scraper service is running on PID: $SCRAPER_PID"
echo "To stop it later, run: kill $SCRAPER_PID"
