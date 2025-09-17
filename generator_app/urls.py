from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "generator_app"

urlpatterns = [
    path("generate/", views.generate, name="generate"), # Main page per text generation
    path("generate-image/", views.generate_image, name="generate_image"), # Main page per image generation
    path("train-lora/", views.train_lora, name="train_lora"), # Main page per LoRA training
]