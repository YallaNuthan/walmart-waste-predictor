# Stage 1: build the frontend
FROM node:18‑alpine AS frontend-build
WORKDIR /app
# install node deps
COPY package.json package-lock.json ./
RUN npm ci
# copy and build your Vite/Tailwind app
COPY . .
RUN npm run build

# Stage 2: build the Python backend & bundle static assets
FROM python:3.10‑slim
# install system packages needed for numpy, pandas, etc.
RUN apt‑get update && apt‑get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    libatlas-base-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# copy Flask app and model files
COPY flask_app.py .
COPY *.pkl .

# copy built frontend into a `static` folder for Flask to serve
COPY --from=frontend-build /app/dist ./static

# expose the port your Flask/Gunicorn will run on
EXPOSE 10000

# launch with Gunicorn (production‑ready WSGI server)
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:10000", "flask_app:app"]
