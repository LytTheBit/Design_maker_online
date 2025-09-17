# trainer_app/tasks.py
from django.conf import settings
from django.utils.text import slugify
from generator_app.models import LoraModel

import os, re, json, shutil, subprocess, threading
from pathlib import Path


def run_training_job(job_id: str):
    """
    Esegue il training in modo sincrono (una sola chiamata).
    Viene usata dal thread di background avviato dalla view.
    """
    from .models import TrainingJob

    job = TrainingJob.objects.get(id=job_id)
    dataset_dir = Path(job.dataset_dir)
    out_dir     = Path(job.out_dir)

    # stato iniziale
    job.status   = "running"
    job.progress = 1
    job.log      = (job.log or "") + "Avvio training…\n"
    job.save(update_fields=["status", "progress", "log"])

    # comando esterno (definito in settings.TRAIN_CMD)
    cmd = settings.TRAIN_CMD.format(
        base_model = job.base_model,
        dataset_dir= str(dataset_dir),
        out_dir    = str(out_dir),
        steps      = int(job.steps),
        rank       = int(job.rank),
        lr         = float(job.lr),
    )

    # importantissimo per output riga-per-riga
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        cmd,
        shell=True,
        env=env,
        cwd=str(settings.BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,  # line-based
    )

    step_re = re.compile(r"step=(\d+)")
    total   = max(1, int(job.steps))

    try:
        # stream del log e progress
        for line in proc.stdout:
            job.log += line
            m = step_re.search(line)
            if m:
                cur = int(m.group(1))
                job.progress = min(99, int(cur * 100 / total))
            job.save(update_fields=["log", "progress"])

        proc.wait()

        if proc.returncode != 0:
            job.status   = "failed"
            job.progress = max(job.progress or 0, 5)
            job.log     += f"\nProcesso terminato con codice {proc.returncode}.\n"
            job.save(update_fields=["status", "progress", "log"])
            return  # esco senza alzare eccezione (il DB ha già lo stato)

        # ===== SUCCESSO =====
        src = out_dir / "pytorch_lora_weights.safetensors"
        if not src.exists():
            cand = list(out_dir.glob("*.safetensors"))
            if not cand:
                raise FileNotFoundError("Nessun file .safetensors prodotto dal training.")
            src = cand[0]

        safe_name = slugify(job.name or f"lora-{job.id}")
        lora_dir  = Path(settings.LORA_MODELS_DIR) / safe_name
        lora_dir.mkdir(parents=True, exist_ok=True)

        out_file = lora_dir / "pytorch_lora_weights.safetensors"
        shutil.copy2(src, out_file)

        # metadati
        (lora_dir / "meta.json").write_text(json.dumps({
            "name":  job.name,
            "base":  job.base_model,
            "steps": int(job.steps),
            "rank":  int(job.rank),
            "lr":    float(job.lr),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        # path relativo per FileField
        rel_path = str(out_file.relative_to(Path(settings.MEDIA_ROOT)))

        # aggiorna/crea il modello usabile dal generatore
        LoraModel.objects.update_or_create(
            name=safe_name,
            defaults={"file": rel_path, "is_active": True},
        )

        job.lora_name = safe_name
        job.status    = "completed"
        job.progress  = 100
        job.log      += "\nTraining completato con successo.\n"
        job.save(update_fields=["lora_name", "status", "progress", "log"])

    except Exception as e:
        job.status = "failed"
        job.log    = (job.log or "") + f"\nERRORE: {e}\n"
        job.save(update_fields=["status", "log"])
        # non rilancio: lo stato è già visibile al polling


def start_training_in_background(job_id: str):
    """
    Avvia run_training_job(job_id) in un thread (niente Celery, niente Redis).
    """
    t = threading.Thread(target=run_training_job, args=(job_id,), daemon=True)
    t.start()


# Alias opzionali per retro-compatibilità: se altrove importo questi nomi, non esplode nulla
run_training_task = run_training_job
