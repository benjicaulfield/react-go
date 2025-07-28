from rest_framework import serializers
from .models import Record, Listing, Seller

class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = "__all__"

class SellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = "__all__"

class ListingSerializer(serializers.ModelSerializer):
    record = RecordSerializer()
    seller = SellerSerializer()
    class Meta:
        model = Listing
        fields = "__all__"

