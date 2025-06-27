from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    # login/logout pronti di Django
    path('login/', auth_views.LoginView.as_view(template_name='account_app/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/menu/home/'), name='logout'),


    # Registrazione degli utenti
    path('register/', views.register, name='register'),
]