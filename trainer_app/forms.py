from django import forms
from django.conf import settings
from django.forms.widgets import ClearableFileInput

class MultiFileInput(ClearableFileInput):
    allow_multiple_selected = True

class TrainingForm(forms.Form):
    name = forms.CharField(label="Nome del LoRA", max_length=128)
    base_model = forms.ChoiceField(choices=[(k, k) for k in settings.LORA_BASE_MODELS.keys()])
    steps = forms.IntegerField(min_value=50, max_value=20000, initial=800)
    rank  = forms.IntegerField(min_value=4, max_value=128, initial=16)
    lr    = forms.FloatField(initial=1e-4)

    zip_dataset = forms.FileField(required=False)
    images = forms.FileField(widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*"}), required=False)
    captions = forms.FileField(required=False)

    def clean(self):
        cleaned = super().clean()
        # serve almeno uno tra zip o immagini
        has_zip = bool(cleaned.get("zip_dataset"))
        has_imgs = bool(self.files.getlist("images"))  # <— importante
        if not has_zip and not has_imgs:
            raise forms.ValidationError("Carica un dataset: ZIP oppure immagini singole.")
        return cleaned