"""Root URL configuration. Delegates everything under /api/ to the api package."""
from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
]

# An unrouted path and an unhandled crash never reach DRF, so they are
# answered in the same shape here rather than as Django's HTML pages.
handler404 = "utils.common.not_found"
handler500 = "utils.common.server_error"
