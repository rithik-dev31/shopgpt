from django.db import models

# Create your models here.

from django.db import models
import json

class ChatSession(models.Model):
    user_id = models.CharField(max_length=100, default='anon')
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class Product(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    platform = models.CharField(max_length=20)
    title = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField()
    data = models.JSONField(default=dict)
