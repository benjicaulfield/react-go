from django.contrib import admin
from .models import Record, Seller, Listing, RecommendationModel, RecommendationMetrics, RecordOfTheDay

admin.site.register(Record)
admin.site.register(Seller)
admin.site.register(Listing)
admin.site.register(RecommendationModel)
admin.site.register(RecommendationMetrics)
admin.site.register(RecordOfTheDay)

# Register your models here.
