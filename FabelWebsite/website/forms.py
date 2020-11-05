from django import forms

from .models import Upload
from django.core.exceptions import ValidationError

class UploadForm(forms.ModelForm):

    class Meta:
        model = Upload
        fields = ('pic',)

    def validate_file_extension(self, file):
        if file.content_type != 'application/zip':
            raise ValidationError(u'Wrong File Type')

    def clean(self):
        self.validate_file_extension(self.cleaned_data['pic'])
