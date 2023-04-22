from django.db import models

class CustomUser(models.Model):
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    phone = models.CharField(max_length=255, blank=True, null=True)