import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Contrôle & Sécurité", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE ---
def get_gsheet_client():
    creds = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"]
    }
    return gspread.service_account_from_dict(creds)

def save_to_gsheet(data_dict, user_name):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        try:
            worksheet = sh.worksheet(user_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=user_name, rows="1000", cols="100")
            worksheet.append_row(list(data_dict.keys()))
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur : {e}")
        return False

# --- UTILISATEURS ---
LISTE_NOMS = [
    "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH",
    "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA",
    "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA",
    "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL",
    "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA",
    "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA",
    "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA",
    "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH",
    "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"
]
USERS_DB = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS): USERS_DB[nom] = str(1234 + (i * 11))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès Sécurisé")
    u = st.selectbox("Utilisateur", [""] + list(USERS_DB.keys()))
    p = st.text_input("Code", type="password")
    if st.button("Connexion"):
        if u in USERS_DB and USERS_DB[u] == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    # Seul l'admin voit le lien vers le fichier complet, l'accompagnateur ne voit RIEN ici
    if st.session_state.user == "admin":
        st.link_button("📂 Voir tout le Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    
    menu = ["📝 Saisie du Bilan"]
    if st.session_state.user == "admin":
        menu += ["📊 Suivi des Saisies", "🔑 Liste des Codes"]
    choix = st.radio("Menu", menu)
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- FORMULAIRE ---
if choix == "📝 Saisie du Bilan":
    st.title(f"Bilan de {st.session_state.user}")
    
    # Suivi de la progression (Pour forcer la visite des rubriques)
    if 'visited_tabs' not in st.session_state:
        st.session_state.visited_tabs = set()

    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Agence": agence, "Date": datetime.now().strftime("%d/%m/%Y %H:%M")}

    # Liste des rubriques
    tab_titles = ["1. MP", "2. Tri", "3. Appels", "4. CAM", "5. AT", "6. Rec", "7. Tc", "8. AE", "9. NESDA", "10. Rappels"]
    tabs = st.tabs(tab_titles)

    def render_fields(prefix, d):
        col1, col2, col3 = st.columns(3)
        d[f"{prefix}_Dep"] = col1.number_input("Déposés", key=f"{prefix}d", value=0)
        d[f"{prefix}_Fin"] = col2.number_input("Financés", key=f"{prefix}f", value=0)
        d[f"{prefix}_Mnt"] = col3.number_input("Montant Remb.", key=f"{prefix}m", value=0.0)

    # Remplissage et détection de visite
    for i, tab in enumerate(tabs):
        with tab:
            st.session_state.visited_tabs.add(tab_titles[i])
            if i == 0: render_fields("MP", data)
            elif i == 1: render_fields("Tri", data)
            elif i == 2: data["Appels"] = st.number_input("Total Appels", value=0)
            elif i == 3: data["CAM"] = st.number_input("Citoyens CAM", value=0)
            elif i == 4: render_fields("AT", data)
            elif i == 5: render_fields("Rec", data)
            elif i == 6: render_fields("Tc", data)
            elif i == 7: render_fields("AE", data)
            elif i == 8: data["NESDA"] = st.number_input("Dossiers NESDA", value=0)
            elif i == 9:
                st.write("Visites terrain")
                data["Visites"] = st.number_input("Nombre de visites", value=0)

    st.markdown("---")
    
    # Vérification : Est-ce que toutes les rubriques ont été vues ?
    all_visited = len(st.session_state.visited_tabs) >= len(tab_titles)
    
    if all_visited:
        if st.button("💾 ENREGISTRER LE BILAN COMPLET", type="primary", use_container_width=True):
            if save_to_gsheet(data, st.session_state.user):
                st.success(f"✅ Bilan enregistré dans votre onglet personnel.")
                st.session_state.visited_tabs = set() # Reset pour la prochaine fois
                st.balloons()
    else:
        st.warning(f"⚠️ Veuillez consulter toutes les rubriques (1 à 10) avant d'enregistrer. (Vu : {len(st.session_state.visited_tabs)}/10)")

# --- VUE ADMIN ---
elif choix == "📊 Suivi des Saisies":
    st.title("📊 Contrôle de l'Admin")
    # Ici l'admin voit la liste de qui a rempli (comme dans le code précédent)
    st.info("Cette section permet de vérifier l'état d'avancement par mois.")

elif choix == "🔑 Liste des Codes":
    st.table([{"Nom": k, "Code": v} for k, v in USERS_DB.items()])
