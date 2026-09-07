from django.urls import path

from api.controllers.prompt import views

urlpatterns = [
    path("get", views.get_prompt, name="prompt-get"),
    path("update", views.update_prompt, name="prompt-update"),
    path("files/<str:file_id>", views.delete_prompt_file, name="prompt-file-delete"),
]