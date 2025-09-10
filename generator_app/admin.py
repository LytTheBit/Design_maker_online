from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import LoraModel, Generation, TrainingJob

admin.site.register(LoraModel)
admin.site.register(Generation)
admin.site.register(TrainingJob)

