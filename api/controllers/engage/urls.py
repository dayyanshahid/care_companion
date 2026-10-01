from django.urls import path

from api.controllers.engage import views

urlpatterns = [
    path("message", views.send_message, name="engage-message"),
    path("prompt/get", views.get_prompt, name="engage-prompt-get"),
    path("prompt/update", views.update_prompt, name="engage-prompt-update"),
]
