# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

RUN mkdir /app
# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt
RUN apt-get update && apt-get install -y curl
# Install system dependencies for Chrome and ChromeDriver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    xdg-utils

# Install Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install ChromeDriver
RUN LATEST_CHROMEDRIVER_VERSION=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$LATEST_CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip -o /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip


# Run app.py when the container launches
