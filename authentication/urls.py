
from django.urls import path,include
from .views import index

app_name = 'authentication'
urlpatterns = [
    path('', index, name='index' ),
   ]