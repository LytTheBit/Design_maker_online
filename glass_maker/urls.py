"""
URL configuration for glass_maker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    # switch lingua (sempre senza prefisso)
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    path('menu/',      include('menu_app.urls')), # per testare il menu senza cambiare la homepage
    path('account/',   include('account_app.urls')), # login, logout, registrazione, profilo
    path('generator/', include('generator_app.urls')), # generatore di immagini (bicchieri)
    path("trainer/", include(("trainer_app.urls", "trainer_app"), namespace="trainer_app")), # addestramento AI

    # homepage
    path('', include('menu_app.urls')),

    prefix_default_language=False,
)

# Servi i MEDIA solo in sviluppo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)