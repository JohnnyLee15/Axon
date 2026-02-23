# Base image
FROM python:3.11-slim

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent buffered stdout
ENV PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements.txt to container
COPY requirements.txt .

# Install reqs
RUN pip install --no-cache-dir -r requirements.txt

# Copy Axon directory into /app
COPY . .