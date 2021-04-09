from django.db import models

# Create your models here.
class UploadModel(models.Model):
    pic = models.FileField(upload_to=None)
    upload_date=models.DateTimeField(auto_now_add = True)

    def __repr__(self):
        return self.pic.name.split('/')[-1][:-4]