from discogs.models import Listing

def get_sorted_listings(request, seller_name):
    print("DEBUG: get_sorted_listings() called")  # Check if this prints

    sort_param = request.GET.get('sort', 'score')
    direction = request.GET.get('direction', 'asc')

    valid_sorts = {
        'score': 'score',
        'artist': 'record__artist',
        'year': 'record__year',
        'price': 'record_price,'
    }

    sort_field = valid_sorts.get(sort_param, 'score')
    if direction == 'desc':
        sort_field = f"-{sort_field}"

    listings = Listing.objects.filter(seller__username=seller_name).order_by(sort_field)
    print(f"DEBUG: Sorting by {sort_field} | Listings count: {listings.count()}")
    return listings



    



