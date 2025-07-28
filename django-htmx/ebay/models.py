from django.db import models

class EbayRecord(models.Model):
    artist = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    