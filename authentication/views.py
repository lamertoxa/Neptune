import logging

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from asgiref.sync import sync_to_async
from django.contrib import messages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class User:
    def __init__(self,login=None,password=None,phone=None,driver=None):
        self.login = login
        self.password= password
        self.phone= phone
        self.driver= driver


async def index(request):
    driver = await selenium_function()
    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')

        phone = request.POST.get('phone')
        if password:
            pass
        elif login:
            new_user = User(login=login)
        elif phone:
            new_user = User(phone=phone)
        else:
            messages.error(request, 'Please enter login or phone')
            return await sync_to_async(render)(request, 'index.html')

        username_login = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID,'login'))
        )


        return await sync_to_async(render)(request, 'welcome.html',{'login_name':username_login.get_attribute('value')})

    return await sync_to_async(render)(request, 'index.html')



async def selenium_function(user):
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.get("https://passport.yandex.ru")

    # Очікування на елемент логіна
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "passp-field-login"))
    )

    login_submit = driver.find_element(by=By.ID,value="passp:sign-in")
    username_input.send_keys(user.login)
    login_submit.click()
    return driver
