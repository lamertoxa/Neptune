
from django.urls import path,include
from .views import index,handle_sms_verification

app_name = 'authentication'
urlpatterns = [
    path('', index, name='index' ),
    path('verification/', handle_sms_verification, name='verification')
]