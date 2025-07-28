from django.urls import path
from .views import home_view, dashboard_view, dashboard_listings_view
from .views import search_seller_view, by_seller_view, seller_trigger_view
from .views import scoring_view, tune_scoring_view, export_listings_csv
from .views import ScraperDataToDatabaseView, ScraperDataToDatabaseBySellerView
from .views import recommender_view, recommendation_predictions_view, submit_recommendations_view
from .views import recommendation_tuner_view, recommendation_tuner_predictions_view, model_performance_stats_view
from .views import add_to_wantlist, scraper_status_view

urlpatterns = [
    path("", home_view, name="home"),
    path("api/data/", ScraperDataToDatabaseView.as_view(), name="data-receive"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("dashboard/listings/", dashboard_listings_view, name="dashboard_listings"),
    path("by-seller/", by_seller_view, name="by-seller"),
    path("by-seller/search/", search_seller_view, name="search-seller"),
    path("data/<str:seller>/",  ScraperDataToDatabaseBySellerView.as_view(), name="data-receive-by-seller"),
    path("seller-trigger/", seller_trigger_view, name="seller-trigger"),
    path("scoring/", scoring_view, name="scoring"),
    path("tune-scoring/", tune_scoring_view, name="tune-scoring"),
    path("export-listings/", export_listings_csv, name="export-listings"),
    path('recommender/', recommender_view, name='recommender'),
    path('recommendation-predictions/', recommendation_predictions_view, name='recommendation_predictions'),
    path('submit-recommendations/', submit_recommendations_view, name='submit_recommendations'),
    path('recommendation-tuner/', recommendation_tuner_view, name='recommendation_tuner'),
    path('recommendation-tuner-predictions/', recommendation_tuner_predictions_view, name='recommendation_tuner_predictions'),
    path('model-performance-stats/', model_performance_stats_view, name='model_performance_stats'),
    path('add-to-wantlist/', add_to_wantlist, name='add-to-wantlist'),
    path('scraper-status/', scraper_status_view, name='scraper-status'),
]
