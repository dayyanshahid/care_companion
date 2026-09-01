from django.conf import settings
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("chat/", include("api.controllers.chatbot.urls")),
    path("knowledge/", include("api.controllers.knowledge.urls")),
    path(
        "assets/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "assets"},
    ),
]