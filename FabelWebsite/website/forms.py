from django import forms

from .models import Upload

class UploadForm(forms.ModelForm):

    class Meta:
        model = Upload
        fields = ('pic',)

    def clean(self):
        print(self.cleaned_data)
