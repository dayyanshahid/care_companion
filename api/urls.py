from django.urls import include, path

urlpatterns = [
    path("chat/", include("api.controllers.chatbot.urls")),
    path("knowledge/", include("api.controllers.knowledge.urls")),
]
