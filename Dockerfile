FROM python:3.12-slim

# Dépendances système (OpenCV runtime + gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 build-essential ca-certificates git curl \
 && rm -rf /var/lib/apt/lists/*

# pdfresurrect (via APT – dispo sur Debian slim)
RUN apt-get update && apt-get install -y --no-install-recommends pdfresurrect \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 LC_ALL=C.UTF-8 LANG=C.UTF-8

# Dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Code
COPY . .

# Port Streamlit
EXPOSE 8501

# Commande par défaut = Streamlit (UI)
CMD ["streamlit", "run", "streamlit/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
