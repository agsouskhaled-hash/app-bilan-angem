import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Complet", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE GOOGLE SHEETS ---
def get_gsheet_client():
    credentials = {
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
    return gspread.service_account_from_dict(credentials)

def load_data_from_gs():
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records())
    except: return pd.DataFrame()

def save_data_to_gs(new_entry):
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        df_existing = load_data_from_gs()
        new_row = pd.DataFrame([new_entry])
        if not df_existing.empty:
            df_existing = df_existing.astype(str)
            new_row = new_row.astype(str)
            mask = (df_existing["Accompagnateur"] == new_entry["Accompagnateur"]) & \
                   (df_existing["Mois"] == new_entry["Mois"]) & \
                   (df_existing["Annee"] == str(new_entry["Annee"]))
            df_existing = df_existing[~mask]
            df_final = pd.concat([df_existing, new_row], ignore_index=True)
        else: df_final = new_row
        worksheet.clear()
        set_with_dataframe(worksheet, df_final)
        return True
    except Exception as e:
        st.error(f"Erreur : {e}")
        return False

# --- LISTE DES UTILISATEURS ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]
USERS = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS): USERS[nom] = str(1234 + (i * 111))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Connexion ANGEM")
    u = st.selectbox("Utilisateur", [""] + list(USERS.keys()))
    p = st.text_input("Code", type="password")
    if st.button("Valider"):
        if u in USERS and USERS[u] == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- INTERFACE PRINCIPALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    if st.session_state.user == "admin":
        st.link_button("📂 Ouvrir Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    menu = ["📝 Saisie Mensuelle", "📊 Suivi Admin", "📋 Liste des Accès"]
    if st.session_state.user != "admin": menu = ["📝 Saisie Mensuelle"]
    choix = st.radio("Navigation", menu)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

if choix == "📝 Saisie Mensuelle":
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent", LISTE_NOMS)
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    data = {"Accompagnateur": agent, "Mois": mois, "Annee": annee, "Agence": agence, "Derniere_MAJ": datetime.now().strftime("%d/%m/%Y %H:%M")}

    # --- LES 10 ONGLETS ---
    tabs = st.tabs(["1. MP", "2. Tri", "3. Appels", "4. CAM", "5. AT", "6. Recyclage", "7. Tricycle", "8. Auto-Ent.", "9. NESDA", "10. Rappels"])

    def render_full_rubrique(prefix, title):
        st.subheader(title)
        col1, col2, col3, col4, col5 = st.columns(5
