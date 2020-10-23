import os

from django.http import HttpResponse, Http404
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAdminUser

from website.models import UserImageUpload, Upload, SquareLabel, PointLabel

import boto3
from boto3.s3.transfer import S3Transfer


@api_view(['POST'])
def send_image(request):
    # saves labels for requested Zip File Name and Image Name from requested user
    # if Bounding Box count is 2 and Point Data count is 1 this is an example of request.data:
    # request.data - {'ZipFile': 'File_1', 'ImageName': 'Image_1','BoundingBox_count': '2', 'Point_count': '1',
    #           'BoundingBox_0_data': '(5,5,10,10)', 'BoundingBox_0_color': 'blue', 'BoundingBox_0_classification': 'Car',
    #           'Point_0_data': '(20, 25, 5)', 'Point_0_color': 'black'}
    image = UserImageUpload.objects.all().filter(zipUpload__user=request.user).filter(
        zipUpload__zipName=request.data['ZipFile']).filter(imageName=request.data['ImageName']).first()
    labeledItems = SquareLabel.objects.all().filter(image__zipUpload__user=request.user).filter(
        image__zipUpload__zipName=request.data['ZipFile']).filter(image__imageName=request.data['ImageName'])
    # first time image is saved it will be recorded as saved
    if image.saved == False:
        image.saved = True
        image.save()
    # delete all former labels
    try:
        labeledItems.delete()
    except:
        print("Did not work")
    # extracts and saves data for labels in models
    for i in range(int(request.data["BoundingBox_count"])):
        coordinateArr = request.data[f"BoundingBox_{i}_data"].split(',')
        classification = request.data[f"BoundingBox_{i}_classification"]
        color = request.data[f"BoundingBox_{i}_color"]
        # extracts coordinates and removes parenthesis
        x = coordinateArr[0][1:]
        y = coordinateArr[1]
        w = coordinateArr[2]
        h = coordinateArr[3][:-1]
        label = SquareLabel(x=x, y=y, w=w, h=h, classification=classification, color=color, image=image)
        label.save()
    for i in range(int(request.data["Point_count"])):
        coordinateArr = request.data[f"Point_{i}_data"].split(',')
        color = request.data[f"Point_{i}_color"]
        # extracts coordinates and removes parenthesis
        x = coordinateArr[0][1:]
        y = coordinateArr[1]
        dimension = coordinateArr[2][:-1]
        label = PointLabel(x=x, y=y, dimension=dimension, color=color, image=image)
        label.save()
    return Response({"result": "success"})

@api_view(['POST'])
def download_count(request):
    # returns image down count for requested Image Name and Zip File name from requested user
    requested_image = UserImageUpload.objects.filter(imageName=request.data['ImageName']).filter(zipUpload__zipName=request.data['ZipFile']).filter(
        zipUpload__user=request.user).first()
    print("LETS SEE:")
    print(requested_image.count)
    return Response({"result":str(requested_image.count)})

@api_view(['POST'])
def download(request):
    user_id_full_string = f'user_{str(request.user.id)}'
    transfer = S3Transfer(boto3.client('s3', 'us-west-2',
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY))
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    temp_directory = os.path.join('media', *[user_id_full_string, 'transfer'])
    if os.path.exists(temp_directory):
        for root, dirs, files in os.walk(temp_directory):
            for name in files:
                local_path = os.path.join(root, name)
                os.remove(local_path)
    else:
        os.mkdir(temp_directory)
    temp_store = os.path.join('media', *[user_id_full_string, 'transfer', request.data['ImageName']])
    s3_path = os.path.join('media', *[user_id_full_string, request.data['ImageName']])
    transfer.download_file(bucket, s3_path, temp_store)
    # downloads an image for requested Image Name and Zip File Name from requested user
    #file_path = os.path.join(settings.MEDIA_ROOT, *[user_id_full_string,'image',request.data['ImageName']])
    requested_image_data = UserImageUpload.objects.filter(imageName=request.data['ImageName']).filter(
        zipUpload__zipName=request.data['ZipFile']).filter(
        zipUpload__user=request.user).first()
    requested_image_data.count += 1
    requested_image_data.save()
    # increments number of times image downloaded
    if os.path.exists(temp_store):
        with open(temp_store, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/force-download")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(temp_store)
            return response
    raise Http404

@api_view(['POST'])
def getLabel(request):
    # returns all labels for requested Image Name and Zip File Name from requested user
    # label is either Bounding Box or Point Data
    result = {}
    count = 0
    for i, items in enumerate(SquareLabel.objects.all().filter(image__imageName=request.data["ImageName"]).filter(
            image__zipUpload__zipName=request.data['ZipFile']).filter(image__zipUpload__user=request.user)):
        #result[i] = {'x':items.x, 'y':items.y, 'w':items.w, 'h':items.h, 'label':items.label}
        result[f"BoundingBox_{i}_data"] = f"({items.x},{items.y},{items.w},{items.h})"
        result[f"BoundingBox_{i}_color"] = items.color
        result[f"BoundingBox_{i}_classification"] = items.classification
        count += 1
    result["BoundingBox_count"] = str(count)
    count = 0
    for i, items in enumerate(PointLabel.objects.all().filter(image__imageName=request.data["ImageName"]).filter(
            image__zipUpload__zipName=request.data['ZipFile']).filter(image__zipUpload__user=request.user)):
        result[f"Point_{i}_data"] = f"({items.x},{items.y},{items.dimension})"
        result[f"Point_{i}_color"] = items.color
        count += 1
    result["Point_count"] = str(count)
    # if Bounding Box count is 2 and Point Data count is 1 this is an example result:
    # result - {'BoundingBox_count': '2', 'Point_count': '1', 'BoundingBox_0_data': '(5,5,10,10)', 'BoundingBox_0_color': 'blue',
    #           'BoundingBox_0_classification': 'Car', 'Point_0_data': '(20, 25, 5)', 'Point_0_color': 'black'}
    return Response(result)

@api_view(['GET'])
def zipFileName(request):
    # returns all zip file names from requested user
    zipFiles = Upload.objects.all().filter(user=request.user)
    result = {}
    for i, zip in enumerate(zipFiles):
        img = zip.userimageupload_set.all()
        unSavedCount = len(img.filter(saved=False))
        result[f"Data_{i}_name"] = zip.zipName
        result["Date"] = zip.upload_date
        # if all image labels have been saved - Data_{i}_saved will be set to true otherwise false
        if unSavedCount == 0:
            result[f"Data_{i}_saved"] = "true"
        else:
            result[f"Data_{i}_saved"] = "false"
    result["Count"] = str(len(zipFiles))
    # if number of zip files is 2 and example result:
    # result - {'Count': '2', 'Date': '1-2-4', 'Data_0_name': 'File_2', 'Data_1_name': 'File_2', 'Data_0_saved': 'true', 'Data_1_saved: 'false'}
    return Response(result)

@api_view(['POST'])
def imageName(request):
    # returns all image names for requested zip file from requested user
    # request contains user information and requested zip file name
    imageNames = UserImageUpload.objects.all().filter(zipUpload__user=request.user).filter(zipUpload__zipName=request.data['ZipFile'])
    result = {}
    for i, img in enumerate(imageNames):
        if img.saved == False:
            result[img.imageName] = "false" # image has never had saved labels
        else:
            result[img.imageName] = "true"  # images have had saved labels
    # example result:
    # result - {'image_1': 'true', 'image_2': 'false', 'image_3': 'true'}
    return Response(result)


@api_view(['POST'])
@permission_classes((IsAdminUser, ))
def reset(request):
    if request.method == 'POST':
        for items in UserImageUpload.objects.all():
            items.stage = '0'
            items.save()
        return Response({"result": "success"})