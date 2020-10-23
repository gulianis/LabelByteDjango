from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = CustomUser
        fields = ('email',)

class GetEmailForm(forms.Form):
    email = forms.EmailField(max_length=70)

class ChangePasswordForm(forms.Form):

    oldPassword = forms.CharField(max_length=32, widget=forms.PasswordInput)
    newPassword = forms.CharField(max_length=32, widget=forms.PasswordInput)
    newPasswordRetyped = forms.CharField(max_length=32, widget=forms.PasswordInput)
