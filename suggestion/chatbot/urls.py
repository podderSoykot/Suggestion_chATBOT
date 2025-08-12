from django.urls import path
from .views import NearestPlacesAPIView,ChatbotMessageAPIView

urlpatterns = [
    path('nearest-places/', NearestPlacesAPIView.as_view(), name='nearest-places'),
    path('message/', ChatbotMessageAPIView.as_view(), name='chatbot-message'),
]
