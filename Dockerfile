FROM python:3.12-slim
# Dépendances système (OpenCV runtime, build tools, ExifTool, pdfresurrect, poppler pour pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    ca-certificates \
    git \
    curl \
    pdfresurrect \
    exiftool \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8
# Dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
# Code
COPY . .
# Port Streamlit
EXPOSE 8501
# Commande par défaut = Streamlit (UI)
CMD ["streamlit", "run", "streamlit/app.py", "--server.address=0.0.0.0", "--server.port=8501"]