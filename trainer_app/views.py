# trainer_app/views.py
import os, zipfile, uuid, logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import TrainingForm
from .tasks import start_training_in_background
from .models import TrainingJob

log = logging.getLogger(__name__)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied

def is_trainer(u):
    return u.is_authenticated and (u.is_superuser or u.groups.filter(name__in=["Addestratore","Admin"]).exists())


@login_required
def train_view(request):
    if not is_trainer(request.user):
        # niente form/job_id: solo il flag e 403
        if not is_trainer(request.user):
            return render(request, "trainer_app/train.html", {"access_granted": False}, status=403)

    # accesso consentito
    if request.method == "POST":
        form = TrainingForm(request.POST, request.FILES)
        print("FILES:", request.FILES.keys())  # DEBUG
        if form.is_valid():
            job_id = uuid.uuid4()

            # --- cartelle ---
            dataset_dir = os.path.join(settings.MEDIA_ROOT, "training_datasets", str(job_id))
            out_dir     = os.path.join(settings.MEDIA_ROOT, "training_out",      str(job_id))
            os.makedirs(dataset_dir, exist_ok=True)
            os.makedirs(out_dir,     exist_ok=True)

            # --- dataset ---
            if form.cleaned_data["zip_dataset"]:
                z = form.cleaned_data["zip_dataset"]
                zpath = os.path.join(dataset_dir, "dataset.zip")
                with open(zpath, "wb") as f:
                    for chunk in z.chunks():
                        f.write(chunk)
                with zipfile.ZipFile(zpath) as zf:
                    zf.extractall(dataset_dir)
                os.remove(zpath)
            else:
                for img in (form.cleaned_data.get("images") or []):
                    with open(os.path.join(dataset_dir, img.name), "wb") as f:
                        for c in img.chunks():
                            f.write(c)
                if form.cleaned_data.get("captions"):
                    cap = form.cleaned_data["captions"]
                    with open(os.path.join(dataset_dir, "captions.txt"), "wb") as f:
                        for c in cap.chunks():
                            f.write(c)

            # --- crea il job PRIMA di schedulare ---
            job = TrainingJob.objects.create(
                id=job_id,
                user=request.user,
                name=form.cleaned_data["name"],
                base_model=form.cleaned_data["base_model"],
                steps=form.cleaned_data["steps"],
                rank=form.cleaned_data["rank"],
                lr=form.cleaned_data["lr"],
                dataset_dir=dataset_dir,
                out_dir=out_dir,
                status="pending",
                progress=0,
            )
            print("CREATED JOB:", job.id)  # DEBUG

            start_training_in_background(str(job.id))

            # redirect con query ?job=<id> (coerente con urls sotto)
            return redirect(reverse("trainer_app:train") + f"?job={job_id}")

        # Form non valido
        print("FORM ERRORS:", form.errors, form.non_field_errors())
    else:
        form = TrainingForm()

    job_id = request.GET.get("job")
    return render(
        request,
        "trainer_app/train.html",
        {"form": form, "job_id": job_id, "access_granted": True}   # <-- QUI
    )

@login_required
def training_status(request, job_id):
    """
    API di polling: stato/progresso/log del training.
    """
    try:
        job = TrainingJob.objects.only("status", "progress", "log", "user", "name", "lora_file").get(id=job_id)
    except TrainingJob.DoesNotExist:
        return HttpResponseForbidden("Job non trovato.")

    if request.user != job.user and not request.user.is_superuser:
        return HttpResponseForbidden("Non autorizzato.")

    tail = (job.log or "")[-20000:]
    return JsonResponse({
        "status": job.status,
        "progress": job.progress or 0,
        "log": tail,
        "lora_ready": bool(getattr(job, "lora_file", None)),
        "lora_name": job.name,
    })
