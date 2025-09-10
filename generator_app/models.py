from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LoraModel(models.Model):
    """
    Registro dei LoRA disponibili per il generatore.
    Il file .safetensors viene salvato in MEDIA_ROOT/lora/<nome>
    """
    name = models.CharField(max_length=100, unique=True)
    base_model = models.CharField(max_length=150, default="SG161222/Realistic_Vision_V4.0_noVAE")
    file = models.FileField(upload_to="lora/")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Generation(models.Model):
    """
    Log di ogni immagine generata
    """
    STATUS = [("queued","queued"),("running","running"),("done","done"),("error","error")]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lora = models.ForeignKey(LoraModel, on_delete=models.PROTECT)
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True)
    num_inference_steps = models.PositiveIntegerField(default=80)
    guidance_scale = models.FloatField(default=9.0)
    extra_condition_scale = models.FloatField(default=1.2)
    seed = models.BigIntegerField(default=1234)

    canny_image = models.ImageField(upload_to="canny/")
    output_image = models.ImageField(upload_to="generated/", blank=True)

    duration_ms = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="queued")
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gen {self.id} by {self.user}"


class TrainingJob(models.Model):
    """
    Job di addestramento (placeholder per step successivi)
    """
    STATUS = [("queued","queued"),("running","running"),("done","done"),("error","error")]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=150)  # nome modello in uscita
    dataset_path = models.CharField(max_length=500)
    params_json = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS, default="queued")
    logs_path = models.CharField(max_length=500, blank=True)
    output_lora_file = models.FileField(upload_to="lora/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Train {self.name} ({self.status})"

