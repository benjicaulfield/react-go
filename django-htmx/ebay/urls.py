from django.urls import path
from .views import training_view, annotate_view, export_annotations, ebay_view

urlpatterns = [
    path('', ebay_view, name="ebay-view"),
    path('train/', training_view, name="training-view"),
    path('train/titles/', training_view, name="training-titles"),
    path('train/annotate/', annotate_view, name='annotate'),
    path('train/export/', export_annotations, name='export-annotations'),
]
