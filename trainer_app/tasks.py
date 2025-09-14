# trainer_app/tasks.py
# trainer_app/tasks.py
import os, shlex, subprocess, re, glob
from celery import shared_task
from django.conf import settings
from django.core.files import File
from .models import TrainingJob, LoRAModel

# cerca "step=123" o "global_step 123" nei log per stimare la % di avanzamento
STEP_RE = re.compile(r"(?:step\s*=?\s*|global_step\s+)(\d+)", re.IGNORECASE)

@shared_task(bind=True)
def run_training_task(self, job_id: str):
    job = TrainingJob.objects.get(pk=job_id)
    try:
        job.status = "running"; job.progress = max(1, job.progress); job.save(update_fields=["status","progress"])

        # mappa la chiave visibile di base_model nel vero path/HF id
        base = settings.LORA_BASE_MODELS[job.base_model]
        ctx = {
            "base_model": base,
            "dataset_dir": job.dataset_dir,
            "out_dir": job.out_dir,
            "steps": job.steps,
            "rank": job.rank,
            "lr": job.lr,
        }
        cmd = settings.TRAIN_CMD.format(**ctx)
        job.log = (job.log or "") + f"$ {cmd}\n"; job.save(update_fields=["log"])

        # lancia il processo e streamma i log
        proc = subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )

        max_seen = 0
        for line in proc.stdout:
            job.log += line
            m = STEP_RE.search(line)
            if m:
                step = int(m.group(1))
                if step > max_seen:
                    max_seen = step
                    pct = min(99, int(100 * max_seen / max(job.steps, 1)))
                    if pct != job.progress:
                        job.progress = pct
            job.save(update_fields=["log","progress"])

        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Training failed with exit {proc.returncode}")

        # trova il .safetensors prodotto
        candidates = sorted(
            glob.glob(os.path.join(job.out_dir, "*.safetensors")) +
            glob.glob(os.path.join(job.out_dir, "**", "*.safetensors"), recursive=True),
            key=os.path.getmtime, reverse=True
        )
        if not candidates:
            raise RuntimeError("Nessun file .safetensors trovato nell'out_dir")

        final_path = candidates[0]
        # salva nella media/lora/ e registra anche su LoRAModel
        with open(final_path, "rb") as f:
            job.lora_file.save(f"{job.name}.safetensors", File(f), save=True)

        LoRAModel.objects.create(
            name=job.name,
            base_model=job.base_model,  # conservo la label visibile
            file=job.lora_file,
            owner=job.user
        )

        job.status = "completed"; job.progress = 100
        job.save(update_fields=["status","progress"])
        return "ok"

    except Exception as e:
        job.status = "failed"
        job.log = (job.log or "") + f"\n[ERROR] {e}\n"
        job.save(update_fields=["status","log"])
        raise
