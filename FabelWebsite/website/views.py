import os, zipfile, boto3
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.template.defaultfilters import filesizeformat

from .forms import UploadForm
from .models import UserImageUpload, Upload, SquareLabel, PointLabel

from users.models import CustomUser

from datetime import datetime, timedelta, timezone

from celery.decorators import task

import boto3
from boto3.s3.transfer import S3Transfer

@task(bind=True, name="delete_data")
def delete_data(self, user_id, zipName, img_list):
    # Deletes zip just uploaded after some specified time
    """
    if settings.USE_S3 == False:
        while len(img_list) > 0:
            img_name = img_list.pop()
            #CurrentUser.total_data_usage -= os.path.getsize(img_name)
            #CurrentUser.save()
            os.remove(img_name)
    else:
        user_id_full_string = f'user_{str(user_id)}'
        client = boto3.client('s3', 'us-west-1',
                     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        last = ""
        while len(img_list) > 0:
            img_name = os.path.basename(img_list.pop())
            some_path = os.path.join('media', *[user_id_full_string, zipName, img_name])
            client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=some_path)
            last = some_path
        return last
    """
    for items in UserImageUpload.objects.all().filter(zipUpload__user_id=user_id).filter(zipUpload__zipName=zipName):
        print(items)
        if settings.USE_S3 == False:
            os.remove(items.imageName)
        else:
            user_id_full_string = f'user_{str(user_id)}'
            client = boto3.client('s3', 'us-west-1',
                                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            some_path = os.path.join('media', *[user_id_full_string, zipName, items.imageName])
            client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=some_path)
    try:
        Upload.objects.filter(user_id = user_id).filter(zipName = zipName).first().delete()
    except:
        print("It did not work")
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

def label_helper(user, user_id, user_id_full_string, files, post):
    error = ''
    #user_id = str(request_call.user.id)
    #user_id_full_string = f'user_{str(request_call.user.id)}'
    user_path = os.path.join(settings.MEDIA_ROOT, user_id_full_string)
    image_path = os.path.join(user_path, 'image')
    txt_path = os.path.join(user_path, 'txt')
    CurrentUser = CustomUser.objects.get(id=user_id)
    if files['pic'].size > settings.ZIP_FILE_SIZE_LIMIT:
        zipObject = UploadForm
        error = f"You have exceeded file upload limit of: {filesizeformat(settings.ZIP_FILE_SIZE_LIMIT)}"
    elif files['pic'].size + CurrentUser.total_data_usage > settings.PROFILE_UPLOAD_LIMIT:
        zipObject = UploadForm
        error = f"You have exceeded monthly upload limit. {filesizeformat(settings.PROFILE_UPLOAD_LIMIT - CurrentUser.total_data_usage)} remaining."
    else:
        zipObject = UploadForm(post, files)
        zipNameDict = {items.zipName: 1 for items in Upload.objects.filter(user=user)}
        if zipObject.is_valid():
            # store information about zip file in db
            zipObject = zipObject.save(commit=False)
            zipObject.user = user
            zipName = '_'.join(os.path.basename(zipObject.pic.name)[:-4].split(' '))
            zipObject.zipName = get_name(zipName, zipNameDict)
            zipObject.save()
            #return None, None
            # creates location to store uploaded files
            for path_type in [user_path, image_path, txt_path, txt_path]:
                if not os.path.isdir(path_type):
                    os.mkdir(path_type)
            # print(zipObject.upload_date + timedelta(days=40))
            # if zipObject.download_date == None:
            #    zipObject.download_date = datetime.now()
            # else:
            #    zipObject.download_date = zipObject.download_date + timedelta(days=40)
            # zipObject.save()
            # print(zipObject.upload_date)
            # print(zipObject.download_date)
            zip_file_path = os.path.join(settings.MEDIA_ROOT,
                                         *[user_id_full_string, 'zip', os.path.basename(zipObject.pic.name)])
            # extract unzipped files
            # img.pic.name follows format user_(id)/zip/(file_name)
            with zipfile.ZipFile(zip_file_path) as zf:
                total_img_memory = 0
                added_img = []
                fileNameDict = {}
                pic_exists = False  # Make sure one img file exists
                for name in zf.namelist():
                    # Zip file contains extra garbage
                    # Look at specific files
                    if name.endswith(('png', 'jpeg', 'jpg', 'PNG', 'JPEG', 'JPG', 'heic', 'HEIC')) and 'MACOSX' not in name:
                        pic_exists = True
                        file_data = zf.read(name)
                        file_name = '_'.join(os.path.basename(name).split(' '))
                        suffix_start = file_name.rfind('.')
                        file_name_without_suffix = file_name[:suffix_start]
                        file_name_suffix = file_name[suffix_start:]
                        file_name_revised = get_name(file_name_without_suffix, fileNameDict) + file_name_suffix
                        fileNameDict[file_name_without_suffix] = 1
                        # os.path.basename(name) gives name of image file
                        with open(os.path.join(image_path, file_name_revised), "wb") as fout:
                            fout.write(file_data)
                        total_img_memory += os.path.getsize(os.path.join(image_path, file_name_revised))
                        added_img.append(os.path.join(image_path, file_name_revised))
                        # Check to make sure unzipped doesn't exceed memory
                        # if it does delete unzipped files and db entrees
                        if total_img_memory > settings.ZIP_FILE_SIZE_LIMIT or total_img_memory + CurrentUser.total_data_usage > settings.PROFILE_UPLOAD_LIMIT:
                            error = delete_zip(added_img, zipObject, total_img_memory, CurrentUser)
                            total_img_memory = 0
                            break
                        imageData = UserImageUpload(imageName=file_name_revised, zipUpload=zipObject)
                        imageData.save()
                if pic_exists == False:
                    delete_zip(added_img, zipObject, total_img_memory, CurrentUser)
                    error = "NO IMAGE FILES IN ZIP FILE"
                    total_img_memory = 0
                if total_img_memory > 0:
                    CurrentUser.total_data_usage += total_img_memory
                    CurrentUser.save()
                    if settings.DELETION == True:
                        if user_id == 1:
                            pass
                        else:
                            #at_time = datetime.utcnow() + timedelta(days=3)
                            at_time = datetime.utcnow() + timedelta(minutes=20)
                            delete_data.apply_async(args=(user_id, zipObject.zipName, added_img), eta=at_time)
            os.remove(zip_file_path)
            if settings.USE_S3 == True:
                transfer = S3Transfer(boto3.client('s3', 'us-west-1',
                                                   aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                                   aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY))
                # client = boto3.client('s3')
                bucket = settings.AWS_STORAGE_BUCKET_NAME
                for root, dirs, files in os.walk(image_path):
                    for name in files:
                        local_path = os.path.join(root, name)
                        s3_path = os.path.join('media', *[user_id_full_string, zipObject.zipName, name])
                        transfer.upload_file(local_path, bucket, s3_path)
                for root, dirs, files in os.walk(image_path):
                    for name in files:
                        local_path = os.path.join(root, name)
                        os.remove(local_path)
        else:
            error = "INCORRECT FILE TYPE"
    return error, zipObject

@login_required
def label(request):
    #at_time = datetime.utcnow() + timedelta(seconds=10)
    #do_stuff.apply_async(args=(), eta=at_time)
    user_id = str(request.user.id)
    user_id_full_string = f'user_{str(request.user.id)}'
    #user_path = os.path.join(settings.MEDIA_ROOT, user_id_full_string)
    #image_path = os.path.join(user_path, 'image')
    #txt_path = os.path.join(user_path, 'txt')
    error = ''
    if request.POST:
        """
        print(request.FILES)
        print(request.POST)
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
                #print(zipObject.upload_date + timedelta(days=40))
                #if zipObject.download_date == None:
                #    zipObject.download_date = datetime.now()
                #else:
                #    zipObject.download_date = zipObject.download_date + timedelta(days=40)
                #zipObject.save()
                #print(zipObject.upload_date)
                #print(zipObject.download_date)
                zip_file_path = os.path.join(settings.MEDIA_ROOT, *[user_id_full_string,'zip',os.path.basename(zipObject.pic.name)])
                # extract unzipped files
                #img.pic.name follows format user_(id)/zip/(file_name)
                with zipfile.ZipFile(zip_file_path) as zf:
                    total_img_memory = 0
                    added_img = []
                    fileNameDict = {}
                    pic_exists = False  # Make sure one img file exists
                    for name in zf.namelist():
                        #Zip file contains extra garbage
                        # Look at specific files
                        if name.endswith(('png','jpeg','jpg')) and 'MACOSX' not in name:
                            pic_exists = True
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
                    if pic_exists == False:
                        delete_zip(added_img, zipObject, total_img_memory, CurrentUser)
                        error = "NO IMAGE FILES IN ZIP FILE"
                        total_img_memory = 0
                    if total_img_memory > 0:
                        CurrentUser.total_data_usage += total_img_memory
                        CurrentUser.save()
                        if settings.DELETION == True:
                            if request.user.id == 1:
                                pass
                            else:
                                at_time = datetime.utcnow() + timedelta(days=3)
                                delete_data.apply_async(args=(request.user.id, zipObject.zipName, added_img), eta=at_time)
                os.remove(zip_file_path)
                if settings.USE_S3 == True:
                    transfer = S3Transfer(boto3.client('s3', 'us-west-1',
                                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY))
                #client = boto3.client('s3')
                    bucket = settings.AWS_STORAGE_BUCKET_NAME
                    for root, dirs, files in os.walk(image_path):
                        for name in files:
                            local_path = os.path.join(root, name)
                            s3_path = os.path.join('media', *[user_id_full_string, zipObject.zipName, name])
                            transfer.upload_file(local_path, bucket, s3_path)
                    for root, dirs, files in os.walk(image_path):
                        for name in files:
                            local_path = os.path.join(root, name)
                            os.remove(local_path)
            else:
                error = "INCORRECT FILE TYPE"
        """
        error, zipObject = label_helper(request.user, user_id, user_id_full_string, request.FILES, request.POST)
        zipObject = UploadForm
    else:
        zipObject = UploadForm
    try:
        images = [items.zipName + '.zip' for items in Upload.objects.filter(user=request.user)]
    except:
        images = None
    return render(request, 'website/label.html', {'form': zipObject,'images': images, 'error': error})

def home(request):
    text_desktop = " LabelByte allows you to label image data on a mobile device. Available for \n" \
                   " iPhone and iPad. To get started download the app. Create account by clicking register \n" \
                   " in the navigation bar or tapping create account on the app. You can upload images to the cloud \n" \
                   " either here or through the app. Login to the app to access your uploaded images and label  \n" \
                   " them with bounding boxes or points. The coordinate data of these labels in addition  \n" \
                   " to a classification label for bounding boxes is downloadable as a txt file. "
    text_mobile = " LabelByte allows you to label \n " \
                  " image data on a mobile device. \n" \
                  " Available for iPhone and iPad. To get \n" \
                  " started download the app. Create \n" \
                  " account  by clicking register in the \n" \
                  " navigation  bar or tapping create \n" \
                  " account on the app. You can upload \n" \
                  " images to the cloud either here or \n" \
                  " through the app. Login to the app to \n" \
                  " access your uploaded coordinate data \n" \
                  " of these labels in addition to a \n" \
                  " classification label for bounding boxes \n" \
                  " is downloadable as a txt file. \n"
    is_mobile = False
    text = text_desktop
    if 'Mobile' in request.META['HTTP_USER_AGENT']:
        is_mobile = True
        text = text_mobile
    return render(request, 'website/home.html', {'text': text, 'is_mobile': is_mobile})

def contact(request):
    is_mobile = False
    if 'Mobile' in request.META['HTTP_USER_AGENT']:
        is_mobile = True
    return render(request, 'website/contact.html', {'is_mobile': is_mobile})

def privacyPolicy(request):
    return render(request, 'website/privacy-policy.html')

def privacyPolicyApp(request):
    return render(request, 'website/privacy-policy-app.html')


def termsOfService(request):
    return render(request, 'website/terms-of-service.html')

def instructions(request):
    is_mobile = False
    if 'Mobile' in request.META['HTTP_USER_AGENT']:
        is_mobile = True
    return render(request, 'website/instructions.html', {'is_mobile': is_mobile})

def faq(request):
    if 'Mobile' in request.META['HTTP_USER_AGENT']:
        return render(request, 'website/faq.html', {'width': '300px', 'height': '1250px', 'is_mobile': True})
    return render(request, 'website/faq.html', {'width': '1000px', 'height': '800px', 'is_mobile': False})

@login_required
def download_label_txt(request):
    # write labels to txt file

    # deals with excessive download requests
    if request.user.download_date == None:
        request.user.download_date = datetime.now(timezone.utc)
        request.user.save()
    else:
        difference = datetime.now(timezone.utc)-request.user.download_date
        day_difference = difference.days
        second_difference = difference.seconds
        if request.user.download_count >= 5:
            if day_difference == 0 and second_difference <= 1200:
                raise Http404
            else:
                request.user.download_date = datetime.now(timezone.utc)
                request.user.download_count = 1
                request.user.save()
        elif day_difference == 0 and second_difference < 60:
            request.user.download_count += 1
            request.user.save()
        else:
            request.user.download_date = datetime.now(timezone.utc)
            request.user.save()
    user_id_full_string = f'user_{str(request.user.id)}'
    file_path = os.path.join(settings.MEDIA_ROOT, *[user_id_full_string,'txt','data.txt'])
    if os.path.exists(file_path):
        os.remove(file_path)
    if not os.path.exists(settings.MEDIA_ROOT):
        raise Http404
    # any previous text file will be deleted and rewritten with new data
    #print(Upload.objects.get(user=request.user).download_date)
    f = open(file_path, "w")
    for label in SquareLabel.objects.filter(image__zipUpload__user=request.user):
        written_label = f"ZipFile-Name:{label.image.zipUpload.zipName},File-Name:{label.image.imageName},Label:BoundingBox,X:{label.x},Y:{label.y},Width:{label.w},Height:{label.h},Classification:{label.classification}\n"
        f.write(written_label)
    for label in PointLabel.objects.filter(image__zipUpload__user=request.user):
        written_label = f"ZipFile-Name:{label.image.zipUpload.zipName},File-Name:{label.image.imageName},Label:Point,X:{label.x},Y:{label.y}\n"
        f.write(written_label)
    f.close()
    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type="application/force-download")
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        return response
    raise Http404

