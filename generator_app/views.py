#C:\Users\Utente\OneDrive\Documenti\GitHub\Design_maker_online\generator_app\views.py
import os
import uuid
import cv2

from django.core.files.storage import default_storage
from django.conf import settings
import requests
from django.http import JsonResponse
import base64
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from pathlib import Path
from .models import LoraModel
from django.core.files.base import ContentFile
from .models import LoraModel, Generation



def generate(request):
    """
    – GET: mostra il form vuoto
    – POST con 'image': salva l’originale, genera il Canny e lo salva
    – POST con 'edited_canny': salva il Canny ritoccato e lo mostra
    """

    # ⬇️  PRIMA leggevi le cartelle; ORA leggiamo dal DB:
    model_list = list(
        LoraModel.objects
        .filter(is_active=True)
        .values_list("name", flat=True)
    )

    original_url = None
    canny_url    = None

    # Percorsi di upload relativi a MEDIA_ROOT
    upload_dir = 'uploads/'
    edited_dir = 'uploads/edited/'
    os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, edited_dir), exist_ok=True)

    if request.method == 'POST':

        # 1) Upload originale e generazione Canny
        if 'image' in request.FILES:
            img_file   = request.FILES['image']
            unique_name = f"{uuid.uuid4().hex}_{img_file.name}"
            orig_path   = os.path.join(upload_dir, unique_name)
            saved_path  = default_storage.save(orig_path, img_file)
            original_url = default_storage.url(saved_path)

            full_saved = os.path.join(settings.MEDIA_ROOT, saved_path)
            img_gray   = cv2.imread(full_saved, cv2.IMREAD_GRAYSCALE)
            edges      = cv2.Canny(img_gray, 100, 200)

            canny_name = f"canny_{unique_name}"
            canny_path = os.path.join(upload_dir, canny_name)
            full_canny = os.path.join(settings.MEDIA_ROOT, canny_path)
            cv2.imwrite(full_canny, edges)
            canny_url = default_storage.url(canny_path)

        # 2) Canvas modificato → sovrascrivi solo il Canny
        elif 'edited_canny' in request.FILES:
            edited      = request.FILES['edited_canny']
            edited_name = f"edited_{uuid.uuid4().hex}.png"
            edited_path = os.path.join(edited_dir, edited_name)
            saved_edit  = default_storage.save(edited_path, edited)
            canny_url   = default_storage.url(saved_edit)
            original_url = request.POST.get('original_url', None)

    return render(request, 'generator_app/generate.html', {
        'original_url': original_url, # URL dell'immagine originale caricata
        'canny_url':    canny_url, # URL dell'immagine Canny (originale o modificata)
        'models':       model_list,  # Lista dei modelli LoRA attivi
    })

# Funzione per verificare se l'utente è autenticato
@login_required
def train_lora(request):
    if request.user.groups.filter(name__in=['Addestratore']).exists() or request.user.is_superuser:
        return render(request, 'generator_app/train_lora.html', {
            'access_granted': True
        })
    else:
        return render(request, 'generator_app/train_lora.html', {
            'access_granted': False
        })

# Codice per la generazione di immagini tramite un server IA esterno
LAMBDA_SERVER_URL = "http://127.0.0.1:8010/generate"

def generate_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "Richiesta non valida"}, status=400)

    # --- Campi dal form ---
    prompt = request.POST.get("prompt", "").strip()
    model_name = request.POST.get("model", "").strip()  # nome del LoraModel scelto
    negative_prompt = request.POST.get("negative_prompt", "").strip()

    canny_file = request.FILES.get("edited_canny")  # immagine Canny modificata

    try:
        num_steps   = int(request.POST.get("num_inference_steps", 150))
        guidance    = float(request.POST.get("guidance_scale", 20))
        cond        = float(request.POST.get("extra_condition_scale", 0.6))
    except ValueError:
        return JsonResponse({"error": "Parametri numerici non validi"}, status=400)

    if not (prompt and canny_file and model_name):
        return JsonResponse({"error": "Dati mancanti"}, status=400)

    # --- Prende il Lora dal DB ---
    try:
        lora_obj = LoraModel.objects.get(name=model_name, is_active=True)
    except LoraModel.DoesNotExist:
        return JsonResponse({"error": "Modello non trovato o inattivo"}, status=400)

    try:
        # DEBUG
        print("Prompt:", prompt)
        print("Model:", lora_obj.name, "=> file:", lora_obj.file.name)
        print("Steps:", num_steps, "Guidance:", guidance, "Extra:", cond)

        # --- Leggi i bytes della canny UNA VOLTA e riusali sia per base64 che per salvataggio ---
        canny_bytes = canny_file.read()
        img_data_url = "data:image/png;base64," + base64.b64encode(canny_bytes).decode()

        # --- Crea riga Generation (status running) e salva subito la canny ---
        gen = Generation.objects.create(
            user=request.user,                 # richiede utente loggato
            lora=lora_obj,
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_steps,
            guidance_scale=guidance,
            extra_condition_scale=cond,
            status="running",
        )
        gen.canny_image.save(f"canny_{gen.id}.png", ContentFile(canny_bytes), save=True)

        # --- Prepara payload per il server IA ---
        payload = {
            "canny": img_data_url,
            "prompt": prompt,
            "model": lora_obj.name,           # nome "umano" (facoltativo)
            "model_file": lora_obj.file.name, # <-- path relativo es. "lora/xxx.safetensors"
            "num_inference_steps": num_steps,
            "guidance_scale": guidance,
            "extra_condition_scale": cond,
            "negative_prompt": negative_prompt,
        }

        print("Invio al server IA…")
        resp = requests.post(LAMBDA_SERVER_URL, json=payload, timeout=60)
        print("Status server IA:", resp.status_code)

        if resp.status_code != 200:
            gen.status = "error"
            gen.error  = resp.text
            gen.save(update_fields=["status", "error"])
            return JsonResponse({"error": "Errore dal server IA"}, status=500)

        data = resp.json()

        # --- Salva output nel DB se presente ---
        img_b64_url = data.get("image", "")
        if isinstance(img_b64_url, str) and img_b64_url.startswith("data:image"):
            _, b64 = img_b64_url.split(",", 1)
            gen.output_image.save(f"gen_{gen.id}.png", ContentFile(base64.b64decode(b64)), save=True)

        gen.status = "done"
        gen.save(update_fields=["status"])
        return JsonResponse(data)

    except Exception as e:
        print("Eccezione generate_image:", str(e))
        return JsonResponse({"error": f"Errore interno: {str(e)}"}, status=500)
