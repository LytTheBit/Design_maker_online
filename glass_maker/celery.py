import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "glass_maker.settings")
app = Celery("glass_maker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  # scopre trainer_app/tasks.py
