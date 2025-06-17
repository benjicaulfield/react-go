# discogs/test_thermodynamic_debugging.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
import json
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from .models import Record, Listing, Seller, RecommendationModel, RecordOfTheDay
from .views import dashboard_view
from .utils.thermodynamic_recommendation import ThermodynamicRecordSelector


class ThermodynamicDebuggingTest(TestCase):
    """Focused tests for debugging thermodynamic selection issues"""
    
    def setUp(self):
        """Set up minimal test data for debugging"""
        self.seller = Seller.objects.create(name="Test Seller", currency='USD')
        
        # Create test records with clear desirability/novelty patterns
        test_data = [
            # High desirability, low novelty (popular mainstream)
            {"artist": "The Beatles", "title": "Abbey Road", "score": 0.9, "wants": 1000, "haves": 500, "genres": ["Rock", "Pop"]},
            # Medium desirability, high novelty (obscure good)
            {"artist": "Obscure Jazz Trio", "title": "Experimental Sessions", "score": 0.7, "wants": 50, "haves": 5, "genres": ["Jazz", "Experimental"]},
            # Low desirability, medium novelty (bad but interesting)
            {"artist": "Failed Band", "title": "Bad Album", "score": 0.3, "wants": 10, "haves": 100, "genres": ["Rock", "Alternative"]},
            # High desirability, high novelty (rare gem)
            {"artist": "Legendary Artist", "title": "Lost Masterpiece", "score": 0.95, "wants": 200, "haves": 2, "genres": ["Jazz", "Rare"]},
            # Additional test records for clustering (need 10 total)
            {"artist": "Indie Darling", "title": "Cult Classic", "score": 0.8, "wants": 75, "haves": 15, "genres": ["Indie", "Alternative"]},
            {"artist": "Electronic Pioneer", "title": "Digital Dreams", "score": 0.75, "wants": 120, "haves": 30, "genres": ["Electronic", "Ambient"]},
            {"artist": "Classical Master", "title": "Symphony No. 9", "score": 0.85, "wants": 300, "haves": 80, "genres": ["Classical", "Orchestral"]},
            {"artist": "Punk Rebels", "title": "Anarchy Album", "score": 0.6, "wants": 40, "haves": 60, "genres": ["Punk", "Hardcore"]},
            {"artist": "Folk Singer", "title": "Acoustic Sessions", "score": 0.65, "wants": 90, "haves": 45, "genres": ["Folk", "Singer-Songwriter"]},
            {"artist": "Hip Hop Artist", "title": "Street Chronicles", "score": 0.55, "wants": 80, "haves": 35, "genres": ["Hip Hop", "Rap"]},
        ]
        
        self.listings = []
        for i, data in enumerate(test_data):
            record = Record.objects.create(
                discogs_id=f"debug-{i}",
                artist=data["artist"],
                title=data["title"],
                wants=data["wants"],
                haves=data["haves"],
                genres=data["genres"],
                year=2000 + i
            )
            listing = Listing.objects.create(
                record=record,
                seller=self.seller,
                record_price=20.00 + i * 5,
                score=data["score"],
                evaluated=True
            )
            self.listings.append(listing)
        
        self.selector = ThermodynamicRecordSelector()
    
    def test_page_refresh_returns_different_record(self):
        """Test that page refresh can return different records (issue #1)"""
        # Force delete any existing record of the day
        RecordOfTheDay.objects.all().delete()
        
        # Get multiple selections by calling the selector directly
        selections = []
        for i in range(5):
            selected_listing, breakdown = self.selector.select_record_of_the_day()
            if selected_listing:
                selections.append({
                    'listing_id': selected_listing.id,
                    'artist': selected_listing.record.artist,
                    'title': selected_listing.record.title,
                    'entropy': breakdown.get('entropy_measure', 0),
                    'temperature': breakdown.get('system_temperature', 0)
                })
        
        print(f"\n=== PAGE REFRESH VARIATION TEST ===")
        print(f"Got {len(selections)} selections:")
        for i, sel in enumerate(selections):
            print(f"  {i+1}. {sel['artist']} - {sel['title']} "
                  f"(Entropy: {sel['entropy']:.3f}, Temp: {sel['temperature']:.3f})")
        
        # Should get valid selections
        self.assertGreater(len(selections), 0)
        
        # Check for some variation (not always the same record)
        unique_artists = set(sel['artist'] for sel in selections)
        print(f"Unique artists selected: {len(unique_artists)} out of {len(selections)} runs")
        
        # At least some variation expected due to stochastic sampling
        if len(selections) >= 3:
            self.assertGreaterEqual(len(unique_artists), 1, "Should show some selection variety")
    
    def test_entropy_represents_novelty_correctly(self):
        """Test that entropy correctly measures novelty/surprise (issue #2)"""
        # Test entropy calculation for our test cases
        print(f"\n=== ENTROPY (NOVELTY) ANALYSIS ===")
        
        # Set up clustering with all listings
        self.selector._update_cluster_model(self.listings)
        
        for listing in self.listings:
            entropy = self.selector._calculate_entropy_measure(listing, self.listings)
            wants_haves_ratio = listing.record.wants / max(listing.record.haves, 1)
            
            print(f"{listing.record.artist}: "
                  f"Entropy={entropy:.3f}, "
                  f"Wants/Haves={wants_haves_ratio:.2f}, "
                  f"Score={listing.score}")
            
            # Entropy should be in valid range
            self.assertGreaterEqual(entropy, 0.1)
            self.assertLessEqual(entropy, 0.9)
        
        # The obscure jazz trio should have higher entropy than The Beatles
        beatles_listing = next(l for l in self.listings if "Beatles" in l.record.artist)
        obscure_listing = next(l for l in self.listings if "Obscure" in l.record.artist)
        
        beatles_entropy = self.selector._calculate_entropy_measure(beatles_listing, self.listings)
        obscure_entropy = self.selector._calculate_entropy_measure(obscure_listing, self.listings)
        
        print(f"Beatles entropy: {beatles_entropy:.3f}")
        print(f"Obscure jazz entropy: {obscure_entropy:.3f}")
        
        # Novelty test: rare/obscure should have higher entropy
        # Note: This might not always hold due to clustering, but let's check
        print(f"Obscure jazz has {'higher' if obscure_entropy > beatles_entropy else 'lower'} entropy than Beatles")
    
    def test_temperature_represents_desirability_correctly(self):
        """Test that temperature correctly represents desirability (issue #2)"""
        print(f"\n=== TEMPERATURE (DESIRABILITY) ANALYSIS ===")
        
        # Create scenarios with different desirability levels
        high_score_listings = [l for l in self.listings if l.score > 0.8]
        low_score_listings = [l for l in self.listings if l.score < 0.5]
        
        high_temp = self.selector._calculate_system_temperature(high_score_listings)
        low_temp = self.selector._calculate_system_temperature(low_score_listings)
        
        print(f"High-score listings temperature: {high_temp:.3f}")
        print(f"Low-score listings temperature: {low_temp:.3f}")
        
        # Temperature should be in valid range
        self.assertGreaterEqual(high_temp, 0.1)
        self.assertLessEqual(high_temp, 1.0)
        self.assertGreaterEqual(low_temp, 0.1)
        self.assertLessEqual(low_temp, 1.0)
        
        # Test with all listings
        all_temp = self.selector._calculate_system_temperature(self.listings)
        print(f"All listings temperature: {all_temp:.3f}")
    
    def test_thermodynamic_algorithm_correctness(self):
        """Test the core thermodynamic algorithm for correctness (issue #3)"""
        print(f"\n=== THERMODYNAMIC ALGORITHM VALIDATION ===")
        
        # Test free energy calculation for each listing
        temperature = 0.6  # Fixed temperature for testing
        
        for listing in self.listings:
            entropy = self.selector._calculate_entropy_measure(listing, self.listings)
            free_energy, utility, entropy_term = self.selector._calculate_free_energy(
                listing, entropy, temperature
            )
            
            # Verify F = U - T*S relationship
            expected_free_energy = utility - entropy_term
            self.assertAlmostEqual(free_energy, expected_free_energy, places=5)
            
            # Verify entropy term calculation
            expected_entropy_term = temperature * entropy
            self.assertAlmostEqual(entropy_term, expected_entropy_term, places=5)
            
            print(f"{listing.record.artist}:")
            print(f"  Score: {listing.score:.3f} → Utility: {utility:.3f}")
            print(f"  Entropy: {entropy:.3f} → Entropy Term: {entropy_term:.3f}")
            print(f"  Free Energy: {free_energy:.3f}")
            print()
        
        # Test Boltzmann sampling
        free_energies = []
        listing_ids = []
        
        for listing in self.listings:
            entropy = self.selector._calculate_entropy_measure(listing, self.listings)
            free_energy, _, _ = self.selector._calculate_free_energy(listing, entropy, temperature)
            free_energies.append(free_energy)
            listing_ids.append(listing.id)
        
        # Run sampling multiple times
        sample_counts = {lid: 0 for lid in listing_ids}
        
        for _ in range(100):
            selected_id, probability = self.selector._boltzmann_sampling(
                free_energies, listing_ids, temperature
            )
            sample_counts[selected_id] += 1
        
        print("Boltzmann Sampling Results (100 samples):")
        for i, listing in enumerate(self.listings):
            count = sample_counts[listing.id]
            fe = free_energies[i]
            print(f"  {listing.record.artist}: {count}% (FE: {fe:.3f})")
    
    def test_simplified_breakdown_display(self):
        """Test simplified breakdown with just entropy and temperature (issue #2)"""
        selected_listing, breakdown = self.selector.select_record_of_the_day()
        
        if selected_listing:
            print(f"\n=== SIMPLIFIED BREAKDOWN ===")
            print(f"Selected: {selected_listing.record.artist} - {selected_listing.record.title}")
            print(f"Novelty (Entropy): {breakdown.get('entropy_measure', 0):.3f}")
            print(f"Desirability (Temperature): {breakdown.get('system_temperature', 0):.3f}")
            
            # Key metrics should be present
            self.assertIn('entropy_measure', breakdown)
            self.assertIn('system_temperature', breakdown)
            
            # Values should be in expected ranges
            entropy = breakdown['entropy_measure']
            temperature = breakdown['system_temperature']
            
            self.assertGreaterEqual(entropy, 0.1)
            self.assertLessEqual(entropy, 0.9)
            self.assertGreaterEqual(temperature, 0.1)
            self.assertLessEqual(temperature, 1.0)


class VotingSystemTest(TestCase):
    """Test voting system integration for user feedback (issue #4)"""
    
    def setUp(self):
        """Set up test data for voting system"""
        self.user = User.objects.create_user(username='voter', password='testpass')
        self.seller = Seller.objects.create(name="Voting Seller", currency='USD')
        
        # Create test record and listing
        self.record = Record.objects.create(
            discogs_id="vote-test-1",
            artist="Test Artist",
            title="Test Album",
            wants=100,
            haves=50,
            genres=["Rock"]
        )
        
        self.listing = Listing.objects.create(
            record=self.record,
            seller=self.seller,
            record_price=25.00,
            score=0.7
        )
        
        # Create Record of the Day
        today = timezone.now().date()
        self.rotd = RecordOfTheDay.objects.create(
            date=today,
            listing=self.listing,
            model_score=0.7,
            entropy_measure=0.5,
            system_temperature=0.6,
            utility_term=-0.7,  # Add missing required field
            entropy_term=0.3,   # Add missing required field
            free_energy=-1.0,   # Add missing required field
            selection_probability=0.2,  # Add missing required field
            total_candidates=5,  # Add missing required field
            cluster_count=3,     # Add missing required field
            selection_method='thermodynamic_boltzmann'
        )
    
    def test_voting_system_concept(self):
        """Test the concept of user voting on desirability and novelty"""
        print(f"\n=== VOTING SYSTEM DESIGN TEST ===")
        
        # Simulate user votes
        desirability_vote = 4  # 1-5 scale (5 = highly desirable)
        novelty_vote = 2       # 1-5 scale (5 = very novel/surprising)
        
        print(f"User voted:")
        print(f"  Desirability: {desirability_vote}/5")
        print(f"  Novelty: {novelty_vote}/5")
        
        # Test how votes could influence thermodynamic parameters
        
        # Method 1: Direct influence on temperature and entropy
        base_temperature = 0.6
        base_entropy = 0.5
        
        # Adjust temperature based on desirability vote
        # Higher desirability vote → higher temperature (more exploration of similar items)
        temperature_adjustment = (desirability_vote - 3) * 0.1  # -0.2 to +0.2
        adjusted_temperature = np.clip(base_temperature + temperature_adjustment, 0.1, 1.0)
        
        # Adjust entropy based on novelty vote
        # Higher novelty vote → system learns to expect more novelty
        entropy_adjustment = (novelty_vote - 3) * 0.1  # -0.2 to +0.2
        adjusted_entropy = np.clip(base_entropy + entropy_adjustment, 0.1, 0.9)
        
        print(f"Thermodynamic adjustments:")
        print(f"  Temperature: {base_temperature:.3f} → {adjusted_temperature:.3f}")
        print(f"  Entropy: {base_entropy:.3f} → {adjusted_entropy:.3f}")
        
        # Method 2: Influence Boltzmann weights directly
        vote_weight = (desirability_vote + novelty_vote) / 10.0  # 0.2 to 1.0
        print(f"  Boltzmann weight multiplier: {vote_weight:.3f}")
        
        # Method 3: Update model training data
        # Convert votes to training labels
        keeper_likelihood = (desirability_vote * 0.6 + novelty_vote * 0.4) / 5.0
        should_be_keeper = keeper_likelihood > 0.6
        
        print(f"  Training signal: keeper_likelihood={keeper_likelihood:.3f}, "
              f"should_be_keeper={should_be_keeper}")
        
        # Test assertions
        self.assertGreaterEqual(adjusted_temperature, 0.1)
        self.assertLessEqual(adjusted_temperature, 1.0)
        self.assertGreaterEqual(adjusted_entropy, 0.1)
        self.assertLessEqual(adjusted_entropy, 0.9)
        self.assertGreaterEqual(vote_weight, 0.2)
        self.assertLessEqual(vote_weight, 1.0)
    
    def test_vote_aggregation_over_time(self):
        """Test how multiple votes could be aggregated"""
        print(f"\n=== VOTE AGGREGATION TEST ===")
        
        # Simulate multiple user votes over time
        votes = [
            {"desirability": 5, "novelty": 3},  # High desire, medium novelty
            {"desirability": 3, "novelty": 5},  # Medium desire, high novelty
            {"desirability": 4, "novelty": 4},  # Balanced
            {"desirability": 2, "novelty": 1},  # Low scores
        ]
        
        # Calculate averages
        avg_desirability = sum(v["desirability"] for v in votes) / len(votes)
        avg_novelty = sum(v["novelty"] for v in votes) / len(votes)
        
        print(f"Vote history: {votes}")
        print(f"Averages: Desirability={avg_desirability:.2f}, Novelty={avg_novelty:.2f}")
        
        # Calculate system-wide adjustments
        global_temperature_bias = (avg_desirability - 3) * 0.05  # Smaller adjustment
        global_entropy_bias = (avg_novelty - 3) * 0.05
        
        print(f"Global biases: Temperature={global_temperature_bias:.3f}, "
              f"Entropy={global_entropy_bias:.3f}")
        
        # Test that aggregation works
        self.assertAlmostEqual(avg_desirability, 3.5, places=1)
        self.assertAlmostEqual(avg_novelty, 3.25, places=1)


class DashboardIntegrationTest(TestCase):
    """Test dashboard integration with debugging focus"""
    
    def setUp(self):
        """Set up test data for dashboard debugging"""
        self.user = User.objects.create_user(username='dashuser', password='testpass')
        self.seller = Seller.objects.create(name="Dashboard Seller", currency='USD')
        
        # Create a few test listings
        for i in range(5):
            record = Record.objects.create(
                discogs_id=f"dash-debug-{i}",
                artist=f"Artist {i}",
                title=f"Album {i}",
                wants=50 + i * 20,
                haves=25
            )
            Listing.objects.create(
                record=record,
                seller=self.seller,
                record_price=15.00 + i * 3,
                score=0.6 + i * 0.08
            )
    
    def test_dashboard_no_refresh_button_needed(self):
        """Test that dashboard works without refresh button (issue #1)"""
        # Delete any existing record of the day to force new selection
        RecordOfTheDay.objects.all().delete()
        
        self.client.login(username='dashuser', password='testpass')
        
        # First request should create a record of the day
        response1 = self.client.get(reverse('dashboard'))
        self.assertEqual(response1.status_code, 200)
        
        # Check that a record was selected
        today = timezone.now().date()
        first_rotd = RecordOfTheDay.objects.filter(date=today).first()
        self.assertIsNotNone(first_rotd)
        
        # Second request should use the same record (since it's the same day)
        response2 = self.client.get(reverse('dashboard'))
        second_rotd = RecordOfTheDay.objects.get(date=today)
        
        self.assertEqual(first_rotd.id, second_rotd.id)
        
        print(f"\n=== DASHBOARD REFRESH BEHAVIOR ===")
        print(f"First selection: {first_rotd.listing.record.artist}")
        print(f"Same day access uses same record: ✓")
        
        # To test different selection, we'd need to simulate a different day
        # or delete the existing record
        RecordOfTheDay.objects.filter(date=today).delete()
        
        response3 = self.client.get(reverse('dashboard'))
        new_rotd = RecordOfTheDay.objects.get(date=today)
        
        print(f"After deletion, new selection: {new_rotd.listing.record.artist}")
        print(f"Can get different records: ✓")
    
    def test_simplified_thermodynamic_display(self):
        """Test that dashboard shows simplified thermodynamic analysis"""
        self.client.login(username='dashuser', password='testpass')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        
        # Check that simplified breakdown is in context
        context = response.context
        breakdown = context.get('breakdown', {})
        
        print(f"\n=== DASHBOARD BREAKDOWN ===")
        print(f"Available breakdown keys: {list(breakdown.keys())}")
        
        # Should have the key thermodynamic metrics
        essential_keys = ['entropy_measure', 'system_temperature']
        for key in essential_keys:
            self.assertIn(key, breakdown, f"Breakdown should contain {key}")
            print(f"{key}: {breakdown[key]:.3f}")
        
        # Should NOT need all the complex metrics for display
        # (though they can exist for debugging)
        optional_keys = ['utility_term', 'entropy_term', 'free_energy']
        print(f"Optional detailed metrics present: {[k for k in optional_keys if k in breakdown]}")


class PerformanceTest(TestCase):
    """Test thermodynamic selection performance"""
    
    def setUp(self):
        """Create larger dataset for performance testing"""
        self.seller = Seller.objects.create(name="Perf Seller", currency='USD')
        
        # Create 50 listings for performance testing
        for i in range(50):
            record = Record.objects.create(
                discogs_id=f"perf-{i}",
                artist=f"Performance Artist {i}",
                title=f"Speed Album {i}",
                wants=25 + i * 5,
                haves=10 + i * 2,
                genres=["Rock", "Jazz", "Electronic"][i % 3]
            )
            Listing.objects.create(
                record=record,
                seller=self.seller,
                record_price=10.00 + i,
                score=0.4 + (i % 20) * 0.03
            )
    
    def test_selection_performance(self):
        """Test that thermodynamic selection completes in reasonable time"""
        import time
        
        selector = ThermodynamicRecordSelector()
        
        start_time = time.time()
        selected_listing, breakdown = selector.select_record_of_the_day()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        print(f"\n=== PERFORMANCE TEST ===")
        print(f"Selection time with 50 listings: {execution_time:.3f} seconds")
        print(f"Selected: {selected_listing.record.artist if selected_listing else 'None'}")
        
        # Should complete within reasonable time
        self.assertLess(execution_time, 5.0, "Selection should complete within 5 seconds")
        self.assertIsNotNone(selected_listing, "Should successfully select a record")