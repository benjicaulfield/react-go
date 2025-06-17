# management/commands/export_listings.py
from django.core.management.base import BaseCommand
from django.db.models import F, Value, TextField, CharField
from django.db.models.functions import Coalesce
import csv
import os
from django.conf import settings
from ...models import Listing

class Command(BaseCommand):
    help = 'Export 5000 most recent listings to a CSV file'

    def handle(self, *args, **options):
        # Default output directory (you can customize this)
        output_dir = os.path.join(settings.BASE_DIR, 'exports')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with timestamp
        from django.utils import timezone
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f'listings_export_{timestamp}.csv')

        # Get the most recent 5000 listings with related record details
        listings = Listing.objects.select_related('record', 'seller')\
            .annotate(
                record_artist=F('record__artist'),
                record_title=F('record__title'),
                record_label=Coalesce(
                    F('record__label'), 
                    Value(''), 
                    output_field=TextField()
                ),
                record_format=Coalesce(
                    F('record__format'), 
                    Value(''), 
                    output_field=CharField()
                ),
                record_year=Coalesce(
                    F('record__year'), 
                    Value(None)
                ),
                seller_name=F('seller__name')
            ).order_by('-id')[:5000]

        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
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

        self.stdout.write(self.style.SUCCESS(f'Successfully exported {listings.count()} listings to {output_file}'))