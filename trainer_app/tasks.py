# trainer_app/tasks.py
import os, re, json, shutil, subprocess, threading
from pathlib import Path
from django.conf import settings
from django.utils.text import slugify
from generator_app.models import LoraModel

def _run_training_job(job_id: str):
    from .models import TrainingJob
    job = TrainingJob.objects.get(id=job_id)

    job.status = "running"
    job.progress = 1
    job.log = "Avvio training…\n"
    job.save(update_fields=["status", "progress", "log"])

    dataset_dir = Path(job.dataset_dir)  # NECESSARIO (prima era str)
    out_dir     = Path(job.out_dir)      # NECESSARIO (prima era str)

    cmd = settings.TRAIN_CMD.format(
        base_model=job.base_model,
        dataset_dir=str(dataset_dir),
        out_dir=str(out_dir),
        steps=job.steps,
        rank=job.rank,
        lr=job.lr,
    )

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        cmd, shell=True, env=env, cwd=str(settings.BASE_DIR),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, text=True,
    )

    step_re = re.compile(r"^step=(\d+)\s*$")
    total = max(1, int(job.steps))

    try:
        for line in proc.stdout:
            job.log += line
            m = step_re.match(line.strip())
            if m:
                cur = int(m.group(1))
                job.progress = min(99, int(cur * 100 / total))
            job.save(update_fields=["log", "progress"])

        proc.wait()
        if proc.returncode != 0:
            job.status = "failed"
            job.progress = max(job.progress, 5)
            job.log += f"\nProcesso terminato con codice {proc.returncode}.\n"
            job.save(update_fields=["status", "progress", "log"])
            return

        # === success ===
        src = out_dir / "pytorch_lora_weights.safetensors"
        if not src.exists():
            cand = list(out_dir.glob("*.safetensors"))
            if not cand:
                job.status = "failed"
                job.log += "\nERRORE: Nessun file .safetensors prodotto dal training.\n"
                job.save(update_fields=["status", "log"])
                return
            src = cand[0]

        safe_name = slugify(job.name or f"lora-{job.id}")
        dest_dir = Path(settings.LORA_MODELS_DIR) / safe_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_file = dest_dir / "pytorch_lora_weights.safetensors"
        shutil.copy2(src, out_file)

        (dest_dir / "meta.json").write_text(json.dumps({
            "name": job.name, "base": job.base_model, "steps": job.steps,
            "rank": job.rank, "lr": job.lr,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        rel_path = str(out_file.relative_to(Path(settings.MEDIA_ROOT)))
        LoraModel.objects.update_or_create(
            name=safe_name, defaults={"file": rel_path, "is_active": True},
        )

        job.lora_name = safe_name
        job.status = "completed"
        job.progress = 100
        job.log += "\nTraining completato con successo.\n"
        job.save(update_fields=["lora_name", "status", "progress", "log"])

    except Exception as e:
        job.status = "failed"
        job.log += f"\nERRORE: {e}\n"
        job.save(update_fields=["status", "log"])

def start_training_in_background(job_id: str):
    threading.Thread(target=_run_training_job, args=(job_id,), daemon=True).start()
