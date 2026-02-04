import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

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

def save_to_gsheet(data_dict):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0) 
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur de communication : {e}")
        return False

# --- LISTE DES ACCOMPAGNATEURS ET GÉNÉRATION DES CODES ---
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

# Création du dictionnaire des utilisateurs avec leurs codes
USERS_DB = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS):
    USERS_DB[nom] = str(1234 + (i * 11)) # Génère un code unique par personne

# --- SYSTÈME D'AUTHENTIFICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accès Système Bilan ANGEM")
    u_select = st.selectbox("Sélectionnez votre nom", [""] + list(USERS_DB.keys()))
    p_input = st.text_input("Entrez votre code d'accès", type="password")
    
    if st.button("Se connecter"):
        if u_select in USERS_DB and USERS_DB[u_select] == p_input:
            st.session_state.auth = True
            st.session_state.user = u_select
            st.rerun()
        else:
            st.error("Nom ou code incorrect.")
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    menu_options = ["📝 Saisie du Bilan"]
    if st.session_state.user == "admin":
        menu_options.append("📊 Liste des Codes")
    
    choix = st.radio("Navigation", menu_options)
    
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if choix == "📝 Saisie du Bilan":
    st.title(f"Bilan de {st.session_state.user}")
    
    # 1. Infos de base
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    # Initialisation de la ligne de données (Ordre exact du Google Sheet)
    data = {
        "Accompagnateur": st.session_state.user,
        "Mois": mois,
        "Annee": annee,
        "Agence": agence,
        "Derniere_MAJ": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    tabs = st.tabs([
        "1. Matière Première", "2. Triangulaire", "3. Appels", "4. CAM", 
        "5. Algérie Télécom", "6. Recyclage", "7. Tricycle", 
        "8. Auto-Entrepreneur", "9. NESDA", "10. Rappels"
    ])

    def render_rubrique(prefix, title):
        st.subheader(title)
        col1, col2, col3, col4, col5 = st.columns(5)
        data[f"{prefix}_Dep"] = col1.number_input("Déposés", key=f"{prefix}1", value=0)
        data[f"{prefix}_Trt"] = col2.number_input("Traités CEF", key=f"{prefix}2", value=0)
        data[f"{prefix}_Val"] = col3.number_input("Validés CEF", key=f"{prefix}3", value=0)
        data[f"{prefix}_Tms"] = col4.number_input("Transmis Banque", key=f"{prefix}4", value=0)
        data[f"{prefix}_Fin"] = col5.number_input("Financés", key=f"{prefix}5", value=0)
        
        colA, colB, colC, colD = st.columns(4)
        data[f"{prefix}_O10"] = colA.number_input("BC 10%", key=f"{prefix}6", value=0)
        data[f"{prefix}_O90"] = colB.number_input("BC 90%", key=f"{prefix}7", value=0)
        data[f"{prefix}_PVE"] = colC.number_input("PV Existence", key=f"{prefix}8", value=0)
        data[f"{prefix}_PVD"] = colD.number_input("PV Démarrage", key=f"{prefix}9", value=0)
        
        colR1, colR2 = st.columns(2)
        data[f"{prefix}_RNbr"] = colR1.number_input("Nb Reçus Remb.", key=f"{prefix}10", value=0)
        data[f"{prefix}_RMnt"] = colR2.number_input("Montant Remb. (DA)", key=f"{prefix}11", value=0.0)

    with tabs[0]: render_rubrique("MP", "Achat de Matière Première")
    with tabs[1]: render_rubrique("Tri", "Formule Triangulaire")
    with tabs[2]: data["Appels"] = st.number_input("Total Appels Nominatifs", value=0)
    with tabs[3]: data["CAM"] = st.number_input("Citoyens reçus au CAM", value=0)
    with tabs[4]: render_rubrique("AT", "Dispositif Algérie Télécom")
    with tabs[5]: render_rubrique("Rec", "Dispositif Recyclage")
    with tabs[6]: render_rubrique("Tc", "Dispositif Tricycle")
    with tabs[7]: render_rubrique("AE", "Statut Auto-Entrepreneur")
    with tabs[8]: data["NESDA"] = st.number_input("Dossiers via NESDA", value=0)
    with tabs[9]:
        for m in ["27k", "40k", "100k", "400k", "1M"]:
            cl, cv = st.columns(2)
            data[f"Let_{m}"] = cl.number_input(f"Lettres Rappel ({m})", key=f"l{m}", value=0)
            data[f"Vis_{m}"] = cv.number_input(f"Visites Terrain ({m})", key=f"v{m}", value=0)

    st.markdown("---")
    if st.button("💾 ENREGISTRER LE BILAN", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Données enregistrées dans Google Sheets !")
            st.balloons()

# --- GESTION DES CODES (ADMIN UNIQUEMENT) ---
elif choix == "📊 Liste des Codes":
    st.title("📋 Codes d'accès des accompagnateurs")
    codes_data = [{"Accompagnateur": k, "Code d'accès": v} for k, v in USERS_DB.items()]
    st.table(codes_data)
