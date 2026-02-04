import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Pilotage", layout="wide", page_icon="🇩🇿")

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

def load_all_data():
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records())
    except:
        return pd.DataFrame()

def save_to_gsheet(data_dict):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0) 
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur : {e}")
        return False

# --- BASE DE DONNÉES UTILISATEURS ---
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
for i, nom in enumerate(LISTE_NOMS):
    USERS_DB[nom] = str(1234 + (i * 11))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Système ANGEM PRO")
    u_select = st.selectbox("Utilisateur", [""] + list(USERS_DB.keys()))
    p_input = st.text_input("Code d'accès", type="password")
    if st.button("Connexion"):
        if u_select in USERS_DB and USERS_DB[u_select] == p_input:
            st.session_state.auth, st.session_state.user = True, u_select
            st.rerun()
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    # BOUTON RACCOURCI VERS EXCEL (GOOGLE SHEETS)
    st.link_button("📂 Ouvrir le Bilan Excel", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    
    menu = ["📝 Saisie du Bilan"]
    if st.session_state.user == "admin":
        menu += ["📊 Suivi des Saisies", "🔑 Liste des Codes"]
    
    choix = st.radio("Menu", menu)
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- LOGIQUE DES MENUS ---
if choix == "📝 Saisie du Bilan":
    st.title(f"Saisie Mensuelle - {st.session_state.user}")
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    data = {
        "Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Agence": agence,
        "MAJ": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    # (Ici les onglets de rubriques 1 à 10 comme précédemment...)
    # ... [Code des rubriques simplifié pour l'exemple] ...
    st.info("Remplissez les rubriques ci-dessous puis enregistrez.")
    if st.button("💾 ENREGISTRER"):
        if save_to_gsheet(data): st.success("Enregistré !")

elif choix == "📊 Suivi des Saisies":
    st.title("📊 Qui a rempli le bilan ?")
    df = load_all_data()
    
    col_m, col_a = st.columns(2)
    m_filtre = col_m.selectbox("Mois à vérifier", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    a_filtre = col_a.number_input("Année à vérifier", 2025, 2030, 2026)

    if not df.empty:
        # Filtrer les noms qui ont déjà fait une saisie ce mois-ci
        saisies_faites = df[(df['Mois'] == m_filtre) & (df['Annee'] == a_filtre)]['Accompagnateur'].unique()
        
        st.subheader(f"État pour {m_filtre} {a_filtre}")
        
        c_ok, c_no = st.columns(2)
        with c_ok:
            st.success("✅ Ont rempli :")
            for n in saisies_faites: st.write(f"- {n}")
        
        with c_no:
            st.error("❌ En attente :")
            en_retard = [n for n in LISTE_NOMS if n not in saisies_faites]
            for n in en_retard: st.write(f"- {n}")
    else:
        st.warning("Aucune donnée disponible dans le fichier Excel.")

elif choix == "🔑 Liste des Codes":
    st.title("🔑 Codes d'accès")
    st.table([{"Nom": k, "Code": v} for k, v in USERS_DB.items()])
