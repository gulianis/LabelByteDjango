from django import forms

from website.models import Upload

class NewUploadForm(forms.ModelForm):

    class Meta:
        model = Upload
        fields = ('pic',)