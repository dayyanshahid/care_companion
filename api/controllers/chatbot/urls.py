from django.urls import path
from api.controllers.chatbot import views

urlpatterns = [
    path("message", views.send_message, name="chat-message"),
]