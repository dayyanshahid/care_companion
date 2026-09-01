"""Root URL configuration. Delegates everything under /api/ to the api package."""
from django.conf import settings
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("api/", include("api.urls")),
    # The invitation email's images. Put a real web server in front of these
    # in production - this view is here so the mail renders without one.
    path(
        "assets/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "assets"},
    ),
]

# An unrouted path and an unhandled crash never reach DRF, so they are
# answered in the same shape here rather than as Django's HTML pages.
handler404 = "utils.common.not_found"
handler500 = "utils.common.server_error"
