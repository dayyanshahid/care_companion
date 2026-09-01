from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
]

handler404 = "utils.common.not_found"
handler500 = "utils.common.server_error"
