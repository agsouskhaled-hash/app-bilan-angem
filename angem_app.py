import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Bilan Officiel", layout="wide", page_icon="🇩🇿")

# --- CONNEXION ---
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
        st.error(f"Erreur d'écriture : {e}")
        return False

# --- LISTE DES ACCOMPAGNATEURS ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Accès Système ANGEM")
    u = st.selectbox("Utilisateur", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code d'accès", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- FORMULAIRE ---
st.title(f"📊 Bilan Mensuel - {st.session_state.user}")

c1, c2, c3 = st.columns(3)
mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee = c2.number_input("Année", 2025, 2030, 2026)
agence = c3.text_input("Agence", "Alger Ouest")

data = {
    "Date_Saisie": datetime.now().strftime("%d/%m/%Y %H:%M"),
    "Agent": st.session_state.user,
    "Mois": mois,
    "Annee": annee,
    "Agence": agence
}

# --- ONGLETS AVEC NOMS COMPLETS ---
tabs = st.tabs([
    "1. Matière Première", 
    "2. Formule Triangulaire", 
    "3. Appels", 
    "4. Accueil CAM", 
    "5. Algérie Télécom", 
    "6. Recyclage", 
    "7. Tricycle", 
    "8. Auto-Entrepreneur", 
    "9. NESDA", 
    "10. Rappels"
])

def render_form(prefix, title):
    st.subheader(title)
    col1, col2, col3, col4, col5 = st.columns(5)
    data[f"{prefix}_Dep"] = col1.number_input("Dossiers Déposés", key=f"{prefix}1", min_value=0)
    data[f"{prefix}_Trt"] = col2.number_input("Dossiers Traités CEF", key=f"{prefix}2", min_value=0)
    data[f"{prefix}_Val"] = col3.number_input("Dossiers Validés CEF", key=f"{prefix}3", min_value=0)
    data[f"{prefix}_Tms"] = col4.number_input("Dossiers Transmis Banque", key=f"{prefix}4", min_value=0)
    data[f"{prefix}_Fin"] = col5.number_input("Dossiers Financés", key=f"{prefix}5", min_value=0)
    
    colA, colB, colC, colD = st.columns(4)
    data[f"{prefix}_O10"] = colA.number_input("Bons de commande 10%", key=f"{prefix}6", min_value=0)
    data[f"{prefix}_O90"] = colB.number_input("Bons de commande 90%", key=f"{prefix}7", min_value=0)
    data[f"{prefix}_PVE"] = colC.number_input("PV d'existence", key=f"{prefix}8", min_value=0)
    data[f"{prefix}_PVD"] = colD.number_input("PV de démarrage", key=f"{prefix}9", min_value=0)
    
    st.markdown("---")
    st.write("💰 **Remboursements**")
    colR1, colR2 = st.columns(2)
    data[f"{prefix}_RNbr"] = colR1.number_input("Nombre de reçus", key=f"{prefix}10", min_value=0)
    data[f"{prefix}_RMnt"] = colR2.number_input("Montant Remboursé (DA)", key=f"{prefix}11", min_value=0.0)

with tabs[0]: render_form("MP", "1. Achat Matière Première")
with tabs[1]: render_form("Tri", "2. Formule Triangulaire")
with tabs[2]: data["Appels_Total"] = st.number_input("3. Liste nominative des appels", 0)
with tabs[3]: data["CAM_Total"] = st.number_input("4. Nombre de citoyens reçus au CAM", 0)
with tabs[4]: render_form("AT", "5. Dispositif Algérie Télécom")
with tabs[5]: render_form("Rec", "6. Dispositif Recyclage")
with tabs[6]: render_form("Tc", "7. Dispositif Tricycle")
with tabs[7]: render_form("AE", "8. Statut Auto-Entrepreneur")
with tabs[8]: data["NESDA_Total"] = st.number_input("9. Dossiers traités via NESDA", 0)
with tabs[9]:
    st.subheader("10. Lettres de Rappel & Visites de terrain")
    for m in ["27.000", "40.000", "100.000", "400.000", "1.000.000"]:
        cl, cv = st.columns(2)
        data[f"Let_{m}"] = cl.number_input(f"Lettres de rappel ({m} DA)", key=f"l{m}", value=0)
        data[f"Vis_{m}"] = cv.number_input(f"Visites de terrain ({m} DA)", key=f"v{m}", value=0)

st.markdown("---")
if st.button("💾 ENREGISTRER LE BILAN COMPLET", type="primary", use_container_width=True):
    if save_to_gsheet(data):
        st.success("✅ Données transférées vers votre modèle Google Sheets !")
        st.balloons()
