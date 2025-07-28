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
    
    def __str__(self):
        return f"{self.record.artist} '{self.record.title}': {self.record_price}, {self.score}"
    
class RecommendationModel(models.Model):
    """
    Stores the persisted ML model, vectorizer, and metadata for the recommendation system.
    Only one instance should exist (enforced in views).
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    model_data = models.BinaryField(help_text="Pickled SGDClassifier model")
    vectorizer_data = models.BinaryField(help_text="Pickled TfidfVectorizer")
    feature_names = models.JSONField(default=list, help_text="List of feature names for consistency")
    last_accuracy = models.FloatField(default=0.0, help_text="Last computed accuracy")

    def save_model(self, model, vectorizer, feature_names):
        self.model_data = pickle.dumps(model)
        self.vectorizer_data = pickle.dumps(vectorizer), 
        self.feature_names = feature_names
        self.save()

    def load_model(self):
        return pickle.loads(self.model_data), pickle.loads(self.vectorizer_data), self.feature_names

class RecommendationMetrics(models.Model):
    """
    Tracks model performance over sessions for display.
    """
    session_date = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField()
    precision = models.FloatField()
    num_samples = models.IntegerField()
    notes = models.TextField(blank=True)
