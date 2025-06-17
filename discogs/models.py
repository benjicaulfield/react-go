from django.db import models
from django.utils import timezone
import pickle

class Record(models.Model):
    discogs_id = models.CharField(max_length=255, unique=True)
    artist = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    format = models.CharField(max_length=255, default="")
    label = models.TextField()
    catno = models.CharField(max_length=255, null=True)
    wants = models.IntegerField(default=0)
    haves = models.IntegerField(default=0)
    added = models.DateTimeField(default=timezone.now)
    genres = models.JSONField(default=list)
    styles = models.JSONField(default=list)
    suggested_price = models.CharField(max_length=255, default="")
    year = models.IntegerField(null=True)

    class Meta:
        ordering = ["-added"]
        indexes = [
            models.Index(fields=["-added"]),
        ]

    def __str__(self):
        return self.title + " " + self.artist

class Seller(models.Model):
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name
    
class Listing(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    record_price = models.DecimalField(max_digits=6, decimal_places=2)
    media_condition = models.CharField(max_length=255)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    kept = models.BooleanField(default=False)
    evaluated = models.BooleanField(default=False)
    predicted_keeper = models.BooleanField(default=False)  # New field for model predictions
    
    def __str__(self):
        return f"{self.record.artist} '{self.record.title}': {self.record_price}, {self.score}"

class RecommendationModel(models.Model):
    """
    Stores the machine learning model and related data for the recommendation system
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    model_data = models.BinaryField(null=True, blank=True)
    vectorizer_data = models.BinaryField(null=True, blank=True)
    scaler_data = models.BinaryField(null=True, blank=True)  # For feature scaling
    feature_names = models.JSONField(default=list)
    last_accuracy = models.FloatField(default=0.0)
    model_version = models.CharField(max_length=50, default='v1.0')  # Track model versions
    
    def save_model(self, model, vectorizer, feature_names):
        """Save ML model, vectorizer, and feature names"""
        self.model_data = pickle.dumps(model)
        self.vectorizer_data = pickle.dumps(vectorizer)
        self.feature_names = feature_names
        self.save()
    
    def load_model(self):
        """Load ML model and vectorizer"""
        try:
            if self.model_data and self.vectorizer_data:
                return pickle.loads(self.model_data), pickle.loads(self.vectorizer_data), self.feature_names
            return None, None, []
        except Exception:
            return None, None, []

class RecommendationMetrics(models.Model):
    """
    Tracks performance metrics for recommendation sessions
    """
    session_date = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField()
    precision = models.FloatField()
    num_samples = models.IntegerField()
    notes = models.TextField(blank=True)

class RecordOfTheDay(models.Model):
    """
    Tracks daily record selections using thermodynamic computing
    """
    date = models.DateField(unique=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Thermodynamic selection breakdown
    model_score = models.FloatField()
    entropy_measure = models.FloatField()
    system_temperature = models.FloatField()
    utility_term = models.FloatField(null=True, blank=True)
    entropy_term = models.FloatField(null=True, blank=True) 
    free_energy = models.FloatField(null=True, blank=True)
    selection_probability = models.FloatField(null=True, blank=True)
    total_candidates = models.IntegerField(null=True, blank=True)
    cluster_count = models.IntegerField(null=True, blank=True)
    selection_method = models.CharField(max_length=50, default='thermodynamic_boltzmann')

    desirability_votes = models.JSONField(default=list)
    novelty_votes = models.JSONField(default=list)
    average_desirability = models.FloatField(default=0.0)
    average_novelty = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-date']
        
    def __str__(self):
        return f"Record of the Day {self.date}: {self.listing.record.artist} - {self.listing.record.title}"
    
class RecordOfTheDayFeedback(models.Model):
    record_of_the_day = models.ForeignKey(RecordOfTheDay, on_delete=models.CASCADE, related_name='feedback')
    desirability_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 scale
    novelty_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])      # 1-5 scale
    created_at = models.DateTimeField(auto_now_add=True)

        
    def __str__(self):
        return f"Feedback for {self.record_of_the_day.date} - D:{self.desirability_rating} N:{self.novelty_rating}"