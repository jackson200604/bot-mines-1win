import streamlit as st
import requests

st.title("🛡️ Bot Mines Predictor")

# Grille 5x5
grid_size = 5
mines_count = st.sidebar.slider("Nombre de mines", 1, 24, 3)

st.write("Sélectionnez les mines apparues lors des dernières parties :")

# Création de la grille visuelle
cols = st.columns(grid_size)
history = []

for i in range(grid_size * grid_size):
    with cols[i % grid_size]:
        if st.checkbox(f"{i+1}", key=f"tile_{i}"):
            history.append(i)

if st.button("Analyser la séquence"):
    # Appel vers ton backend Render (URL à changer après déploiement)
    backend_url = "https://ton-app-backend.onrender.com/predict"
    payload = {"history": history, "mines_count": mines_count}
    
    try:
        response = requests.post(backend_url, json=payload)
        res_data = response.json()
        st.success(f"Cases recommandées : {res_data['recommended_tiles']}")
    except:
        st.error("Connexion au backend impossible.")
