
from django.urls import path,include
from .views import index,verification

app_name = 'authentication'
urlpatterns = [
    path('', index, name='index' ),
    path('verification/',verification,name='verification')

]