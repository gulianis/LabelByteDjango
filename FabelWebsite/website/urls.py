from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('label/', views.label, name='label'),
    path('download-label-txt/', views.download_label_txt, name='download'),
    path('how-it-works/', views.howItWorks, name='how-it-works'),
    path('privacy-policy/', views.privacyPolicy, name='privacy-policy'),
    path('terms-of-service/', views.termsOfService, name='terms-of-service')
]
