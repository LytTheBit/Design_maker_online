from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # generate view
    path("generate/", views.generate, name="generator"),

    # urls.py
    path("generate-image/", views.generate_image, name="generate_image"),

    # train view
    path('train-lora/',   views.train_lora,  name='train_lora'),
]