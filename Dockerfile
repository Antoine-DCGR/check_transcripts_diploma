FROM python:3.11-slim

WORKDIR /app

# ===============================
# Dépendances système (OBLIGATOIRES)
# ===============================
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    pkg-config \
    \
    # OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    \
    # PDF / images
    poppler-utils \
    qpdf \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    \
    # Math / ML
    libblas-dev \
    liblapack-dev \
    \
    # Divers
    libffi-dev \
    libssl-dev \
    \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Python deps
# ===============================
COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ===============================
# App
# ===============================
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
