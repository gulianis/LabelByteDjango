from .models import CustomUser
def totalUserCount():
    return len(CustomUser.objects.all())