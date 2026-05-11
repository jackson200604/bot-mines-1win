# 1. Image de base légère (Python Slim)
FROM python:3.10-slim

# 2. Définir le répertoire de travail
WORKDIR /app

# 3. Copier les dépendances et les installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copier le reste du code
COPY . .

# 5. Lancer l'application avec Uvicorn
# On utilise la variable d'environnement PORT fournie par Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]# 1. Image de base légère (Python Slim)
FROM python:3.10-slim

# 2. Définir le répertoire de travail
WORKDIR /app

# 3. Copier les dépendances et les installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copier le reste du code
COPY . .

# 5. Lancer l'application avec Uvicorn
# On utilise la variable d'environnement PORT fournie par Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
