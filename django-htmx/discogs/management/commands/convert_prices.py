from django.core.management.base import BaseCommand
from discogs.models import Listing, Seller
from decimal import Decimal

class Command(BaseCommand):
    help = "Convert all prices for seller 'recordmania.se' from SEK to USD at 0.09 exchange rate."

    def handle(self, *args, **kwargs):
        SEK_TO_USD = Decimal("0.09")

        seller = Seller.objects.filter(name="recordmania.se").first()
        if not seller:
            self.stdout.write(self.style.ERROR("❌ Seller 'recordmania.se' not found."))
            return

        listings = Listing.objects.filter(seller=seller)
        count = listings.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("⚠ No listings found for 'recordmania.se'."))
            return

        self.stdout.write(self.style.SUCCESS(f"🔄 Converting {count} listings from SEK to USD..."))

        for listing in listings:
            old_price = listing.record_price
            new_price = round(old_price * SEK_TO_USD, 2)  # Convert SEK → USD
            listing.record_price = new_price
            listing.save()
            self.stdout.write(f"✅ Updated listing {listing.id}: {old_price} SEK → {new_price} USD")

        self.stdout.write(self.style.SUCCESS("🎉 Conversion complete!"))
