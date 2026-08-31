from django.urls import path

from api.controllers.chatbot import views

urlpatterns = [
    path("patients", views.list_patients, name="chat-patients"),
    path("start", views.start_chat, name="chat-start"),
    path("message", views.send_message, name="chat-message"),
    path("conversations", views.list_conversations, name="chat-conversations"),
    path("conversations/<str:ident>", views.read_conversation, name="chat-read"),
]
