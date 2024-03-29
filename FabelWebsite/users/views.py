from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.conf import settings

from .forms import CustomUserCreationForm, ChangePasswordForm

from users.models import CustomUser

from datetime import datetime, timedelta, timezone

from .dataUsage import totalUserCount

def register(request):
    limit = ''
    if request.method == "POST":
        # Mechanism to deal with excessive account creation
        if totalUserCount() >= settings.TOTAL_USER_LIMIT:
            limit = 'Registration temporarily unavailable. Check back soon.'
            form = CustomUserCreationForm()
        else:
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Account created, please login.')
                return redirect('login')

    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form, 'limit': limit})

@login_required
def profile(request):
    if request.POST:
        return redirect('change-password')
    return render(request, 'users/profile.html')


def forgotPassword(request):
    result = ''
    if request.method == "POST":
        check = CustomUser.objects.filter(email=request.POST['email'])
        if len(check) > 0:
            user_entered = check.first()
            if user_entered.new_password_date == None:
                user_entered.new_password_date = datetime.now(timezone.utc)
                user_entered.save()
            else:
                difference = datetime.now(timezone.utc) - user_entered.new_password_date
                day_difference = difference.days
                second_difference = difference.seconds
                if user_entered.new_password_count >= 2:
                    if day_difference == 0:
                        result = 'Reached daily password reset limit'
                        return render(request, 'users/sendPasswordReset.html', {'result': result})
                    else:
                        user_entered.new_password_date = datetime.now(timezone.utc)
                        user_entered.new_password_count = 1
                        user_entered.save()
                elif day_difference == 0:
                    user_entered.new_password_count += 1
                    user_entered.save()
                else:
                    user_entered.new_password_count = 1
                    user_entered.new_password_date = datetime.now(timezone.utc)
                    user_entered.save()
            password = CustomUser.objects.make_random_password()
            user_entered.set_password(password)
            user_entered.save()
            email = EmailMessage('Password Reset', f'Here is your new password: {password}', to=[user_entered.email])
            email.send()
            return render(request, 'users/Email.html')
        else:
            result = 'Account does not exist'
    return render(request, 'users/sendPasswordReset.html', {'result': result})

def emailSent(request):
    return render(request, 'users/Email.html')

def newPassword(request, code):
    print(code)
    return render(request, 'users/newPassword.html')

def isValidPassword(password):
    if len(password) < 8 or password.isnumeric == True:
        return False
    return True

@login_required
def changePassword(request):
    error = ''
    if request.POST:
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            oldPassword = form.cleaned_data['oldPassword']
            newPassword = form.cleaned_data['newPassword']
            newPasswordRetyped = form.cleaned_data['newPasswordRetyped']
            if request.user.check_password(oldPassword) == False:
                error = 'Incorrect password'
            elif newPassword != newPasswordRetyped:
                error = 'Retyped password does not match'
            elif isValidPassword(newPassword) == False:
                error = 'New password is not valid'
            else:
                request.user.set_password(newPassword)
                request.user.save()
                return render(request, 'users/passwordChange.html')
    else:
        form = ChangePasswordForm()
    return render(request, 'users/changePassword.html', {'form': form, 'error': error})