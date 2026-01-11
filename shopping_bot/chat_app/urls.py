from django.urls import path
from . import views
urlpatterns = [path('', views.chat_view, name='chat'),  # / → chat.html
    path('chat/', views.chat_view, name='chat_api'),  # POST endpoint
    path('health/', views.health, name='health')
]
    