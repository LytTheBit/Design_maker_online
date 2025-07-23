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



def generate(request):
    """
    – GET: mostra il form vuoto
    – POST con 'image': salva l’originale, genera il Canny e lo salva
    – POST con 'edited_canny': salva il Canny ritoccato e lo mostra
    """

    original_url = None
    canny_url    = None

    # Percorsi di upload relativi a MEDIA_ROOT
    upload_dir      = 'uploads/'
    edited_dir      = 'uploads/edited/'
    os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, edited_dir), exist_ok=True)

    if request.method == 'POST':

        # 1) Upload originale e generazione Canny
        if 'image' in request.FILES:
            img_file = request.FILES['image']
            # Usa un nome univoco
            unique_name = f"{uuid.uuid4().hex}_{img_file.name}"
            orig_path   = os.path.join(upload_dir, unique_name)
            # Salva nel media storage
            saved_path  = default_storage.save(orig_path, img_file)
            original_url = default_storage.url(saved_path)

            # Genera Canny
            full_saved = os.path.join(settings.MEDIA_ROOT, saved_path)
            img_gray   = cv2.imread(full_saved, cv2.IMREAD_GRAYSCALE)
            edges      = cv2.Canny(img_gray, 100, 200)

            # Salva il Canny
            canny_name = f"canny_{unique_name}"
            canny_path = os.path.join(upload_dir, canny_name)
            full_canny = os.path.join(settings.MEDIA_ROOT, canny_path)
            cv2.imwrite(full_canny, edges)
            canny_url = default_storage.url(canny_path)

        # 2) Se arriva invece il canvas modificato, sovrascrivi solo il Canny
        elif 'edited_canny' in request.FILES:
            edited = request.FILES['edited_canny']
            # Nome univoco per la versione ritoccata
            edited_name = f"edited_{uuid.uuid4().hex}.png"
            edited_path = os.path.join(edited_dir, edited_name)
            saved_edit  = default_storage.save(edited_path, edited)
            canny_url   = default_storage.url(saved_edit)
            # Mantieni la precedente original_url se presente in GET params
            original_url = request.POST.get('original_url', None)

    # Passa sempre al template le URL (anche None)
    return render(request, 'generator_app/generate.html', {
        'original_url': original_url,
        'canny_url':    canny_url,
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
LAMBDA_SERVER_URL = "http://129.146.65.221:7860/generate"

def generate_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "Richiesta non valida"}, status=400)

    # Recupera i dati dal form
    prompt = request.POST.get("prompt")
    negative_prompt = request.POST.get("negative_prompt", "").strip()

    canny_file = request.FILES.get("edited_canny")

    try:
        num_steps = int(request.POST.get("num_inference_steps", 80))
        guidance = float(request.POST.get("guidance_scale", 9.0))
        conditioning = float(request.POST.get("controlnet_conditioning_scale", 1.2))
    except ValueError:
        return JsonResponse({"error": "Parametri numerici non validi"}, status=400)

    if not prompt or not canny_file:
        return JsonResponse({"error": "Dati mancanti"}, status=400)

    try:
        # DEBUG
        print("Prompt ricevuto:", prompt)
        print("Negative Prompt:", negative_prompt)
        print("Steps:", num_steps, "Guidance:", guidance, "Conditioning:", conditioning)

        # Codifica in base64
        img_base64 = base64.b64encode(canny_file.read()).decode()
        img_data_url = f"data:image/png;base64,{img_base64}"
        print("Base64 pronta (lunghezza):", len(img_data_url))

        # Prepara i dati per il server IA
        payload = {
            "canny": img_data_url, # Usa l'immagine Canny come input
            "prompt": prompt, # Aggiungi il prompt
            "num_inference_steps": num_steps, # Aggiungi il numero di passi di inferenza
            "guidance_scale": guidance, # Aggiungi il guidance scale
            "controlnet_conditioning_scale": conditioning, # Aggiungi il conditioning scale
            "negative_prompt": negative_prompt, # Aggiungi il negative prompt se presente
        }

        print("Invio richiesta al server IA...")
        response = requests.post(LAMBDA_SERVER_URL, json=payload, timeout=60)
        print("Risposta server:", response.status_code)

        if response.status_code != 200:
            print("Contenuto errore:", response.text)
            return JsonResponse({"error": "Errore dal server IA"}, status=500)

        return JsonResponse(response.json())

    except Exception as e:
        print("Eccezione generata:", str(e))
        return JsonResponse({"error": f"Errore interno: {str(e)}"}, status=500)