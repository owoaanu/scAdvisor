from django.db import models

# class EMSData(models.Model):
#     loc_name = models.CharField(max_length=100)
#     site = models.CharField(max_length=100)
#     url_type = models.CharField(max_length=50)  # e.g. 'channels', 'data_2', 'data_5', 'chart'
#     interval = models.CharField(max_length=10, blank=True, null=True)  # e.g. 2, 5, 10, 30, etc.
#     url = models.URLField()
#     received_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.loc_name} - {self.url_type} ({self.interval or 'N/A'})"



class EMSLocality(models.Model):
    site = models.CharField(max_length=100)
    locName = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    url = models.URLField()
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=50)

class EMSImage(models.Model):
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE)
    channel_id = models.IntegerField()
    culture = models.CharField(max_length=10)
    interval = models.CharField(max_length=10)
    image = models.ImageField(upload_to='ems_images/')
    created_at = models.DateTimeField(auto_now_add=True)