# Stage 1: Build the frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app

# Copy everything up front (but .dockerignore will keep out local node_modules)
COPY . .

# Install deps fresh according to package-lock.json, then build
RUN npm ci
RUN npm run build
# Stage 2: Build the Python backend & bundle static assets
FROM python:3.10-slim AS backend-build
RUN apt-get update && apt-get install -y \
    build-essential python3-dev gcc g++ libatlas-base-dev libopenblas-dev \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
# 1) upgrade pip, install numpy wheel + Cython + wheel
# 2) install remaining packages without PEP517 isolation
RUN pip install --upgrade pip \
 && pip install --no-cache-dir "numpy>=1.24.4,<2.0" Cython wheel \
 && pip install --no-build-isolation --no-cache-dir -r requirements.txt
COPY flask_app.py *.pkl ./
COPY --from=frontend-build /app/dist ./static

# Stage 3: Production image
FROM python:3.10-slim
WORKDIR /app
COPY --from=backend-build /app /app
EXPOSE 10000
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:10000", "flask_app:app"]
