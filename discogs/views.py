import os
import csv
import json
import dotenv
import logging
import requests
import numpy as np
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render

from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .utils.improved_recommendation import ImprovedRecordRecommender
from .utils.thermodynamic_recommendation import ThermodynamicRecordSelector
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Listing, Record, Seller, RecommendationMetrics, RecommendationModel, RecordOfTheDay
from .serializers import RecordSerializer, ListingSerializer, SellerSerializer
from .scraper.get_inventory import get_inventory, update_user_inventory, authenticate_client
from .utils.scoring import calculate_score
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import TfidfVectorizer


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

class DashboardAPIView(APIView):
    def get(self, request):
        num_records = Record.objects.count()
        num_listings = Listing.objects.count()
        unevaluated = Listing.objects.filter(evaluated=False).count()
        
        try:
            model = RecommendationModel.objects.latest('updated_at')
            accuracy = round(model.last_accuracy * 100, 2)
        except RecommendationModel.DoesNotExist:
            accuracy = 0.0
        
        # Get or create today's Record of the Day using thermodynamic selection
        today = timezone.now().date()
        force_refresh = request.GET.get('force_refresh', '0') == '1'
        record_of_the_day_obj = None
        record_of_the_day = None
        breakdown = {}
        
        try:
            if not force_refresh:
                record_of_the_day_obj = RecordOfTheDay.objects.get(date=today)
            else:
                RecordOfTheDay.objects.filter(date=today).delete()

            if record_of_the_day_obj:
                record_of_the_day = record_of_the_day_obj.listing
                breakdown = {
                    'model_score': record_of_the_day_obj.model_score,
                    'entropy_measure': record_of_the_day_obj.entropy_measure,
                    'system_temperature': record_of_the_day_obj.system_temperature,
                    'utility_term': record_of_the_day_obj.utility_term,
                    'entropy_term': record_of_the_day_obj.entropy_term,
                    'free_energy': record_of_the_day_obj.free_energy,
                    'selection_probability': record_of_the_day_obj.selection_probability,
                    'total_candidates': record_of_the_day_obj.total_candidates,
                    'cluster_count': record_of_the_day_obj.cluster_count,
                    'selection_method': record_of_the_day_obj.selection_method
                }
            else:
                selector = ThermodynamicRecordSelector()
                record_of_the_day, breakdown = selector.select_record_of_the_day()
            
        except RecordOfTheDay.DoesNotExist:
            try:
                selector = ThermodynamicRecordSelector()
                record_of_the_day, breakdown = selector.select_record_of_the_day()
                
                if record_of_the_day and breakdown:
                    record_of_the_day_obj = RecordOfTheDay.objects.create(
                        date=today,
                        listing=record_of_the_day,
                        model_score=breakdown.get('model_score', 0.0),
                        entropy_measure=breakdown.get('entropy_measure', 0.0),
                        system_temperature=breakdown.get('system_temperature', 0.5),
                        utility_term=breakdown.get('utility_term', 0.0),
                        entropy_term=breakdown.get('entropy_term', 0.0),
                        free_energy=breakdown.get('free_energy', 0.0),
                        selection_probability=breakdown.get('selection_probability', 0.0),
                        total_candidates=breakdown.get('total_candidates', 0),
                        cluster_count=breakdown.get('cluster_count', 0),
                        selection_method=breakdown.get('selection_method', 'thermodynamic_boltzmann')
                    )
                else:
                    record_of_the_day = Listing.objects.filter(score__gt=0).order_by('-score').first()
                    breakdown = {'selection_method': 'fallback_highest_score'}
                    
            except Exception as e:
                logger.error(f"Error selecting thermodynamic record of the day: {e}")
                record_of_the_day = Listing.objects.filter(score__gt=0).order_by('-score').first()
                breakdown = {'error': str(e), 'selection_method': 'fallback_error'}
        
        # Serialize the record of the day
        record_of_the_day_data = None
        if record_of_the_day:
            record_of_the_day_data = ListingSerializer(record_of_the_day).data
        
        record_of_the_day_obj_data = None
        if record_of_the_day_obj:
            record_of_the_day_obj_data = {
                'id': record_of_the_day_obj.id,
                'date': record_of_the_day_obj.date,
                'model_score': record_of_the_day_obj.model_score,
                'entropy_measure': record_of_the_day_obj.entropy_measure,
                'system_temperature': record_of_the_day_obj.system_temperature,
                'utility_term': record_of_the_day_obj.utility_term,
                'entropy_term': record_of_the_day_obj.entropy_term,
                'free_energy': record_of_the_day_obj.free_energy,
                'selection_probability': record_of_the_day_obj.selection_probability,
                'total_candidates': record_of_the_day_obj.total_candidates,
                'cluster_count': record_of_the_day_obj.cluster_count,
                'selection_method': record_of_the_day_obj.selection_method,
                'desirability_votes': record_of_the_day_obj.desirability_votes,
                'novelty_votes': record_of_the_day_obj.novelty_votes,
                'average_desirability': record_of_the_day_obj.average_desirability,
                'average_novelty': record_of_the_day_obj.average_novelty,
            }
        
        response = Response({
            'num_records': num_records,
            'num_listings': num_listings,
            'accuracy': accuracy,
            'unevaluated': unevaluated,
            'record_of_the_day': record_of_the_day_data,
            'record_of_the_day_obj': record_of_the_day_obj_data,
            'breakdown': breakdown,
        })
        response['Access-Control-Allow-Origin'] = 'http://localhost:5173'
        return response

def dashboard_view(request):
    # Keep the old view for backward compatibility
    api_view = DashboardAPIView()
    response = api_view.get(request)
    return JsonResponse(response.data)

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

def advanced_search_view(request):
    """
    Main search page - renders the search form
    """
    return render(request, 'search.html')

def search_results_view(request):
    """
    Handles search queries and returns paginated results via HTMX
    """
    # Base queryset: Read-only query with prefetch for efficiency
    queryset = Listing.objects.select_related('record').all()

    # Text search (multi-field)
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(record__artist__icontains=query) |
            Q(record__title__icontains=query) |
            Q(record__label__icontains=query)
        )

    # Genre/Styles filter - FIXED JSONField query
    genre_style = request.GET.get('genre_style', '').strip()
    if genre_style:
        queryset = queryset.filter(
            Q(record__genres__icontains=genre_style) |
            Q(record__styles__icontains=genre_style)
        )

    # Year range filter
    min_year = request.GET.get('min_year')
    max_year = request.GET.get('max_year')
    if min_year and max_year:
        try:
            queryset = queryset.filter(record__year__range=(int(min_year), int(max_year)))
        except ValueError:
            pass  # Ignore invalid inputs

    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        try:
            queryset = queryset.filter(record_price__range=(float(min_price), float(max_price)))
        except ValueError:
            pass  # Ignore invalid inputs

    # Condition filter
    condition = request.GET.get('condition', '').strip()
    if condition:
        queryset = queryset.filter(media_condition__iexact=condition)

    # Seller filter
    seller = request.GET.get('seller', '').strip()
    if seller:
        queryset = queryset.filter(seller__name__icontains=seller)

    # Sorting
    sort = request.GET.get('sort', '-score')  # Default to score descending
    valid_sorts = {
        'score_desc': '-score',
        'price_asc': 'record_price',
        'price_desc': '-record_price',
        'year_asc': 'record__year',
        'year_desc': '-record__year',
    }
    queryset = queryset.order_by(valid_sorts.get(sort, '-score'))

    # Pagination (20 items per page)
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, 20)
    try:
        listings = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        listings = paginator.page(1)

    # Return results partial for HTMX
    return render(request, 'partials/search_results.html', {
        'listings': listings,
        'query': query,  # For highlighting or context
    })

def genre_autocomplete_view(request):
    """
    FIXED: Provides JSON suggestions for genre autocomplete
    """
    term = request.GET.get('term', '').strip().lower()
    genres = set()
    
    # FIXED: Safely handle None values and check types
    records = Record.objects.exclude(genres__isnull=True).exclude(styles__isnull=True)
    for record in records:
        # Check genres
        if record.genres and isinstance(record.genres, list):
            genres.update([g for g in record.genres if isinstance(g, str) and term in g.lower()])
        
        # Check styles
        if record.styles and isinstance(record.styles, list):
            genres.update([s for s in record.styles if isinstance(s, str) and term in s.lower()])
    
    suggestions = sorted(list(genres))[:10]  # Limit for performance
    return JsonResponse(suggestions, safe=False)

def condition_autocomplete_view(request):
    """
    Provides JSON suggestions for condition autocomplete
    """
    term = request.GET.get('term', '').strip().lower()
    # Read-only: Get unique conditions matching term
    conditions = Listing.objects.filter(
        media_condition__icontains=term
    ).values_list('media_condition', flat=True).distinct()[:10]
    return JsonResponse(list(conditions), safe=False)

def seller_autocomplete_view(request):
    """
    Provides JSON suggestions for seller autocomplete
    """
    term = request.GET.get('term', '').strip().lower()
    sellers = Seller.objects.filter(name__icontains=term).values_list('name', flat=True).distinct()[:10]
    return JsonResponse(list(sellers), safe=False)

def styles_autocomplete_view(request):
    """
    Provides JSON suggestions for styles autocomplete (separate from genres)
    """
    term = request.GET.get('term', '').strip().lower()
    styles = set()
    
    records = Record.objects.exclude(styles__isnull=True)
    for record in records:
        if record.styles and isinstance(record.styles, list):
            styles.update([s for s in record.styles if isinstance(s, str) and term in s.lower()])
    
    suggestions = sorted(list(styles))[:10]
    return JsonResponse(suggestions, safe=False)

def recommender_view(request):
    """Main interface: Show 10 random unevaluated listings with improved UI."""
    unevaluated_listings = Listing.objects.filter(evaluated=False).order_by('?')[:10]
    total_unevaluated = Listing.objects.filter(evaluated=False).count()
    
    context = {
        'listings': unevaluated_listings,
        'total_unevaluated': total_unevaluated
    }
    return render(request, 'improved_recommender.html', context)



def prepare_features(listings, vectorizer=None, fit_vectorizer=False):
    """Prepare features for model training/prediction"""
    # Handle empty listings case
    if not listings:
        if vectorizer and hasattr(vectorizer, 'get_feature_names_out'):
            feature_names = vectorizer.get_feature_names_out().tolist() + ['price', 'wants', 'haves', 'wants_haves_ratio', 'year']
            return np.empty((0, len(feature_names))), feature_names, vectorizer
        else:
            return np.empty((0, 105)), [], vectorizer  # Reasonable default size
    
    # Extract data
    data = []
    texts = []
    for listing in listings:
        record = listing.record
        text = f"{record.artist} {record.title} {record.label}"
        texts.append(text)
        
        # Create a feature dict
        features = {
            'price': float(listing.record_price),
            'wants': record.wants,
            'haves': record.haves,
            'wants_haves_ratio': record.wants / max(1, record.haves),
            'year': record.year or 0
        }
        data.append(features)
    
    # Process text features
    if vectorizer is None:
        vectorizer = TfidfVectorizer(max_features=100)
    
    # Ensure vectorizer is fitted
    if fit_vectorizer or not hasattr(vectorizer, 'vocabulary_'):
        # Fit with current texts or a dummy if empty
        if texts:
            vectorizer.fit(texts)
        else:
            vectorizer.fit(["dummy text to initialize vectorizer"])
    
    # Transform texts
    text_features = vectorizer.transform(texts)
    
    # Convert features to numpy array
    X_numeric = np.array([[d['price'], d['wants'], d['haves'], d['wants_haves_ratio'], d['year']] for d in data])
    
    # Combine features
    if hasattr(text_features, 'toarray'):
        X = np.hstack([text_features.toarray(), X_numeric])
    else:
        X = np.hstack([text_features, X_numeric])
    
    # Create feature names list
    feature_names = vectorizer.get_feature_names_out().tolist() + ['price', 'wants', 'haves', 'wants_haves_ratio', 'year']
    
    return X, feature_names, vectorizer

def get_recommendation_model():
    """Get or create recommendation model"""
    try:
        model_obj = RecommendationModel.objects.latest('updated_at')
        model, vectorizer, feature_names = model_obj.load_model()
        
        # If model is None, initialize a new one
        if model is None:
            model = SGDClassifier(loss='log_loss', random_state=42, warm_start=True)
            vectorizer = TfidfVectorizer(max_features=100)
            # Fit the vectorizer with a dummy string
            vectorizer.fit(["dummy text to initialize vectorizer"])
            feature_names = []
            
            # Save the new model
            model_obj.save_model(model, vectorizer, feature_names)
    except RecommendationModel.DoesNotExist:
        # Create a new model
        model = SGDClassifier(loss='log_loss', random_state=42, warm_start=True, class_weight='balanced')
        vectorizer = TfidfVectorizer(max_features=100)
        # Fit the vectorizer with a dummy string
        vectorizer.fit(["dummy text to initialize vectorizer"])
        feature_names = []
        
        # Create and save new model object
        model_obj = RecommendationModel()
        model_obj.save_model(model, vectorizer, feature_names)
    
    return model, vectorizer, feature_names, model_obj

def recommendation_predictions_view(request):
    """Get predictions for listings using improved recommendation system"""
    try:
        # Get listing IDs from request
        listing_ids = request.GET.getlist('listing_ids')
        
        # Convert to integers if they're strings
        if listing_ids and isinstance(listing_ids[0], str):
            listing_ids = [int(id) for id in listing_ids]
        
        # Get listings
        listings = list(Listing.objects.filter(id__in=listing_ids))
        
        if not listings:
            return JsonResponse([], safe=False)
        
        # Use improved recommendation system
        recommender = ImprovedRecordRecommender()
        predictions_dict = recommender.predict(listings)
        
        # Format predictions for response
        predictions = []
        for listing in listings:
            probability = predictions_dict.get(listing.id, 0.5)
            predictions.append({
                'id': listing.id,
                'prediction': probability > 0.5,
                'probability': probability
            })
        
        return JsonResponse(predictions, safe=False)
    except Exception as e:
        logger.error(f"Error in prediction view: {e}")
        # Return default predictions on error
        predictions = []
        try:
            listing_ids = request.GET.getlist('listing_ids')
            if listing_ids and isinstance(listing_ids[0], str):
                listing_ids = [int(id) for id in listing_ids]
            for lid in listing_ids:
                predictions.append({
                    'id': lid,
                    'prediction': True,
                    'probability': 0.5
                })
        except:
            pass
        return JsonResponse(predictions, safe=False)

@csrf_exempt
@transaction.atomic
def submit_recommendations_view(request):
    """Handle submission of user selections using improved recommendation system"""
    if request.method == 'POST':
        try:
            # Get listing IDs and keeper IDs
            listing_ids = request.POST.getlist('listing_ids')
            keeper_ids = request.POST.getlist('keeper_ids')
            
            # Convert to integers if they're strings
            if listing_ids and isinstance(listing_ids[0], str):
                listing_ids = [int(id) for id in listing_ids]
            
            if keeper_ids and isinstance(keeper_ids[0], str):
                keeper_ids = [int(id) for id in keeper_ids]
            
            # Get listings
            listings = Listing.objects.filter(id__in=listing_ids)
            
            # Update listings individually to ensure refresh_from_db works in tests
            for listing in listings:
                listing.evaluated = True
                listing.kept = listing.id in keeper_ids
                listing.save()
            
            # Use improved recommendation system for training
            recommender = ImprovedRecordRecommender()
            training_success = recommender.train(keeper_ids, listing_ids)
            
            if training_success:
                logger.info(f"Successfully trained model with {len(listing_ids)} samples, {len(keeper_ids)} keepers")
            else:
                logger.warning("Model training failed, but continuing...")
            
            return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Error in submit view: {e}")
            return JsonResponse({"error": str(e)})
    
    return HttpResponseBadRequest("Invalid request method")

def recommendation_tuner_view(request):
    """Show next batch of listings (same as recommender)"""
    unevaluated_listings = Listing.objects.filter(evaluated=False).order_by('?')[:10]
    return render(request, 'recommender.html', {'listings': unevaluated_listings})

def recommendation_tuner_predictions_view(request):
    """Get predictions for current session (same as regular predictions)"""
    return recommendation_predictions_view(request)

def model_performance_stats_view(request):
    """Return model performance statistics"""
    try:
        # Get the latest model
        try:
            model_obj = RecommendationModel.objects.latest('updated_at')
            accuracy = model_obj.last_accuracy
        except RecommendationModel.DoesNotExist:
            accuracy = 0.0
        
        # Get metrics
        metrics = RecommendationMetrics.objects.order_by('-session_date')
        
        # Prepare response
        response_data = {
            'accuracy': accuracy,
            'total_sessions': metrics.count(),
            'sessions': list(metrics.values('session_date', 'accuracy', 'precision', 'num_samples'))
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Error in stats view: {e}")
        return JsonResponse({"error": str(e)})

@csrf_exempt
def refresh_record_of_the_day_view(request):
    """Force refresh of Record of the Day using thermodynamic selection"""
    if request.method == 'POST':
        try:
            today = timezone.now().date()
            
            # Delete existing record for today to force refresh
            RecordOfTheDay.objects.filter(date=today).delete()
            
            # Select new record using thermodynamic system
            selector = ThermodynamicRecordSelector()
            record_of_the_day, breakdown = selector.select_record_of_the_day()
            
            if record_of_the_day and breakdown:
                # Save the new selection
                record_of_the_day_obj = RecordOfTheDay.objects.create(
                    date=today,
                    listing=record_of_the_day,
                    model_score=breakdown.get('model_score', 0.0),
                    entropy_measure=breakdown.get('entropy_measure', 0.0),
                    system_temperature=breakdown.get('system_temperature', 0.5),
                    utility_term=breakdown.get('utility_term', 0.0),
                    entropy_term=breakdown.get('entropy_term', 0.0),
                    free_energy=breakdown.get('free_energy', 0.0),
                    selection_probability=breakdown.get('selection_probability', 0.0),
                    total_candidates=breakdown.get('total_candidates', 0),
                    cluster_count=breakdown.get('cluster_count', 0),
                    selection_method=breakdown.get('selection_method', 'thermodynamic_boltzmann')
                )
                
                logger.info(f"Refreshed Record of the Day: {record_of_the_day.record.artist} - {record_of_the_day.record.title}")
                
                return HttpResponse(
                    '<div class="text-green-500 text-sm">✅ Record of the Day refreshed! Reload page to see the new selection.</div>'
                )
            else:
                return HttpResponse(
                    '<div class="text-red-500 text-sm">❌ Failed to select new record. No eligible listings found.</div>'
                )
                
        except Exception as e:
            logger.error(f"Error refreshing Record of the Day: {e}")
            return HttpResponse(
                f'<div class="text-red-500 text-sm">❌ Error: {str(e)}</div>'
            )
    
    return HttpResponse(
        '<div class="text-red-500 text-sm">❌ Invalid request method</div>'
    )

@csrf_exempt
def vote_record_of_the_day_view(request, record_id):
    if request.method == 'POST':
        try:
            record = RecordOfTheDay.objects.get(id=record_id)
            desirability = float(request.POST.get('desirability', 0.5))
            novelty = float(request.POST.get('novelty', 0.5))
            # Append votes (simplified; add user ID in production)
            record.desirability_votes.append(desirability)
            record.novelty_votes.append(novelty)
            record.average_desirability = sum(record.desirability_votes) / len(record.desirability_votes)
            record.average_novelty = sum(record.novelty_votes) / len(record.novelty_votes)
            record.save()
            # Feed back into model (see below)
            return HttpResponse('<div class="text-green-500">Vote submitted! Thanks for your feedback.</div>')
        except Exception as e:
            return HttpResponse(f'<div class="text-red-500">Error: {str(e)}</div>')
    return HttpResponseBadRequest()
