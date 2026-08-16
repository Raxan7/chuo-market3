from django.urls import path
from .views import (
    MaterialListView,
    MaterialDetailView,
    MaterialCreateView,
    MaterialUpdateView,
    MaterialDeleteView,
)

app_name = 'materials'

urlpatterns = [
    path('', MaterialListView.as_view(), name='list'),
    path('add/', MaterialCreateView.as_view(), name='create'),
    path('<int:pk>/', MaterialDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', MaterialUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', MaterialDeleteView.as_view(), name='delete'),
]