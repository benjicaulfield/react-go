import os
import csv
import dotenv
import logging
import numpy as np
import requests
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Listing, Record, Seller, RecommendationModel, RecommendationMetrics
from .serializers import RecordSerializer, ListingSerializer, SellerSerializer
from .scraper.get_inventory import get_inventory, update_user_inventory, authenticate_client
from .scraper.gmail import get_gmail_service, get_usernames
from .utils.scoring import calculate_score
from django.db import transaction
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score
import joblib
import pickle

dotenv.load_dotenv()
logger = logging.getLogger(__name__)
KEY = os.getenv('EXCHANGE_RATE_API_KEY')

class BaseScraperDataView(APIView):
    def process_inventory(self, seller_name, inventory, exchange_rates):
        if not inventory:
            logger.warning(f"No inventory found for user {seller_name}")
            return
            
        record_ids = [record['discogs_id'] for record in inventory]
        update_user_inventory(seller_name, record_ids)

        successful_records = []
        failed_records = []
        
        for record_data in inventory:
            try:
                record, created = self.process_record(record_data)
                if created:
                    logger.info(f"Created new record: {record_data['artist']} - {record_data['title']}")
                
                try:
                    listing = self.process_listing(record, record_data, exchange_rates)
                    successful_records.append(record_data)
                except Exception as e:
                    logger.error(f"Failed to create listing for record {record_data['discogs_id']}: {str(e)}")
                    failed_records.append((record_data, str(e)))
                    
            except Exception as e:
                logger.error(f"Failed to process record {record_data['discogs_id']}: {str(e)}")
                failed_records.append((record_data, str(e)))
                continue

        try:
            currency = inventory[0]['record_price'][1]
            Seller.objects.get_or_create(
                name=seller_name,
                currency=currency
            )
        except Exception as e:
            logger.error(f"Failed to create/update seller {seller_name}: {str(e)}")

        # Log summary
        logger.info(f"Processed {len(successful_records)} records successfully for {seller_name}")
        if failed_records:
            logger.error(f"Failed to process {len(failed_records)} records for {seller_name}")
            for failed_record, error in failed_records:
                logger.error(f"- {failed_record['artist']} - {failed_record['title']}: {error}")

    def process_record(self, record_data):
        return Record.objects.get_or_create(
            discogs_id=record_data['discogs_id'],
            defaults={
                'artist': record_data['artist'],
                'title': record_data['title'],
                'format': record_data['format'],
                'label': record_data['label'],
                'catno': record_data['catno'],
                'wants': record_data['wants'],
                'haves': record_data['haves'],
                'genres': record_data['genres'],
                'styles': record_data['styles'],
                'year': record_data.get('year', None)
            }
        )

    def process_listing(self, record, record_data, exchange_rates):
        record_price = self.currency_exchange(record_data['record_price'], exchange_rates)
        seller, _ = Seller.objects.get_or_create(name=record_data['seller'])
        print(f"DEBUG: Processing listing - Record ID: {record.id}, Seller ID: {seller.id}")

        return Listing.objects.get_or_create(
            seller=seller,
            record=record,
            defaults={
                'record_price': record_price,
                'media_condition': record_data['media_condition'],
                'kept': False,
                'evaluated': False
            }
        )
    
    def get_exchange_rates(self):
        url = f'https://v6.exchangerate-api.com/v6/{KEY}/latest/USD'
        response = requests.get(url)
        data = response.json()

        if data.get('result') == 'error':
            return {}
        
        rates = data.get('conversion_rates', {})
        return rates

    def currency_exchange(self, price_tuple, exchange_rates):
        price, currency = price_tuple
        exchange_rate = exchange_rates.get(currency, 1)
        return round(float(price) * exchange_rate, 2)

    def clean_suggested_price(self, price):
        _, price, currency = price.split(" ")
        exchange_rate = self.get_exchange_rates().get(currency, 1)
        return round(float(price) * exchange_rate, 2)

class ScraperDataToDatabaseView(BaseScraperDataView):
    def post(self, request, *args, **kwargs):
        print("\n=== Starting scraper view processing ===")
        try:
            service = get_gmail_service()
            subject = 'dotdashdashdot - Shop New Wantlist Items for Sale'
            usernames = list(set(get_usernames(service, subject)))
            print(f"Found usernames: {usernames}")
            if not usernames:
                return Response(
                    {"error": "No usernames found in email subject"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(f"Error fetching usernames: {e}")
            return Response(
                {"error": "Failed to fetch usernames"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        exchange_rates = self.get_exchange_rates()

        for user in usernames:
            print(f"\n=== Processing user {user} ===")
            try:
                inventory = get_inventory(user)
                print(f"Got inventory for {user}, {len(inventory)} records")
                self.process_inventory(user, inventory, exchange_rates)
            except Exception as e:
                logger.error(f"Error processing inventory for user {user}: {e}")
                continue

        return Response(
            {"message": "Data processed successfully"},
            status=status.HTTP_201_CREATED,
        )

class ScraperDataToDatabaseBySellerView(BaseScraperDataView):
    def post(self, request, *args, **kwargs):
        seller_name = kwargs.get('seller')
        if not seller_name:
            return Response(
                {"error": "Seller name not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        exchange_rates = self.get_exchange_rates()
        
        try:
            inventory = get_inventory(seller_name)
            self.process_inventory(seller_name, inventory, exchange_rates)
        except Exception as e:
            logger.error(f"Error processing inventory for seller {seller_name}: {e}")
            return Response(
                {"error": f"Failed to process inventory for {seller_name}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": f"Data processed successfully for seller {seller_name}"},
            status=status.HTTP_201_CREATED,
        )
class RecordsBySellerAPIView(APIView):
    def get(self, request, *args, **kwargs):
        seller_name = kwargs.get('seller_name')
        if not seller_name:
            return Response({'error': 'Seller name is required'}, status=status.HTTP_400_BAD_REQUEST)  
        seller_records = Record.objects.filter(seller__name=seller_name)
        serializer = RecordSerializer(seller_records, many=True)
        return Response(serializer.data) 

def scoring_view(request):
    return render(request, 'scoring.html')

def tune_scoring_view(request):
    if request.method != "POST":
        return HttpResponse("Invalid request method.", status=405)
    seller_name = request.POST.get('seller', '').strip()
    if not seller_name:
        return HttpResponse("No seller specified")
    
    unevaluated_listings = Listing.objects.filter(seller__name=seller_name, evaluated=False).order_by('?')[:10]
    for listing in unevaluated_listings:
        listing.score = calculate_score(listing.record.wants,
                                        listing.record.haves,
                                        listing.record_price)
        
    return TemplateResponse(request, 'partials/scoring_listings.html', {
        'listings': unevaluated_listings,
        'total_count': Listing.objects.filter(seller__name=seller_name).count(),
        'unevaluated_count': Listing.objects.filter(seller__name=seller_name, evaluated=False).count()
    })

def dashboard_view(request):
    return render(request, 'dashboard.html')

def dashboard_listings_view(request):
    top_listings = Listing.objects.order_by('-score')[:10]
    random_listings = Listing.objects.order_by('?')[:10]
    all_listings = (top_listings | random_listings).order_by('?')

    return TemplateResponse(request, 'partials/listings.html', 
                            {'listings': all_listings})

@csrf_exempt
def add_to_wantlist(request):
    if request.method == "POST":
        record_id = request.POST.get("record_id")
        if not record_id:
            return HttpResponse("No record ID provided", status=400)
        
        d = authenticate_client()

        try:
            d.user().wantlist.add(record_id)
            return HttpResponse('<p class="text-green-500">Added to wantlist!</p>')
        except Exception as e:
            return HttpResponse(f'<p class="text-red-500">Failed to add to wantlist: {str(e)}</p>', status=400)

    return HttpResponse('<p class="text-red-500">Invalid request</p>', status=400)      

def home_view(request):
    return render(request, 'home.html')

def by_seller_view(request):
    return render(request, 'by_seller.html')

def search_seller_view(request):
    if request.method != "POST":
        return HttpResponse("Invalid request method.", status=405)

    seller_name = request.POST.get('seller', '').strip()
    print(f"DEBUG: Received seller name: '{seller_name}'")  # Log received seller name

    if not seller_name:
        return HttpResponse("No seller specified")

    listings = Listing.objects.filter(seller__name=seller_name)
    print(f"DEBUG: Found {listings.count()} listings for {seller_name}")  # Log number of listings

    return render(request, 'partials/listings.html', {
        'listings': listings,
        'seller_name': seller_name
    })

def seller_trigger_page_view(request):
    return render(request, 'seller_trigger.html')

def seller_trigger_view(request):
    if request.method == 'POST':
        seller_name = request.POST.get("seller", "").strip()
        if not seller_name:
            return HttpResponse("Please enter a seller name.")
        
        scraper_view = ScraperDataToDatabaseBySellerView()
        response = scraper_view.post(request, seller=seller_name)

        # If the scrape is successful, redirect to the by-seller page
        if response.status_code == 201:
            return redirect(f"{reverse('by-seller')}?seller={seller_name}")

        # If the scraper fails, show an error message
        return HttpResponse(f"Error: {response.data.get('error', 'Unknown error')}", status=response.status_code)

    return render(request, "seller_trigger.html")

def export_listings_csv(request):
    """
    Export listings to CSV with record details
    Limits to 5000 most recent listings
    """
    # Get the most recent 5000 listings with related record details
    listings = Listing.objects.select_related('record', 'seller')\
        .annotate(
            record_artist=F('record__artist'),
            record_title=F('record__title'),
            record_label=Coalesce(F('record__label'), Value('')),
            record_format=Coalesce(F('record__format'), Value('')),
            record_year=Coalesce(F('record__year'), Value(None)),
            seller_name=F('seller__name')
        ).order_by('-id')[:5000]

    # Create the HttpResponse object with CSV mime type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="listings_export.csv"'

    # Create a CSV writer
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Listing ID', 'Record Artist', 'Record Title', 'Record Label', 
        'Record Format', 'Record Year', 'Seller', 'Record Price', 
        'Media Condition', 'Score', 'Kept', 'Evaluated'
    ])

    # Write data rows
    for listing in listings:
        writer.writerow([
            listing.id,
            listing.record_artist,
            listing.record_title,
            listing.record_label,
            listing.record_format,
            listing.record_year,
            listing.seller_name,
            listing.record_price,
            listing.media_condition,
            listing.score,
            listing.kept,
            listing.evaluated
        ])

    return response

def prepare_features(listings, vectorizer=None, fit_vectorizer=False):
    data = []
    for listing in listings:
        record = listing.record
        text = f"{record.artist} {record.title} {record.label}"  # Bag-of-words input
        genre_style = record.genres + record.styles if record.genres and record.styles else []
        year_bin = f"{(record.year // 10) * 10}s" if record.year else "Unknown"  # e.g., "1980s"
        genre_year = [f"{g}_{year_bin}" for g in genre_style]  # Temporal interaction features
        wants_haves_ratio = record.wants / (record.haves + 1) if record.haves else 0
        data.append({
            'text': text,
            'price': float(listing.record_price),
            'wants_haves_ratio': wants_haves_ratio,
            'year': record.year or 0,  # Impute missing year
            'genre_style': genre_style + genre_year,  # Combined for one-hot
        })
    
    # Feature transformation
    texts = [d['text'] for d in data]
    numerical_features = np.array([[d['price'], d['wants_haves_ratio'], d['year']] for d in data])
    categorical_features = [d['genre_style'] for d in data]
    
    if fit_vectorizer and vectorizer is None:
        vectorizer = TfidfVectorizer(max_features=1000)  # Limit for performance
    
    if vectorizer:
        text_features = vectorizer.transform(texts) if not fit_vectorizer else vectorizer.fit_transform(texts)
    else:
        text_features = np.empty((len(data), 0))  # Placeholder if no vectorizer
    
    # One-hot encode categorical (genres/styles/year interactions)
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    cat_features = encoder.fit_transform(np.array(categorical_features, dtype=object).reshape(-1, 1)) if categorical_features else np.empty((len(data), 0))
    
    # Scale numerical
    scaler = StandardScaler()
    num_features = scaler.fit_transform(numerical_features)
    
    # Combine all features
    X = np.hstack([text_features.toarray() if hasattr(text_features, 'toarray') else text_features, num_features, cat_features])
    feature_names = (
        vectorizer.get_feature_names_out().tolist() if vectorizer else [] +
        ['price', 'wants_haves_ratio', 'year'] +
        encoder.get_feature_names_out().tolist()
    )
    return X, feature_names, vectorizer, encoder, scaler

# Utility to get or initialize the model
def get_recommendation_model():
    try:
        rec_model = RecommendationModel.objects.latest('updated_at')
        model, vectorizer, feature_names = rec_model.load_model()
    except RecommendationModel.DoesNotExist:
        # Initialize default model
        model = SGDClassifier(loss='log_loss', random_state=42, warm_start=True)
        vectorizer = TfidfVectorizer(max_features=1000)
        feature_names = []
        rec_model = RecommendationModel()
        rec_model.save_model(model, vectorizer, feature_names)
    return model, vectorizer, feature_names, rec_model

def recommender_view(request):
    """Main interface: Show 10 random unevaluated listings."""
    unevaluated_listings = Listing.objects.filter(evaluated=False).order_by('?')[:10]
    return render(request, 'recommender.html', {'listings': unevaluated_listings})

def recommendation_predictions_view(request):
    """HTMX endpoint: Get ML predictions for displayed listings."""
    listing_ids = request.GET.getlist('listing_ids')  # Assume sent via HTMX
    listings = Listing.objects.filter(id__in=listing_ids, evaluated=False)
    model, vectorizer, _, _ = get_recommendation_model()
    X, _, _, _, _ = prepare_features(listings, vectorizer=vectorizer)
    if X.size > 0:
        predictions = model.predict(X)
        probs = model.predict_proba(X)[:, 1]  # Probability of being keeper
    else:
        predictions, probs = [False] * len(listings), [0.5] * len(listings)
    return render(request, 'partials/recommendation_predictions.html', {
        'predictions': zip(listings, predictions, probs)
    })

@csrf_exempt
def submit_recommendations_view(request):
    """Handle submission: Update DB, retrain model, load next batch."""
    if request.method == 'POST':
        listing_ids = request.POST.getlist('listing_ids')
        keeper_ids = request.POST.getlist('keepers')  # IDs marked as keeper
        listings = Listing.objects.filter(id__in=listing_ids, evaluated=False)
        model, vectorizer, feature_names, rec_model = get_recommendation_model()
        X, new_feature_names, updated_vectorizer, _, _ = prepare_features(listings, vectorizer, fit_vectorizer=True)
        y = [1 if str(listing.id) in keeper_ids else 0 for listing in listings]  # Labels from user
        
        with transaction.atomic():
            for listing, pred, label in zip(listings, model.predict(X) if X.size else [False]*len(listings), y):
                listing.evaluated = True
                listing.is_keeper = bool(label)
                listing.predicted_keeper = bool(pred)
                listing.save()
            
            # Incremental update
            if X.size > 0:
                model.partial_fit(X, y)
                # Update feature names if new ones appear
                feature_names = list(set(feature_names + new_feature_names))
                rec_model.save_model(model, updated_vectorizer, feature_names)
            
            # Track metrics
            if y:
                accuracy = accuracy_score(y, model.predict(X))
                precision = precision_score(y, model.predict(X), zero_division=0)
                RecommendationMetrics.objects.create(
                    accuracy=accuracy, precision=precision, num_samples=len(y)
                )
        
        # Return next batch via HTMX
        next_listings = Listing.objects.filter(evaluated=False).order_by('?')[:10]
        return render(request, 'partials/recommender_listings.html', {'listings': next_listings})
    return HttpResponse("Invalid request", status=400)

def recommendation_tuner_view(request):
    """Tuner interface: Same as main, for iterative tuning."""
    # Identical to recommender_view for simplicity
    unevaluated_listings = Listing.objects.filter(evaluated=False).order_by('?')[:10]
    return render(request, 'recommendation_tuner.html', {'listings': unevaluated_listings})

def recommendation_tuner_predictions_view(request):
    """Predictions for tuner: Mirrors recommendation_predictions_view."""
    # Reuse logic for consistency
    return recommendation_predictions_view(request)

def model_performance_stats_view(request):
    """Display model stats."""
    metrics = RecommendationMetrics.objects.order_by('-session_date')[:10]  # Last 10 sessions
    try:
        latest_model = RecommendationModel.objects.latest('updated_at')
        overall_accuracy = latest_model.last_accuracy
    except RecommendationModel.DoesNotExist:
        overall_accuracy = 0.0
    return render(request, 'model_performance_stats.html', {
        'metrics': metrics, 'overall_accuracy': overall_accuracy
    })

def scraper_status_view(request):
    """Return scraper status for a given seller."""
    seller_name = request.GET.get('seller', '')
    # This is a placeholder - implement actual scraper status logic as needed
    return render(request, 'partials/scraper_status.html', {
        'seller_name': seller_name,
        'status': 'idle'  # placeholder status
    })
