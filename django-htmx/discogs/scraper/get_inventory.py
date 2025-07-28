import os
import json
from dotenv import load_dotenv
import discogs_client
import time
import logging
from datetime import datetime
import random
from ..utils.rate_limits import rate_limit_client

load_dotenv()
logger = logging.getLogger(__name__)

consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')
TOKEN_FILE = 'discogs_token.json'
INVENTORY_FILE = 'user_inventories.json'

INVENTORIES_FOLDER = 'inventories'

def load_inventory_json():
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_inventory_json(inventory):
    with open(INVENTORY_FILE, 'w') as f:
        json.dump(inventory, f, indent=4)

def update_user_inventory(username, record_ids):
    data = load_inventory_json()
    today = datetime.now().strftime('%Y-%m-%d')
    if username not in data:
        data[username] = {
            "last_inventory": today,
            "record_ids": record_ids
        }
    else:
        existing_ids = data[username]['record_ids']
        all_ids = record_ids + [rid for rid in existing_ids if rid not in record_ids]
        data[username] = {
            "last_inventory": today,
            "record_ids": all_ids[:50]
        }
    
    save_inventory_json(data)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def save_tokens(token, secret):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'secret': secret}, f)

def authenticate_client():
    tokens = load_tokens()
    if tokens:
        d = discogs_client.Client('wantlist/1.0')
        d.set_consumer_key(consumer_key, consumer_secret)
        d.set_token(tokens['token'], tokens['secret'])
    else:
        # Perform OAuth flow if no tokens are found
        d = discogs_client.Client('wantlist/1.0')
        d.set_consumer_key(consumer_key, consumer_secret)
        token, secret, url = d.get_authorize_url()
        print(f"Please visit this URL to authorize: {url}")
        verifier = input("Enter the verifier code: ")
        access_token, access_secret = d.get_access_token(verifier)

        # Save the tokens for future use
        save_tokens(access_token, access_secret)

    return rate_limit_client(d)

def get_inventory(username):
    print(f"\n=== Starting inventory fetch for {username} ===")
    d = authenticate_client()
    records = []
    user = d.user(username)
    inventory = user.inventory
    inventory.per_page = 100

    previous_inventory = load_inventory_json().get(username, {})
    previous_ids = set(previous_inventory.get('record_ids', []))
    print(f"Found {len(previous_ids)} previous records for {username}")

    current_ids = []

    total_pages = min(100, inventory.pages)
    for i in range(total_pages, 0, -1):
        time.sleep(random.uniform(0.25, 0.75))
        try:
            print(f"\nFetching page {i} for {username}")
            page = inventory.page(i)
            page_records = filter_page(page)
            print(f"Found {len(page_records)} records on page {i}")
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            continue

        for record in page_records:
            print(f"Processing record: {record['discogs_id']} - {record['artist']} - {record['title']}")  # id, artist, title
            if record['discogs_id'] in previous_ids:
                print(f"Found previously seen record {record['discogs_id']}, stopping")
                update_user_inventory(username, current_ids)
                return records
            current_ids.append(record['discogs_id'])
        records += page_records
        print(f"Total records collected so far: {len(records)}")

    print(f"\n=== Finished fetching inventory for {username}, total records: {len(records)} ===")
    return records

def filter_page(page):
    conditions = {"Near Mint (NM or M-)", "Very Good Plus (VG+)", "Very Good (VG)", "Good Plus (G+)"}
    keepers = []
    for listing in page:
        if 'LP' in listing.data['release']['format'] and wanted(listing) and listing.condition in conditions:
            keepers.append(parse_listing(listing))
    return keepers

def parse_listing(l):
    time.sleep(random.uniform(0.5, 1.00))
    return {
        'discogs_id': l.release.id,
        'media_condition': l.condition,  # Changed from 'condition'
        'record_price': (l.price.value, l.price.currency),
        'seller': l.seller.username,
        'artist': l.release.data['artist'],
        'title': l.release.data['title'],
        'format': 'LP',  # Added this
        'label': l.release.data['label'],
        'catno': l.release.data['catalog_number'],
        'wants': l.release.data['stats']['community']['in_wantlist'],
        'haves': l.release.data['stats']['community']['in_collection'],
        'genres': l.release.genres,
        'styles': l.release.styles,
        'year': l.release.year,
        'suggested_price': l.release.price_suggestions.very_good_plus if hasattr(l.release, 'price_suggestions') else None
    }

def wanted(listing):
    return listing.data['release']['stats']['community']['in_wantlist'] > listing.data['release']['stats']['community']['in_collection']
