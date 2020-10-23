import os, zipfile
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.template.defaultfilters import filesizeformat

from .forms import UploadForm
from .models import UserImageUpload, Upload, SquareLabel, PointLabel

from users.models import CustomUser

from datetime import datetime, timedelta

from celery.decorators import task

import boto3
from boto3.s3.transfer import S3Transfer

@task(bind=True, name="delete_data")
def delete_data(self, user_id, zipName, img_list):
    # Deletes zip just uploaded after some specified time
    CurrentUser = CustomUser.objects.get(id=user_id)
    try:
        Upload.objects.filter(user_id = user_id).filter(zipName=zipName).first().delete()
    except:
        print("It did not work")
    while len(img_list) > 0:
        img_name = img_list.pop()
        #CurrentUser.total_data_usage -= os.path.getsize(img_name)
        #CurrentUser.save()
        os.remove(img_name)
    return "Deleted From Memory"


@task(bind=True, name='do_stuff')
def do_stuff(self):
    return 2

def delete_zip(added_img, zipObject, total_img_memory, CurrentUser):
    # Deletes zipObject which will delete all child nodes including grand-children great-grand-children ect...
    while len(added_img) > 0:
        try:
            os.remove(added_img.pop())
        except:
            print("Was not able to remove image")
    try:
        zipObject.delete()
    except:
        print("Was not able to remove zip from db")
    if total_img_memory > settings.ZIP_FILE_SIZE_LIMIT:
        error = f"You have exceeded file upload limit of: {filesizeformat(settings.ZIP_FILE_SIZE_LIMIT)}"
    else:
        error = f"You have exceeded monthly upload limit. {filesizeformat(settings.PROFILE_UPLOAD_LIMIT - CurrentUser.total_data_usage)} remaining."
    return error

def get_name(name, nameDict):
    # Replaces spaces with _
    if name in nameDict:
        i = 2
        while name in nameDict:
            if i > 2:
                name = name[:-2]
            name += '_' + str(i)
            i += 1
    return name


@login_required
def label(request):
    #at_time = datetime.utcnow() + timedelta(seconds=10)
    #do_stuff.apply_async(args=(), eta=at_time)
    user_id = str(request.user.id)
    user_id_full_string = f'user_{str(request.user.id)}'
    user_path = os.path.join(settings.MEDIA_ROOT, user_id_full_string)
    image_path = os.path.join(user_path, 'image')
    txt_path = os.path.join(user_path, 'txt')
    error = ''
    if request.POST:
        CurrentUser = CustomUser.objects.get(id=request.user.id)
        if request.FILES['pic'].size > settings.ZIP_FILE_SIZE_LIMIT:
            zipObject = UploadForm
            error = f"You have exceeded file upload limit of: {filesizeformat(settings.ZIP_FILE_SIZE_LIMIT)}"
        elif request.FILES['pic'].size + CurrentUser.total_data_usage > settings.PROFILE_UPLOAD_LIMIT:
            zipObject = UploadForm
            error = f"You have exceeded monthly upload limit. {filesizeformat(settings.PROFILE_UPLOAD_LIMIT - CurrentUser.total_data_usage)} remaining."
        else:
            zipObject = UploadForm(request.POST, request.FILES)
            zipNameDict = {items.zipName:1 for items in Upload.objects.filter(user=request.user)}
            if zipObject.is_valid():
                # store information about zip file in db
                zipObject = zipObject.save(commit=False)
                zipObject.user = request.user
                zipName = '_'.join(os.path.basename(zipObject.pic.name)[:-4].split(' '))
                zipObject.zipName = get_name(zipName, zipNameDict)
                zipObject.save()
                # creates location to store uploaded files
                for path_type in [user_path, image_path, txt_path, txt_path]:
                    if not os.path.isdir(path_type):
                        os.mkdir(path_type)
                print(zipObject.upload_date)
                zip_file_path = os.path.join(settings.MEDIA_ROOT, *[user_id_full_string,'zip',os.path.basename(zipObject.pic.name)])
                # extract unzipped files
                #img.pic.name follows format user_(id)/zip/(file_name)
                with zipfile.ZipFile(zip_file_path) as zf:
                    total_img_memory = 0
                    added_img = []
                    fileNameDict = {}
                    for name in zf.namelist():
                        #Zip file contains extra garbage
                        # Look at specific files
                        if name.endswith(('png','jpeg','jpg')) and 'MACOSX' not in name:
                            file_data = zf.read(name)
                            file_name = '_'.join(os.path.basename(name).split(' '))
                            suffix_start = file_name.rfind('.')
                            file_name_without_suffix = file_name[:suffix_start]
                            file_name_suffix = file_name[suffix_start:]
                            file_name_revised = get_name(file_name_without_suffix, fileNameDict) + file_name_suffix
                            fileNameDict[file_name_without_suffix] = 1
                            #os.path.basename(name) gives name of image file
                            with open(os.path.join(image_path,file_name_revised), "wb") as fout:
                                fout.write(file_data)
                            total_img_memory += os.path.getsize(os.path.join(image_path,file_name_revised))
                            added_img.append(os.path.join(image_path,file_name_revised))
                            # Check to make sure unzipped doesn't exceed memory
                            # if it does delete unzipped files and db entrees
                            if total_img_memory > settings.ZIP_FILE_SIZE_LIMIT or total_img_memory + CurrentUser.total_data_usage > settings.PROFILE_UPLOAD_LIMIT:
                                error = delete_zip(added_img, zipObject, total_img_memory, CurrentUser)
                                total_img_memory = 0
                                break
                            imageData = UserImageUpload(imageName=file_name_revised, zipUpload=zipObject)
                            imageData.save()
                    if total_img_memory > 0:
                        CurrentUser.total_data_usage += total_img_memory
                        CurrentUser.save()
                    #at_time = datetime.utcnow() + timedelta(seconds=120)
                    #delete_data.apply_async(args=(request.user.id, zipObject.zipName, added_img), eta=at_time)
                os.remove(zip_file_path)
                if settings.USE_S3 == True:
                    transfer = S3Transfer(boto3.client('s3', 'us-west-2',
                                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY))
                #client = boto3.client('s3')
                    bucket = settings.AWS_STORAGE_BUCKET_NAME
                    for root, dirs, files in os.walk(image_path):
                        for name in files:
                            local_path = os.path.join(root, name)
                            s3_path = os.path.join('media', *[user_id_full_string, name])
                            transfer.upload_file(local_path, bucket, s3_path)
                    for root, dirs, files in os.walk(image_path):
                        for name in files:
                            local_path = os.path.join(root, name)
                            os.remove(local_path)
    zipObject = UploadForm
    try:
        images = [items.zipName + '.zip' for items in Upload.objects.filter(user=request.user)]
    except:
        images = None
    return render(request, 'website/label.html', {'form': zipObject,'images': images, 'error': error})

def home(request):
    return render(request, 'website/home.html')

def howItWorks(request):
    return render(request, 'website/howItWorks.html')

@login_required
def download_label_txt(request):
    # write labels to txt file
    user_id_full_string = f'user_{str(request.user.id)}'
    file_path = os.path.join(settings.MEDIA_ROOT, *[user_id_full_string,'txt','data.txt'])
    if os.path.exists(file_path):
        os.remove(file_path)
    # any previous text file will be deleted and rewritten with new data
    f = open(file_path, "w")
    for label in SquareLabel.objects.filter(image__zipUpload__user=request.user):
        written_label = f"File-Name:{label.image.imageName},Label:BoundingBox,X:{label.x},Y:{label.y},Width:{label.w},Height:{label.h},Classification:{label.classification}\n"
        f.write(written_label)
        print(label.image.imageName)
    for label in PointLabel.objects.filter(image__zipUpload__user=request.user):
        written_label = f"File-Name:{label.image.imageName},Label:Point,X:{label.x},Y:{label.y}\n"
        f.write(written_label)
    f.close()
    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type="application/force-download")
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        return response
    raise Http404