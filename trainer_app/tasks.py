# trainer_app/tasks.py
from celery import shared_task

@shared_task(bind=True)
def run_training_task(self, job_id: str):
    # Stub per avvio senza errori; lo sostituiremo con il vero training
    return "ok"
