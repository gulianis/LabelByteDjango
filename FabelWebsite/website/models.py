from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

User = settings.AUTH_USER_MODEL

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/zip/<filename>
    user_id_full_string = f'user_{str(instance.user.id)}'
    return f'{user_id_full_string}/zip/{filename}'

class Upload(models.Model):
    pic = models.FileField(upload_to=user_directory_path)
    upload_date=models.DateTimeField(auto_now_add = True)
    zipName = models.CharField(max_length=256)
    complete = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __repr__(self):
        return self.pic.name.split('/')[-1][:-4]

class UserImageUpload(models.Model):
    imageName = models.CharField(max_length=256)
    coordinateData = models.TextField()
    zipUpload = models.ForeignKey(Upload, on_delete=models.CASCADE)
    saved = models.BooleanField(default=False)
    count = models.IntegerField(default=0)

class SquareLabel(models.Model):
    x = models.CharField(max_length=256)
    y = models.CharField(max_length=256)
    w = models.CharField(max_length=256)
    h = models.CharField(max_length=256)
    classification = models.CharField(max_length=256)
    color = models.CharField(max_length=256)
    image = models.ForeignKey(UserImageUpload, on_delete=models.CASCADE)

    def __repr__(self):
        return "SquareLabel"

class PointLabel(models.Model):
    x = models.CharField(max_length=256)
    y = models.CharField(max_length=256)
    dimension = models.CharField(max_length=256)
    color = models.CharField(max_length=256)
    image = models.ForeignKey(UserImageUpload, on_delete=models.CASCADE)

    def __repr__(self):
        return "PointLabel"
