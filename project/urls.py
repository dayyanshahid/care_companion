"""Root URL configuration. Delegates everything under /api/ to the api package."""
from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
]
