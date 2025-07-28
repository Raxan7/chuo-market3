from django.contrib import admin
from .models import EmailSignup

@admin.register(EmailSignup)
class EmailSignupAdmin(admin.ModelAdmin):
    list_display = ('email', 'purpose', 'date_joined')
    search_fields = ('email', 'purpose')
    list_filter = ('purpose', 'date_joined')
