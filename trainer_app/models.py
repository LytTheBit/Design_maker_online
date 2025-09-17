from django.db import models

# trainer_app/models.py
import uuid
from django.conf import settings
from django.db import models

class LoRAModel(models.Model):
    """
    Modello salvato (file .safetensors) + metadati di base.
    """
    name = models.CharField(max_length=128, unique=True)
    base_model = models.CharField(max_length=128)  # es. "Realistic Vision 4.0"
    file = models.FileField(upload_to="lora/")     # MEDIA_ROOT/lora/...
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="trainer_lora_models",  # <— nome univoco lato User
    )

    def __str__(self):
        return self.name

class TrainingJob(models.Model):
    """
    Job di addestramento lanciato dal sito.
    """
    STATUS = [
        ("pending", "pending"),
        ("running", "running"),
        ("failed", "failed"),
        ("completed", "completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trainer_training_jobs",  # <— nome univoco lato User
    )

    # parametri principali
    name = models.CharField(max_length=128)     # nome del LoRA finale
    base_model = models.CharField(max_length=128)
    steps = models.PositiveIntegerField(default=800)
    rank  = models.PositiveIntegerField(default=16)
    lr    = models.FloatField(default=1e-4)

    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    progress = models.PositiveIntegerField(default=0)  # 0-100
    log = models.TextField(blank=True, default="")

    # I/O paths
    dataset_dir = models.CharField(max_length=512)
    out_dir = models.CharField(max_length=512)
    lora_file = models.FileField(upload_to="lora/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.status})"