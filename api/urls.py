from django.urls import include, path

urlpatterns = [
    path("chat/", include("api.controllers.chatbot.urls")),
    path("prompt/", include("api.controllers.prompt.urls")),
]
