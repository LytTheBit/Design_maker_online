from django import forms
from django.conf import settings

class TrainingForm(forms.Form):
    name = forms.CharField(label="Nome del LoRA", max_length=128)
    base_model = forms.ChoiceField(choices=[(k,k) for k in settings.LORA_BASE_MODELS.keys()])
    steps = forms.IntegerField(min_value=50, max_value=20000, initial=800)
    rank  = forms.IntegerField(min_value=4, max_value=128, initial=16)
    lr    = forms.FloatField(initial=1e-4)
    zip_dataset = forms.FileField(required=False)
    images = forms.FileField(widget=forms.ClearableFileInput(attrs={"multiple": True}), required=False)
    captions = forms.FileField(required=False)
