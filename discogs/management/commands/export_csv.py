import csv
from django.core.management.base import BaseCommand
from discogs.models import Listing  # Replace with your actual app name and model
from discogs.models import Record  # Assuming Record is related to Listing

class Command(BaseCommand):
    help = "Export all listings along with their record data to a CSV file"

    def handle(self, *args, **kwargs):
        filename = "listings_with_records_export.csv"

        # Get all listings and related record data
        listings = Listing.objects.select_related("record").all()  # Adjust the relation name if different

        # Define CSV headers: Listing fields + Record fields
        listing_fields = [field.name for field in Listing._meta.fields]
        record_fields = [field.name for field in Record._meta.fields]

        all_fields = listing_fields + record_fields

        # Write to CSV
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(all_fields)  # Write headers

            for listing in listings:
                record = listing.record  # Assuming Listing has a ForeignKey to Record
                row_data = [getattr(listing, field) for field in listing_fields] + \
                           [getattr(record, field) for field in record_fields]
                writer.writerow(row_data)

        self.stdout.write(self.style.SUCCESS(f"Exported {listings.count()} listings with records to {filename}"))
