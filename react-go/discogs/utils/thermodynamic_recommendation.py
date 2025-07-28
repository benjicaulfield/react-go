import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import euclidean_distances
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import Listing, Record, RecommendationModel, RecordOfTheDay
import pickle

logger = logging.getLogger(__name__)

class ThermodynamicRecordSelector:
    """
    Thermodynamic computing approach to record selection based on free energy minimization.
    Balances exploitation (high utility) with exploration (high entropy/novelty).
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)
        self.cluster_model = KMeans(n_clusters=5, random_state=42)
        self.recent_listings_cache = None
        self.cluster_centroids = None
        self.feature_cache = None
        self.is_fitted = False
        
    def _extract_listing_features(self, listings):
        """Extract comprehensive features from listings for vectorization"""
        features = []
        text_data = []
        
        for listing in listings:
            record = listing.record
            
            # Text features for semantic analysis
            text_content = f"{record.artist} {record.title} {record.label} {' '.join(record.genres or [])} {' '.join(record.styles or [])}"
            text_data.append(text_content)
            
            # Numerical features
            wants_haves_ratio = record.wants / max(record.haves, 1)
            price_normalized = float(listing.record_price) / 100.0  # Normalize price
            
            feature_dict = {
                'price_normalized': price_normalized,
                'wants': record.wants,
                'haves': record.haves,
                'wants_haves_ratio': wants_haves_ratio,
                'year': record.year if record.year else 1970,  # Default year
                'score': float(listing.score),
                'listing_id': listing.id
            }
            features.append(feature_dict)
        
        return features, text_data
    
    def _build_feature_vectors(self, listings, fit_transformers=False):
        """Build comprehensive feature vectors combining text and numerical features"""
        if not listings:
            return np.array([]), []
            
        features, text_data = self._extract_listing_features(listings)
        df = pd.DataFrame(features)
        listing_ids = df['listing_id'].values
        df = df.drop('listing_id', axis=1)
        
        # Process text features
        if not self.is_fitted or fit_transformers:
            text_features = self.vectorizer.fit_transform(text_data)
            self.is_fitted = True
        else:
            try:
                text_features = self.vectorizer.transform(text_data)
            except Exception:
                # If vectorizer not fitted, fit it now
                text_features = self.vectorizer.fit_transform(text_data)
        
        # Combine numerical and text features
        numerical_features = df.values
        combined_features = np.hstack([numerical_features, text_features.toarray()])
        
        # Scale features
        if fit_transformers:
            combined_features = self.scaler.fit_transform(combined_features)
        else:
            try:
                combined_features = self.scaler.transform(combined_features)
            except Exception:
                # If scaler not fitted, fit it now
                combined_features = self.scaler.fit_transform(combined_features)
        
        return combined_features, listing_ids
    
    def _update_cluster_model(self, recent_listings):
        """Update clustering model with recent listings to establish distribution centroids"""
        try:
            if len(recent_listings) < 5:  # Need minimum listings for clustering
                logger.warning("Insufficient recent listings for clustering")
                return False
            if self.recent_listings_cache == recent_listings:
                logger.info("Using cached cluster model")
                return True
            self.recent_listings_cache = recent_listings
                
            # Build feature vectors
            feature_vectors, _ = self._build_feature_vectors(recent_listings, fit_transformers=True)
            
            if feature_vectors.shape[0] == 0:
                return False
            
            # Apply PCA for dimensionality reduction
            if feature_vectors.shape[1] > 10:
                feature_vectors = self.pca.fit_transform(feature_vectors)
            
            # Fit clustering model
            self.cluster_model.fit(feature_vectors)
            self.cluster_centroids = self.cluster_model.cluster_centers_
            self.feature_cache = feature_vectors
            
            logger.info(f"Updated cluster model with {len(recent_listings)} recent listings")
            return True
            
        except Exception as e:
            logger.error(f"Error updating cluster model: {e}")
            return False
    
    def _calculate_entropy_measure(self, listing, recent_listings):
        """
        Calculate entropy-weighted novelty measure based on distance from cluster centroids.
        Higher values indicate more surprising/novel listings.
        """
        try:
            if self.cluster_centroids is None:
                # If no clusters available, use a default entropy measure
                return np.random.uniform(0.3, 0.7)  # Random baseline entropy
            
            # Get feature vector for this listing
            feature_vector, _ = self._build_feature_vectors([listing])
            
            if feature_vector.shape[0] == 0:
                return 0.5  # Default entropy
            
            # Apply same transformations as training data
            if feature_vector.shape[1] > 10:
                try:
                    feature_vector = self.pca.transform(feature_vector)
                except Exception:
                    # If PCA not fitted properly, return default
                    return 0.5
            
            # Calculate minimum distance to any cluster centroid
            distances = euclidean_distances(feature_vector, self.cluster_centroids)
            min_distance = np.min(distances)
            
            # Normalize distance to [0, 1] range (entropy measure)
            # Higher distance = higher entropy (more surprising)
            max_possible_distance = np.max(euclidean_distances(self.cluster_centroids, self.cluster_centroids))
            if max_possible_distance > 0:
                entropy_measure = min_distance / (max_possible_distance + 1e-6)
            else:
                entropy_measure = 0.5
            
            # Ensure entropy is in reasonable range
            entropy_measure = np.clip(entropy_measure, 0.1, 0.9)

            similar_records = RecordOfTheDay.objects.filter(listing__record__genres__overlap=listing.record.genres)[:5]
            avg_novelty = sum(r.average_novelty for r in similar_records) / max(1, len(similar_records))
            entropy_measure *= (1 + 0.3 * avg_novelty)
            
            return entropy_measure
            
        except Exception as e:
            logger.error(f"Error calculating entropy measure: {e}")
            return 0.5  # Default entropy on error
    
    def _calculate_system_temperature(self, eligible_listings):
        """
        Calculate system temperature based on contextual metrics.
        Higher temperature = more exploration, Lower temperature = more exploitation.
        """
        try:
            total_listings = len(eligible_listings)
            unevaluated_count = sum(1 for listing in eligible_listings if not listing.evaluated)
            
            # Base temperature on proportion of unevaluated listings
            unevaluated_ratio = unevaluated_count / max(total_listings, 1)
            
            # Model uncertainty proxy: variance in scores
            scores = [float(listing.score) for listing in eligible_listings if listing.score > 0]
            if scores:
                score_variance = np.var(scores)
                score_std = np.std(scores)
                # Normalize variance to contribute to temperature
                uncertainty_factor = min(score_std / (np.mean(scores) + 1e-6), 1.0)
            else:
                uncertainty_factor = 0.5
            
            # Combine factors to determine temperature
            # High unevaluated ratio or high uncertainty -> higher temperature (more exploration)
            base_temperature = 0.5
            exploration_boost = 0.3 * unevaluated_ratio + 0.2 * uncertainty_factor
            
            past_records = RecordOfTheDay.objects.all()[:10]
            avg_desirability = sum(r.average_desirability for r in past_records)

            temperature = (base_temperature + exploration_boost) * (1 + 0.2 * avg_desirability)
            temperature = np.clip(temperature, 0.1, 1.0)  # Keep in reasonable range
            
            logger.info(f"System temperature: {temperature:.3f} (unevaluated_ratio: {unevaluated_ratio:.3f}, uncertainty: {uncertainty_factor:.3f})")
            
            return temperature
            
        except Exception as e:
            logger.error(f"Error calculating system temperature: {e}")
            return 0.5  # Default temperature
    
    def _calculate_free_energy(self, listing, entropy_measure, temperature):
        """
        Calculate virtual free energy: F = U - T*S
        Where U is utility (model score), T is temperature, S is entropy (novelty)
        Lower free energy = more likely to be selected
        """
        try:
            # Utility term (energy) - use negative score so lower is better
            utility = -float(listing.score) if listing.score > 0 else -1.0
            
            # Entropy term (novelty bonus)
            entropy_term = temperature * entropy_measure
            
            # Free energy = Utility - Temperature * Entropy
            free_energy = utility - entropy_term
            
            return free_energy, utility, entropy_term
            
        except Exception as e:
            logger.error(f"Error calculating free energy: {e}")
            return 0.0, 0.0, 0.0
    
    def _boltzmann_sampling(self, free_energies, listing_ids, temperature):
        """
        Sample from Boltzmann distribution over inverse free energy.
        More surprising records still have a chance to be selected.
        """
        try:
            # Convert to numpy arrays
            free_energies = np.array(free_energies)
            
            # Calculate Boltzmann weights: exp(-F/T)
            # Lower free energy -> higher probability
            boltzmann_weights = np.exp(-free_energies / temperature)
            
            # Normalize to get probabilities
            probabilities = boltzmann_weights / np.sum(boltzmann_weights)
            
            # Sample according to probabilities
            selected_idx = np.random.choice(len(listing_ids), p=probabilities)
            selected_id = listing_ids[selected_idx]
            
            return selected_id, probabilities[selected_idx]
            
        except Exception as e:
            logger.error(f"Error in Boltzmann sampling: {e}")
            # Fallback to random selection
            return np.random.choice(listing_ids), 1.0 / len(listing_ids)
    
    def select_record_of_the_day(self, max_candidates=50):
        """
        Main method to select Record of the Day using thermodynamic principles.
        Returns the selected listing with breakdown of contributing factors.
        """
        try:
            # Get eligible listings (high-scoring, recent, not already featured today)
            today = timezone.now().date()
            
            # Get recent high-scoring listings as candidates
            eligible_listings = list(
                Listing.objects.filter(
                    score__gt=0.5,  # Minimum quality threshold
                ).order_by('-score')[:max_candidates]
            )
            
            if not eligible_listings:
                logger.warning("No eligible listings found for Record of the Day")
                return None, {}
            
            # Get recent listings for clustering (last 7 days or last 200 listings)
            recent_cutoff = timezone.now() - timedelta(days=7)
            recent_listings = list(
                Listing.objects.filter(
                    record__added__gte=recent_cutoff
                ).order_by('-record__added')[:100]
            )
            
            if not recent_listings:
                recent_listings = eligible_listings  # Fallback
            
            # Update clustering model with recent listings
            self._update_cluster_model(recent_listings)
            
            # Calculate system temperature
            temperature = self._calculate_system_temperature(eligible_listings)
            
            # Calculate free energy for each eligible listing
            free_energies = []
            entropy_measures = []
            utility_terms = []
            entropy_terms = []
            listing_ids = []
            
            for listing in eligible_listings:
                entropy_measure = self._calculate_entropy_measure(listing, recent_listings)
                free_energy, utility, entropy_term = self._calculate_free_energy(
                    listing, entropy_measure, temperature
                )
                
                free_energies.append(free_energy)
                entropy_measures.append(entropy_measure)
                utility_terms.append(utility)
                entropy_terms.append(entropy_term)
                listing_ids.append(listing.id)
            
            # Select using Boltzmann sampling
            selected_id, selection_probability = self._boltzmann_sampling(
                free_energies, listing_ids, temperature
            )
            
            # Get the selected listing
            selected_listing = next(
                (listing for listing in eligible_listings if listing.id == selected_id),
                eligible_listings[0]  # Fallback
            )
            
            # Prepare breakdown information
            selected_idx = listing_ids.index(selected_id)
            breakdown = {
                'model_score': float(selected_listing.score),
                'entropy_measure': entropy_measures[selected_idx],
                'system_temperature': temperature,
                'utility_term': utility_terms[selected_idx],
                'entropy_term': entropy_terms[selected_idx],
                'free_energy': free_energies[selected_idx],
                'selection_probability': selection_probability,
                'total_candidates': len(eligible_listings),
                'cluster_count': len(self.cluster_centroids) if self.cluster_centroids is not None else 0,
                'selection_method': 'thermodynamic_boltzmann'
            }
            
            logger.info(f"Selected Record of the Day: {selected_listing.record.artist} - {selected_listing.record.title}")
            logger.info(f"Selection breakdown: {breakdown}")
            
            return selected_listing, breakdown
            
        except Exception as e:
            logger.error(f"Error selecting Record of the Day: {e}")
            # Fallback to highest scoring listing
            try:
                fallback_listing = Listing.objects.filter(score__gt=0).order_by('-score').first()
                return fallback_listing, {'error': str(e), 'selection_method': 'fallback'}
            except Exception:
                return None, {'error': str(e)}
            

