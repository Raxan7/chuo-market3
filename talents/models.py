from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Talent(models.Model):
    CATEGORY_CHOICES = [
        ('music', 'Music'),
        ('art', 'Art'),
        ('writing', 'Writing'),
        ('coding', 'Coding'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    media = models.FileField(upload_to='talents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    talent = models.ForeignKey(Talent, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.talent.title}"


class Like(models.Model):
    talent = models.ForeignKey(Talent, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('talent', 'user')  # Prevents duplicate likes

    def __str__(self):
        return f"{self.user.username} liked {self.talent.title}"
