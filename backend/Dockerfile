# Utilise une version légère de Python
FROM python:3.10-slim

# Définit le dossier de travail
WORKDIR /app

# Copie et installe les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code
COPY . .

# Crée le dossier pour les vidéos
RUN mkdir -p temp_uploads

# Lance le bot
CMD gunicorn --bind 0.0.0.0:$PORT main:app
