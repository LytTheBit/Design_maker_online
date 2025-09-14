from django.urls import path
from . import views

app_name = "trainer_app"
urlpatterns = [
    path("train/", views.train_view, name="train"),
    path("status/<uuid:job_id>/", views.job_status, name="status"),
]
