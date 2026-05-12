# Utilise une version légère de Python
FROM python:3.10-slim

# Évite que Python ne crée des fichiers .pyc et permet l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définit le dossier de travail
WORKDIR /app

# Installe les dépendances système nécessaires pour certaines libs (si besoin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie le fichier des dépendances en premier pour optimiser le cache Docker
COPY requirements.txt .

# Installe les bibliothèques Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du code
COPY . .

# Commande de démarrage (on utilise Gunicorn pour la stabilité)
# Remplace 'main' par le nom de ton fichier si besoin (ex: app:app)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
