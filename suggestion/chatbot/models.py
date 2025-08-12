from django.db import models

class Place(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    category = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name
    
class FAQ(models.Model):
    question=models.TextField()
    answer=models.TextField()

    def __str__(self):
        return self.question[:50]


# Create your models here.
