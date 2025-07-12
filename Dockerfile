# Use Python base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential python3-dev gcc g++ libatlas-base-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy backend code & ML models
COPY flask_app.py *.pkl ./

# Copy the static UI you exported from Lovable
COPY frontend ./frontend

EXPOSE 10000

# Start the Flask app with Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:10000", "flask_app:app"]
