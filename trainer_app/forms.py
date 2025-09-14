from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.widgets import ClearableFileInput


# --- Widget che permette la selezione multipla ---
class MultiFileInput(ClearableFileInput):
    allow_multiple_selected = True


# --- Campo che ACCETTA una lista di file ---
class MultiFileField(forms.FileField):
    widget = MultiFileInput

    default_error_messages = {
        "invalid": "File non valido.",
        "required": "Seleziona almeno un file.",
    }

    def to_python(self, data):
        """
        Accetta:
        - None / [] -> []
        - UploadedFile -> [UploadedFile]
        - [UploadedFile, ...] -> [UploadedFile, ...]
        """
        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        files = []
        for f in data:
            # check molto semplice: un UploadedFile ha 'name' e 'size'
            if not hasattr(f, "name") or not hasattr(f, "size"):
                raise ValidationError(self.error_messages["invalid"], code="invalid")
            files.append(f)
        return files

    def validate(self, data):
        """
        Per i campi richiesti, richiedi almeno un file nella lista.
        Per required=False non sollevare errori.
        """
        super().validate(None)  # evita la validazione del genitore su 'data' singolo
        if self.required and not data:
            raise ValidationError(self.error_messages["required"], code="required")


class TrainingForm(forms.Form):
    name = forms.CharField(label="Nome del LoRA", max_length=128)
    base_model = forms.ChoiceField(
        choices=[(k, k) for k in settings.LORA_BASE_MODELS.keys()]
    )
    steps = forms.IntegerField(min_value=50, max_value=20000, initial=800)
    rank = forms.IntegerField(min_value=4, max_value=128, initial=16)
    lr = forms.FloatField(initial=1e-4, localize=True)

    zip_dataset = forms.FileField(required=False)
    images = MultiFileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*"}),
    )
    captions = forms.FileField(required=False)

    # accetta "0,0001" oltre a "0.0001"
    def clean_lr(self):
        raw = (self.data.get("lr") or "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            raise ValidationError("Learning rate non valida.")

    def clean(self):
        cleaned = super().clean()
        has_zip = bool(cleaned.get("zip_dataset"))
        imgs = cleaned.get("images") or []
        if not has_zip and not imgs:
            raise ValidationError("Carica un dataset: ZIP oppure immagini singole.")
        return cleaned