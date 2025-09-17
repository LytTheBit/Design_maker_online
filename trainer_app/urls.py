from django.urls import path
from . import views

#app_name = "trainer_app" # Namespace for the app (opzionale ma consigliato)

urlpatterns = [
    path("train/", views.train_view, name="trainer_train"),
    path("status/<uuid:job_id>/", views.training_status, name="status"),
]
