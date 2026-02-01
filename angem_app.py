import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Cloud Fix", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE ---
# Cette fonction utilise les Secrets TOML de Streamlit
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
    gc = gspread.service_account_from_dict(credentials)
    return gc

def load_data_from_gs():
    try:
        gc = get_gsheet_client()
        # Remplace par l'ID de ta feuille (le texte entre /d/ et /edit dans ton lien)
        sh = gc.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        return pd.DataFrame()

def save_data_to_gs(new_entry):
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        
        df_existing = load_data_from_gs()
        new_row = pd.DataFrame([new_entry])
        
        if not df_existing.empty:
            # Nettoyage pour éviter les erreurs de type
            df_existing = df_existing.astype(str)
            new_row = new_row.astype(str)
            # Suppression doublon
            mask = (df_existing["Accompagnateur"] == new_entry["Accompagnateur"]) & \
                   (df_existing["Mois"] == new_entry["Mois"]) & \
                   (df_existing["Annee"] == str(new_entry["Annee"]))
            df_existing = df_existing[~mask]
            df_final = pd.concat([df_existing, new_row], ignore_index=True)
        else:
            df_final = new_row
            
        # Écriture complète
        set_with_dataframe(worksheet, df_final)
        return True
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return False

# --- LISTE DES ACCOMPAGNATEURS ---
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

USERS = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS):
    USERS[nom] = str(1234 + (i * 4444))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Connexion Réseau ANGEM")
    u = st.selectbox("Utilisateur", list(USERS.keys()))
    p = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if USERS.get(u) == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# --- NAVIGATION ---
with st.sidebar:
    st.write(f"Utilisateur : **{st.session_state.user}**")
    menu = ["📝 Saisie Mensuelle", "📊 Suivi Admin", "📋 Liste des Accès"]
    if st.session_state.user != "admin": menu = ["📝 Saisie Mensuelle"]
    choix = st.radio("Menu", menu)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- SAISIE ---
if choix == "📝 Saisie Mensuelle":
    st.title("📝 Saisie du Bilan")
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent", LISTE_NOMS)
    
    c1, c2 = st.columns(2)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)

    # Récupération des rubriques
    st.subheader("1. Matière Première")
    colA, colB = st.columns(2)
    mp_dep = colA.number_input("Dossiers Déposés", 0)
    mp_fin = colB.number_input("Dossiers Financés", 0)

    st.subheader("Remboursements")
    colR1, colR2 = st.columns(2)
    r_nbr = colR1.number_input("Nombre de reçus", 0)
    r_mnt = colR2.number_input("Montant (DA)", 0.0)

    if st.button("💾 ENREGISTRER SUR LE CLOUD", type="primary", use_container_width=True):
        data = {
            "Accompagnateur": agent, "Mois": mois, "Annee": annee,
            "MP_Dep": mp_dep, "MP_Fin": mp_fin, "R_Nbr": r_nbr, "R_Mnt": r_mnt,
            "Last_Update": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        if save_data_to_gs(data):
            st.success("✅ Enregistré avec succès dans Google Sheets !")
            st.balloons()

# --- ADMIN ---
elif choix == "📊 Suivi Admin":
    st.title("📊 Suivi Global")
    df = load_data_from_gs()
    if not df.empty:
        st.dataframe(df)
        st.link_button("📂 Voir la Google Sheet en direct", f"https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    else:
        st.info("Aucune donnée disponible.")

elif choix == "📋 Liste des Accès":
    st.table([{"Nom": k, "Code": v} for k, v in USERS.items()])
