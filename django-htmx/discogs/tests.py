# tests.py
import json
import os
from unittest import mock
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from rest_framework import status
from rest_framework.test import APIClient
from requests_mock import Mocker
from .models import Listing, Record, Seller
from .views import (
    ScraperDataToDatabaseView, ScraperDataToDatabaseBySellerView,
    dashboard_listings_view, search_seller_view
)

class ScrapeDataIntegrationTest(TestCase):
    """Test the data scraping functionality in isolation."""
    
    def setUp(self):
        """Set up test environment before each test method."""
        self.factory = RequestFactory()
        self.client = APIClient()
        # Create a test user for authentication
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        """Clean up test environment after each test method."""
        self.client.logout()

    @mock.patch.dict(os.environ, {"EXCHANGE_RATE_API_KEY": "test_key"})
    def test_scraper_data_flow(self):
        """Test the scraping data flow from API calls to database storage."""
        with transaction.atomic():
            with Mocker() as m:
                # Mock external API responses
                mock_discogs_data = [
                    {
                        "discogs_id": 1,
                        "artist": "Test Artist",
                        "title": "Test Title",
                        "format": "Vinyl",
                        "label": "Test Label",
                        "catno": "TEST001",
                        "wants": 10,
                        "haves": 5,
                        "genres": ["Rock"],
                        "styles": ["Classic Rock"],
                        "year": 1990,
                        "record_price": (10.0, "USD"),
                        "media_condition": "Mint (M)",
                        "seller": "test_seller"
                    }
                ]

                mock_exchange_rate_response = {
                    "result": "success",
                    "conversion_rates": {
                        "USD": 1,
                        "EUR": 0.85
                    }
                }

                # Setup mock responses for external APIs
                m.get('https://v6.exchangerate-api.com/v6/test_key/latest/USD', 
                     text=json.dumps(mock_exchange_rate_response))
                
                # Mock OAuth token endpoint
                m.post('https://oauth2.googleapis.com/token', 
                     json={'access_token': 'test_token', 'refresh_token': 'test_refresh'})
                
                # Mock Discogs endpoints
                m.post('https://api.discogs.com/oauth/request_token', 
                      text='oauth_token=test_token&oauth_token_secret=test_secret')
                m.post('https://api.discogs.com/oauth/access_token', 
                      text='oauth_token=test_token&oauth_token_secret=test_secret')
                m.get('https://api.discogs.com/users/test_seller/inventory', 
                     text=json.dumps(mock_discogs_data))
                
                # Fix 1: Mock the get_exchange_rates method directly on the view class
                with mock.patch.object(ScraperDataToDatabaseView, 'get_exchange_rates', 
                                     return_value=mock_exchange_rate_response.get('conversion_rates', {})):
                    
                    # Mock Gmail service and usernames
                    gmail_service_patcher = mock.patch('discogs.views.get_gmail_service', 
                                                    return_value=mock.MagicMock())
                    gmail_service_mock = gmail_service_patcher.start()
                    self.addCleanup(gmail_service_patcher.stop)
                    
                    usernames_patcher = mock.patch('discogs.views.get_usernames', 
                                                return_value=["test_seller"])
                    usernames_mock = usernames_patcher.start()
                    self.addCleanup(usernames_patcher.stop)
                    
                    # Mock inventory retrieval
                    inventory_patcher = mock.patch('discogs.views.get_inventory', 
                                                return_value=mock_discogs_data)
                    inventory_mock = inventory_patcher.start()
                    self.addCleanup(inventory_patcher.stop)

                    # Test scraping and database population
                    response = self.client.post(reverse('data-receive'), {}, format='json')
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

                    # Verify data is stored in the database
                    self.assertEqual(Record.objects.count(), 1)
                    self.assertEqual(Listing.objects.count(), 1)
                    
                    # Verify record details
                    record = Record.objects.first()
                    self.assertEqual(record.artist, "Test Artist")
                    self.assertEqual(record.title, "Test Title")
                    
                    # Verify listing details
                    listing = Listing.objects.first()
                    self.assertEqual(listing.record_price, 10.0)
                    self.assertEqual(listing.media_condition, "Mint (M)")


class HTMXIntegrationTest(TestCase):
    """Test the HTMX endpoints and rendering."""
    
    def setUp(self):
        """Set up test data and environment."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='12345')
        
        # Create test data
        self.seller = Seller.objects.create(name='test_seller', currency='USD')
        self.record = Record.objects.create(
            discogs_id=1,
            artist="Test Artist",
            title="Test Title",
            format="Vinyl",
            label="Test Label",
            catno="TEST001",
            wants=10,
            haves=5,
            genres=["Rock"],
            styles=["Classic Rock"],
            year=1990
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            record=self.record,
            record_price=10.0,
            media_condition="Mint (M)",
            kept=False,
            evaluated=False
        )

    def test_dashboard_listings_view(self):
        """Test the dashboard listings HTMX endpoint."""
        request = self.factory.get(reverse('dashboard_listings'))
        request.user = self.user
        
        # Add session to request
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        response = dashboard_listings_view(request)
        self.assertEqual(response.status_code, 200)
        
        # Fix 2: Update the HTML structure check to match the actual template
        self.assertContains(response, "Test Artist")
        self.assertContains(response, "Test Title")
        
        # Use actual HTML elements from the template
        self.assertContains(response, '<table class="w-full border-collapse')
        self.assertContains(response, '<tbody>')
        self.assertContains(response, '<tr class="hover:bg-gray-900')
        
    def test_search_seller_view(self):
        """Test the search seller HTMX endpoint."""
        request = self.factory.post(reverse('search-seller'), data={'seller': 'test_seller'})
        request.user = self.user
        
        # Add session to request
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        response = search_seller_view(request)
        self.assertEqual(response.status_code, 200)
        
        # Check for seller-specific content
        self.assertContains(response, "Test Artist")
        self.assertContains(response, "Test Title")
        
        # Check for basic HTML structure
        self.assertContains(response, '<table')
        self.assertContains(response, '<tbody>')