import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
import logging
from ..models import RecommendationModel, RecommendationMetrics, Listing, Record

logger = logging.getLogger(__name__)

class RecordRecommender:
    """Machine learning model for record recommendations"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.feature_names = []
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a new one if none exists"""
        try:
            model_obj = RecommendationModel.objects.first()
            if not model_obj:
                model_obj = RecommendationModel.objects.create()
                self._initialize_model()
                model_obj.save_model(self.model, self.vectorizer, self.feature_names)
            else:
                self.model, self.vectorizer = model_obj.load_model()
                self.feature_names = model_obj.feature_names
                
                # If model couldn't be loaded, initialize a new one
                if self.model is None:
                    self._initialize_model()
                    model_obj.save_model(self.model, self.vectorizer, self.feature_names)
        except Exception as e:
            logger.error(f"Error loading recommendation model: {e}")
            self._initialize_model()
    
    def _initialize_model(self):
        """Create a new model with default parameters"""
        self.vectorizer = CountVectorizer(
            analyzer='word',
            stop_words='english',
            max_features=200,
            min_df=2
        )
        
        # Simple random forest classifier to start with
        self.model = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.feature_names = [
            'price', 'wants', 'haves', 'wants_haves_ratio', 
            'year', 'text_features'
        ]
    
    def _extract_features(self, listings):
        """Extract features from listings for prediction or training"""
        if not listings:
            return None
            
        features = []
        text_data = []
        
        for listing in listings:
            record = listing.record
            
            # Extract text for bag-of-words analysis
            text_content = f"{record.artist} {record.title} {record.label} {' '.join(record.genres)} {' '.join(record.styles)}"
            text_data.append(text_content)
            
            # Calculate wants/haves ratio safely
            wants_haves_ratio = record.wants / max(record.haves, 1)
            
            # Extract numerical features
            feature_dict = {
                'price': float(listing.record_price),
                'wants': record.wants,
                'haves': record.haves,
                'wants_haves_ratio': wants_haves_ratio,
                'year': record.year if record.year else 0,
                'listing_id': listing.id  # Keep track of listing ID
            }
            features.append(feature_dict)
        
        # Create DataFrame from features
        df = pd.DataFrame(features)
        listing_ids = df['listing_id'].values
        df = df.drop('listing_id', axis=1)
        
        # Process text features if vectorizer is trained
        if self.vectorizer:
            try:
                text_features = self.vectorizer.transform(text_data)
                # Convert to DataFrame for easier handling
                text_df = pd.DataFrame(
                    text_features.toarray(),
                    columns=[f'text_{i}' for i in range(text_features.shape[1])]
                )
                # Combine numerical and text features
                df = pd.concat([df, text_df], axis=1)
            except Exception as e:
                logger.error(f"Error processing text features: {e}")
        
        return df, listing_ids, text_data
    
    def predict(self, listings):
        """Predict which listings are likely to be kept"""
        if not self.model or not listings:
            return {}
            
        try:
            features, listing_ids, _ = self._extract_features(listings)
            if features.empty:
                return {}
                
            # Make predictions
            predictions = self.model.predict_proba(features)
            
            # Create a dictionary mapping listing IDs to prediction probabilities
            prediction_dict = {
                int(listing_id): float(pred[1])  # Probability of class 1 (keeper)
                for listing_id, pred in zip(listing_ids, predictions)
            }
            
            return prediction_dict
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return {}
    
    def train(self, keeper_ids, all_listing_ids):
        """Train the model with new data"""
        try:
            # Get all listings that were evaluated
            listings = Listing.objects.filter(id__in=all_listing_ids)
            if not listings:
                return False
                
            # Extract features
            features, listing_ids, text_data = self._extract_features(listings)
            if features.empty:
                return False
            
            # Create target labels (1 for keepers, 0 for non-keepers)
            labels = np.array([1 if lid in keeper_ids else 0 for lid in listing_ids])
            
            # Train or update text vectorizer
            if not self.vectorizer.vocabulary_:
                self.vectorizer.fit(text_data)
                # Re-extract features with trained vectorizer
                features, listing_ids, _ = self._extract_features(listings)
            
            # Train the model
            self.model.fit(features, labels)
            
            # Calculate accuracy
            predictions = self.model.predict(features)
            accuracy = np.mean(predictions == labels)
            precision = np.sum((predictions == 1) & (labels == 1)) / max(np.sum(predictions == 1), 1)
            
            # Save metrics
            RecommendationMetrics.objects.create(
                accuracy=accuracy,
                precision=precision,
                num_samples=len(labels)
            )
            
            # Update model in database
            model_obj = RecommendationModel.objects.first()
            if model_obj:
                model_obj.last_accuracy = accuracy
                model_obj.save_model(self.model, self.vectorizer, self.feature_names)
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False