from django.urls import path
from .views import (
    talent_list, talent_detail, post_talent, add_comment, like_talent,
    edit_talent, delete_talent
)

urlpatterns = [
    path('', talent_list, name='talent_list'),
    path('<int:pk>/', talent_detail, name='talent_detail'),
    path('post/', post_talent, name='post_talent'),
    path('<int:pk>/comment/', add_comment, name='add_comment'),
    path('<int:pk>/like/', like_talent, name='like_talent'),
    path('<int:pk>/edit/', edit_talent, name='edit-talent'),
    path('<int:pk>/delete/', delete_talent, name='delete-talent'),
]
