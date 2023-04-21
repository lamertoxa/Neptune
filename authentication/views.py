from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from asgiref.sync import sync_to_async
from django.contrib import messages

class User:
    def __init__(self,login=None,password=None,phone=None):
        self.login = login
        self.password= password
        self.phone= phone
async def index(request):
    if request.method == 'POST':
        if request.POST['login']:
            new_user = User(login=request.POST['login'])

        elif request.POST['phone']:
            new_user = User(phone=request.POST['phone'])

        return await sync_to_async(render)(request, 'welcome.html')
    return await sync_to_async(render)(request, 'index.html')
