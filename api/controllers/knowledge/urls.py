"""Routes for the knowledge module."""
from django.urls import path

from api.controllers.knowledge import views

urlpatterns = [
    path("search", views.search_knowledge, name="knowledge-search"),
]
