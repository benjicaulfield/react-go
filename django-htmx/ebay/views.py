import json
import dotenv

from django.http import JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .utils.search import Search
from .utils.clean_and_filter_listings import get_listings

dotenv.load_dotenv()
BIO_LABELS = ["B-ARTIST", "I-ARTIST", "B-TITLE", "I-TITLE", "B-META", "I-META", "O"]

# Color mapping for different labels with better contrast and readability
LABEL_COLORS = {
    "B-ARTIST": "bg-red-500 border-red-300 text-white shadow-sm",
    "I-ARTIST": "bg-red-400 border-red-200 text-white shadow-sm", 
    "B-TITLE": "bg-emerald-500 border-emerald-300 text-white shadow-sm",
    "I-TITLE": "bg-emerald-400 border-emerald-200 text-white shadow-sm",
    "B-META": "bg-purple-500 border-purple-300 text-white shadow-sm",
    "I-META": "bg-purple-400 border-purple-200 text-white shadow-sm",
    "O": "bg-slate-500 border-slate-300 text-white shadow-sm"
}

def ebay_view(request):
    return render(request, 'ebay.html')

def ebay_listings_view(request):
    listings = Search().search()
    return TemplateResponse(request, 'partials/listings.html', 
                            {'listings': listings})

def training_view(request):
    if request.header.get("HX-Request"):
        if "records" not in request.session:
            listings = get_listings()
            records = []
            for _, row in listings.iterrows():
                records.append({
                    "title": row['title'],
                    "artist": "",
                    "title": ""
                })
            request.session['records'] = records
            request.session.modified = True 
        
        records = request.session.get("records", [])

        return TemplateResponse(request, "partials/titles_for_artist_title_extraction.html", {
            "records": records
        })
    else:
        return render(request, "train.html")


def training_bio_view(request):
    if request.headers.get("HX-Request"):
        if "records" not in request.session:
            listings = get_listings()
            records = []
            for _, row in listings.iterrows():
                tokens = []
                for word in row["title"].split():
                    tokens.append({
                        "word": word, 
                        "label": None, 
                        "color_class": ""
                    })
                records.append({"title": row["title"], "tokens": tokens})
            request.session["records"] = records
            # Initialize cursor to highlight first token
            request.session["cursor"] = {"record_index": 0, "token_index": 0}
            request.session.modified = True
        
        # Get current cursor position
        cursor = request.session.get("cursor", {"record_index": 0, "token_index": 0})
        records = request.session.get("records", [])
        
        # Add color classes to tokens based on their labels
        for record in records:
            for token in record["tokens"]:
                if token["label"] and not token.get("color_class"):
                    token["color_class"] = LABEL_COLORS.get(token["label"], "bg-gray-600 border-gray-400 text-gray-200")
        
        # Debug: Print current cursor state
        print(f"Training view: record_index={cursor['record_index']}, token_index={cursor['token_index']}")
        
        return TemplateResponse(request, "partials/training_titles.html", {
            "records": records,
            "labels": BIO_LABELS,
            "record_index": cursor["record_index"],
            "token_index": cursor["token_index"]
        })
    else:
        return render(request, "train.html")

@require_POST
def annotate_view(request):
    record_index = int(request.POST.get("record_index", 0))
    token_index = int(request.POST.get("token_index", 0))
    label = request.POST.get("label")

    records = request.session.get("records", [])
    
    # Debug: Print current state
    print(f"Before: record_index={record_index}, token_index={token_index}, total_records={len(records)}")
    if records and record_index < len(records):
        print(f"Current record has {len(records[record_index]['tokens'])} tokens")
    
    if records and 0 <= record_index < len(records):
        tokens = records[record_index]["tokens"]
        if 0 <= token_index < len(tokens):
            # Apply the label
            tokens[token_index]["label"] = label
            tokens[token_index]["color_class"] = LABEL_COLORS.get(label, "bg-slate-500 border-slate-300 text-white shadow-sm")
            
            # Move cursor to next token
            token_index += 1
            
            # If we've reached the end of current record's tokens
            if token_index >= len(tokens):
                record_index += 1
                token_index = 0
                
                # If we've reached the end of all records, cycle back to beginning
                if record_index >= len(records):
                    record_index = 0
                    token_index = 0

    # Debug: Print new state
    print(f"After: record_index={record_index}, token_index={token_index}")
    
    # Save updated records and cursor to session
    request.session["records"] = records
    request.session["cursor"] = {"record_index": record_index, "token_index": token_index}
    request.session.modified = True  # Force session save
    
    # Add color classes to all tokens for display
    for record in records:
        for token in record["tokens"]:
            if token["label"] and not token.get("color_class"):
                token["color_class"] = LABEL_COLORS.get(token["label"], "bg-slate-500 border-slate-300 text-white shadow-sm")

    # Get current record for token count
    current_record = records[record_index] if records and record_index < len(records) else None

    return TemplateResponse(request, "partials/training_titles.html", {
        "records": records,
        "labels": BIO_LABELS,
        "label_colors": LABEL_COLORS,
        "record_index": record_index,
        "token_index": token_index,
        "current_record": current_record
    })

@require_POST
def export_annotations(request):
    import json
    from django.http import HttpResponse

    records = request.session.get("records", [])
    response = HttpResponse(json.dumps(records, indent=2), content_type="application/json")
    response["Content-Disposition"] = "attachment; filename=annotations.json"
    return response