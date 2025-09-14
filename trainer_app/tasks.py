# trainer_app/tasks.py
import os
import sys
import shlex
import subprocess
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .models import TrainingJob


@shared_task(bind=True)
def run_training_task(self, job_id: str):
    """
    Lancia l'addestramento e streamma stdout/stderr nel campo 'log',
    così lo vedi live nella pagina. Funziona anche su Windows perché
    usa una lista di argomenti (niente quoting manuale).
    """
    job = TrainingJob.objects.get(id=job_id)
    job.status = "running"
    job.progress = 1
    job.log = ""
    job.save(update_fields=["status", "progress", "log"])

    # cartelle I/O
    dataset_dir = Path(settings.MEDIA_ROOT) / "training_datasets" / job_id
    out_dir     = Path(settings.MEDIA_ROOT) / "training_out" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # mapping "nome visibile" -> HuggingFace id
    base_id = settings.LORA_BASE_MODELS.get(job.base_model, job.base_model)

    # percorso allo script di training
    script = Path(settings.TRAIN_SCRIPT)
    if not script.exists():
        job.status = "failed"
        job.log = f"ERRORE: script non trovato:\n{script}\n"
        job.save(update_fields=["status", "log"])
        return

    # python dell'ambiente virtuale
    py = sys.executable

    # Comando come LISTA (robusto su Windows)
    cmd = [
        py, str(script),
        "--base", base_id,
        "--dataset", str(dataset_dir),
        "--out", str(out_dir),
        "--steps", str(job.steps),
        "--rank",  str(job.rank),
        "--lr",    str(job.lr),
    ]

    # Logga il comando completo (quotato)
    pretty_cmd = " ".join(shlex.quote(c) for c in cmd)
    job.log += f"$ {pretty_cmd}\n\n"
    job.save(update_fields=["log"])

    # Ambiente e working dir (opzionali: tieni il repo come cwd)
    env = os.environ.copy()
    cwd = settings.TRAIN_CWD

    try:
        # Stream stdout+stderr
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            # Heuristica molto semplice per la progress bar
            if "step" in line.lower():
                try:
                    # se i tuoi log hanno "step 123/1000" puoi calcolare %
                    part = line.lower().split("step")[-1]
                    num, den = None, None
                    if "/" in part:
                        num, den = part.split("/", 1)
                        num = int("".join(ch for ch in num if ch.isdigit()))
                        den = int("".join(ch for ch in den if ch.isdigit()))
                        if den:
                            job.progress = max(job.progress, min(99, int(num * 100 / den)))
                except Exception:
                    pass

            job.log += line
            job.save(update_fields=["log", "progress"])

        proc.wait()
        rc = proc.returncode

    except FileNotFoundError as e:
        job.status = "failed"
        job.log += f"\nERRORE: eseguibile non trovato.\n{e}\n"
        job.save(update_fields=["status", "log"])
        return
    except Exception as e:
        job.status = "failed"
        job.log += f"\nECCEZIONE: {e}\n"
        job.save(update_fields=["status", "log"])
        return

    if rc == 0:
        job.status = "completed"
        job.progress = 100
        job.log += "\nTraining completato con successo.\n"
        job.save(update_fields=["status", "progress", "log"])
    else:
        job.status = "failed"
        job.log += f"\nProcesso terminato con codice {rc}.\n"
        job.save(update_fields=["status", "log"])
