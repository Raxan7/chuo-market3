from django.db import models

# Create your models here.
class EmailSignup(models.Model):
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=255, default="enrolling in the digital marketing course")

    def __str__(self):
        return self.email
