# Utilise une version légère de Python
FROM python:3.10-slim

# Installe les dépendances système nécessaires pour OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Définit le dossier de travail
WORKDIR /app

# Copie le fichier des dépendances et l'installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du code
COPY . .

# Crée le dossier pour les uploads si absent
RUN mkdir -p temp_uploads

# Lance l'application avec Gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT main:app
