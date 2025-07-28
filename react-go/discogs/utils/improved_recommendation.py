import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import logging
import pickle
from ..models import RecommendationModel, RecommendationMetrics, Listing, Record

logger = logging.getLogger(__name__)

class ImprovedRecordRecommender:
    """Enhanced machine learning model for record recommendations"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a new one if none exists"""
        try:
            model_obj = RecommendationModel.objects.first()
            if model_obj:
                model_data = model_obj.load_model()
                if model_data[0] is not None:
                    self.model, self.vectorizer, self.feature_names = model_data
                    # Try to load scaler if it exists
                    if hasattr(model_obj, 'scaler_data') and model_obj.scaler_data:
                        try:
                            self.scaler = pickle.loads(model_obj.scaler_data)
                        except:
                            self.scaler = StandardScaler()  # Create new if loading fails
                    else:
                        self.scaler = StandardScaler()  # Create new if doesn't exist
                    self.is_trained = True
                    logger.info("Loaded existing recommendation model")
                    return
            
            # Create new model if none exists or loading failed
            self._initialize_model()
            logger.info("Initialized new recommendation model")
            
        except Exception as e:
            logger.error(f"Error loading recommendation model: {e}")
            self._initialize_model()
    
    def _initialize_model(self):
        """Create a new model with optimized parameters"""
        # Text vectorizer for artist, title, label, genres, styles
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            stop_words='english',
            max_features=300,
            min_df=2,
            max_df=0.95,
            ngram_range=(1, 2)  # Include bigrams for better context
        )
        
        # Random forest with better parameters
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced',
            bootstrap=True,
            oob_score=True
        )
        
        # Scaler for numerical features
        self.scaler = StandardScaler()
        
        self.feature_names = [
            'price', 'wants', 'haves', 'wants_haves_ratio', 
            'year', 'price_per_want', 'rarity_score', 'condition_score'
        ]
        self.is_trained = False
    
    def _extract_features(self, listings):
        """Extract comprehensive features from listings"""
        if not listings:
            return None, None, None
            
        features = []
        text_data = []
        listing_ids = []
        
        for listing in listings:
            record = listing.record
            listing_ids.append(listing.id)
            
            # Extract text for TF-IDF analysis
            text_content = f"{record.artist} {record.title} {record.label} {' '.join(record.genres or [])} {' '.join(record.styles or [])}"
            text_data.append(text_content)
            
            # Calculate enhanced numerical features
            wants = max(record.wants, 1)
            haves = max(record.haves, 1)
            wants_haves_ratio = wants / haves
            price = float(listing.record_price)
            price_per_want = price / wants if wants > 0 else price
            
            # Rarity score (higher wants/haves ratio + lower haves = rarer)
            rarity_score = wants_haves_ratio * (1 / (1 + np.log(haves)))
            
            # Condition score (convert condition to numerical)
            condition_map = {
                'Mint (M)': 1.0,
                'Near Mint (NM or M-)': 0.9,
                'Very Good Plus (VG+)': 0.8,
                'Very Good (VG)': 0.7,
                'Good Plus (G+)': 0.6,
                'Good (G)': 0.5,
                'Fair (F)': 0.3,
                'Poor (P)': 0.1
            }
            condition_score = condition_map.get(listing.media_condition, 0.5)
            
            feature_dict = {
                'price': price,
                'wants': wants,
                'haves': haves,
                'wants_haves_ratio': wants_haves_ratio,
                'year': record.year if record.year else 1980,  # Default to 1980 if no year
                'price_per_want': price_per_want,
                'rarity_score': rarity_score,
                'condition_score': condition_score
            }
            features.append(feature_dict)
        
        # Create DataFrame from numerical features
        df = pd.DataFrame(features)
        
        return df, listing_ids, text_data
    
    def _combine_features(self, numerical_df, text_data, fit_vectorizer=False):
        """Combine numerical and text features"""
        # Process text features
        if fit_vectorizer or not hasattr(self.vectorizer, 'vocabulary_'):
            if text_data:
                self.vectorizer.fit(text_data)
            else:
                # Fit with dummy data if no text available
                self.vectorizer.fit(["dummy text for initialization"])
        
        # Transform text data
        if text_data:
            text_features = self.vectorizer.transform(text_data)
            text_df = pd.DataFrame(
                text_features.toarray(),
                columns=[f'text_{i}' for i in range(text_features.shape[1])]
            )
        else:
            # Create empty text features if no data
            n_text_features = len(self.vectorizer.get_feature_names_out()) if hasattr(self.vectorizer, 'vocabulary_') else 300
            text_df = pd.DataFrame(
                np.zeros((len(numerical_df), n_text_features)),
                columns=[f'text_{i}' for i in range(n_text_features)]
            )
        
        # Scale numerical features
        if fit_vectorizer:
            numerical_scaled = self.scaler.fit_transform(numerical_df)
        else:
            numerical_scaled = self.scaler.transform(numerical_df)
        
        numerical_scaled_df = pd.DataFrame(
            numerical_scaled,
            columns=numerical_df.columns
        )
        
        # Combine features
        combined_df = pd.concat([numerical_scaled_df, text_df], axis=1)
        
        return combined_df
    
    def predict(self, listings):
        """Predict which listings are likely to be kept"""
        if not self.model or not self.is_trained or not listings:
            # Return default predictions if model not trained
            return {listing.id: 0.5 for listing in listings}
            
        try:
            numerical_df, listing_ids, text_data = self._extract_features(listings)
            if numerical_df is None or numerical_df.empty:
                return {listing.id: 0.5 for listing in listings}
            
            # Combine features
            features = self._combine_features(numerical_df, text_data, fit_vectorizer=False)
            
            # Make predictions
            predictions = self.model.predict_proba(features)
            
            # Create prediction dictionary
            prediction_dict = {}
            for i, listing_id in enumerate(listing_ids):
                # Get probability of positive class (keeper)
                prob = predictions[i][1] if len(predictions[i]) > 1 else 0.5
                prediction_dict[listing_id] = float(prob)
            
            return prediction_dict
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            # Return default predictions on error
            return {listing.id: 0.5 for listing in listings}
    
    def train(self, keeper_ids, all_listing_ids):
        """Train the model with new data"""
        try:
            # Get all listings that were evaluated
            listings = list(Listing.objects.filter(id__in=all_listing_ids))
            if not listings:
                logger.warning("No listings found for training")
                return False
            
            # Extract features
            numerical_df, listing_ids, text_data = self._extract_features(listings)
            if numerical_df is None or numerical_df.empty:
                logger.warning("No features extracted for training")
                return False
            
            # Create target labels
            labels = np.array([1 if lid in keeper_ids else 0 for lid in listing_ids])
            
            # Ensure we have both classes for training
            if len(np.unique(labels)) < 2:
                logger.warning("Training data contains only one class, adding synthetic sample")
                # Add a synthetic sample of the missing class
                missing_class = 0 if 1 in labels else 1
                # Duplicate the first row and assign missing class
                numerical_df = pd.concat([numerical_df, numerical_df.iloc[[0]]], ignore_index=True)
                text_data.append(text_data[0] if text_data else "synthetic sample")
                labels = np.append(labels, missing_class)
            
            # Combine features
            features = self._combine_features(numerical_df, text_data, fit_vectorizer=True)
            
            # Train the model
            self.model.fit(features, labels)
            self.is_trained = True
            
            # Calculate metrics
            predictions = self.model.predict(features)
            probabilities = self.model.predict_proba(features)[:, 1]
            
            accuracy = accuracy_score(labels, predictions)
            precision = precision_score(labels, predictions, zero_division=0)
            recall = recall_score(labels, predictions, zero_division=0)
            f1 = f1_score(labels, predictions, zero_division=0)
            
            # Get feature importance
            feature_importance = {}
            if hasattr(self.model, 'feature_importances_'):
                feature_names = list(numerical_df.columns) + [f'text_{i}' for i in range(len(self.vectorizer.get_feature_names_out()))]
                for name, importance in zip(feature_names, self.model.feature_importances_):
                    feature_importance[name] = float(importance)
            
            # Save metrics
            RecommendationMetrics.objects.create(
                accuracy=accuracy,
                precision=precision,
                num_samples=len(labels),
                notes=f"Recall: {recall:.3f}, F1: {f1:.3f}, OOB Score: {getattr(self.model, 'oob_score_', 'N/A')}"
            )
            
            # Update model in database
            model_obj = RecommendationModel.objects.first()
            if not model_obj:
                model_obj = RecommendationModel()
            
            model_obj.last_accuracy = accuracy
            model_obj.save_model(self.model, self.vectorizer, list(features.columns))
            
            # Save scaler separately (extend the model if needed)
            try:
                model_obj.scaler_data = pickle.dumps(self.scaler)
                model_obj.save()
            except:
                pass  # Ignore if scaler_data field doesn't exist
            
            logger.info(f"Model trained successfully. Accuracy: {accuracy:.3f}, Precision: {precision:.3f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False
    
    def get_feature_importance(self):
        """Get feature importance from the trained model"""
        if not self.model or not self.is_trained:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importance_dict = {}
            # Get top 10 most important features
            indices = np.argsort(self.model.feature_importances_)[-10:]
            for i in indices:
                if i < len(self.feature_names):
                    importance_dict[self.feature_names[i]] = float(self.model.feature_importances_[i])
                else:
                    importance_dict[f'text_feature_{i}'] = float(self.model.feature_importances_[i])
            return importance_dict
        
        return {}
    
    def get_model_stats(self):
        """Get comprehensive model statistics"""
        stats = {
            'is_trained': self.is_trained,
            'model_type': type(self.model).__name__ if self.model else None,
            'n_features': len(self.feature_names),
            'oob_score': getattr(self.model, 'oob_score_', None) if self.is_trained else None
        }
        
        # Get latest metrics
        try:
            latest_metrics = RecommendationMetrics.objects.latest('session_date')
            stats.update({
                'latest_accuracy': latest_metrics.accuracy,
                'latest_precision': latest_metrics.precision,
                'latest_samples': latest_metrics.num_samples,
                'latest_session': latest_metrics.session_date
            })
        except RecommendationMetrics.DoesNotExist:
            pass
        
        return stats
