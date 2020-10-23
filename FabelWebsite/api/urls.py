from . import views

from django.urls import path

from rest_framework.authtoken import views as viewsToken

urlpatterns = [
    path('send_image/', views.send_image, name='send_image'),
    path('download/', views.download, name='download'),
    path('download-count/', views.download_count, name='download-count'),
    path('zipFileName/', views.zipFileName, name="zipFileName"),
    path('imageName/', views.imageName, name="imageName"),
    path('getLabel/', views.getLabel, name="getLabel"),
    path('reset/', views.reset, name='reset'),
    path('token-auth/', viewsToken.obtain_auth_token),
]
