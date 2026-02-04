import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

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
        # On envoie les valeurs dans l'ordre du dictionnaire
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement : {e}")
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
    st.link_button("📂 Ouvrir le Bilan Excel", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    
    menu = ["📝 Saisie du Bilan"]
    if st.session_state.user == "admin":
        menu += ["📊 Suivi des Saisies", "🔑 Liste des Codes"]
    
    choix = st.radio("Menu", menu)
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if choix == "📝 Saisie du Bilan":
    st.title(f"Saisie Mensuelle - {st.session_state.user}")
    
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    # Dictionnaire de données initialisé
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

    def render_rubrique(prefix, title, data_dict):
        st.subheader(title)
        col1, col2, col3, col4, col5 = st.columns(5)
        data_dict[f"{prefix}_Dep"] = col1.number_input("Déposés", key=f"{prefix}_d", value=0)
        data_dict[f"{prefix}_Trt"] = col2.number_input("Traités CEF", key=f"{prefix}_t", value=0)
        data_dict[f"{prefix}_Val"] = col3.number_input("Validés CEF", key=f"{prefix}_v", value=0)
        data_dict[f"{prefix}_Tms"] = col4.number_input("Transmis Banque", key=f"{prefix}_m", value=0)
        data_dict[f"{prefix}_Fin"] = col5.number_input("Financés", key=f"{prefix}_f", value=0)
        
        colA, colB, colC, colD = st.columns(4)
        data_dict[f"{prefix}_O10"] = colA.number_input("BC 10%", key=f"{prefix}_o1", value=0)
        data_dict[f"{prefix}_O90"] = colB.number_input("BC 90%", key=f"{prefix}_o9", value=0)
        data_dict[f"{prefix}_PVE"] = colC.number_input("PV Existence", key=f"{prefix}_pe", value=0)
        data_dict[f"{prefix}_PVD"] = colD.number_input("PV Démarrage", key=f"{prefix}_pd", value=0)
        
        st.write("**💰 Remboursements**")
        colR1, colR2 = st.columns(2)
        data_dict[f"{prefix}_RNbr"] = colR1.number_input("Nombre de reçus", key=f"{prefix}_rn", value=0)
        data_dict[f"{prefix}_RMnt"] = colR2.number_input("Montant (DA)", key=f"{prefix}_rm", value=0.0)

    with tabs[0]: render_rubrique("MP", "1. Achat de Matière Première", data)
    with tabs[1]: render_rubrique("Tri", "2. Formule Triangulaire", data)
    
    with tabs[2]:
        st.subheader("3. Appels Téléphoniques")
        data["Appels_Total"] = st.number_input("Total Appels Nominatifs", value=0)
        
    with tabs[3]:
        st.subheader("4. Accueil CAM")
        data["CAM_Total"] = st.number_input("Citoyens reçus au CAM", value=0)

    with tabs[4]: render_rubrique("AT", "5. Dispositif Algérie Télécom", data)
    with tabs[5]: render_rubrique("Rec", "6. Dispositif Recyclage", data)
    with tabs[6]: render_rubrique("Tc", "7. Dispositif Tricycle", data)
    with tabs[7]: render_rubrique("AE", "8. Statut Auto-Entrepreneur", data)

    with tabs[8]:
        st.subheader("9. NESDA")
        data["NESDA_Total"] = st.number_input("Dossiers via NESDA", value=0)

    with tabs[9]:
        st.subheader("10. Lettres de Rappel & Visites")
        for m in ["27k", "40k", "100k", "400k", "1M"]:
            cl, cv = st.columns(2)
            data[f"Let_{m}"] = cl.number_input(f"Lettres ({m})", key=f"l_{m}", value=0)
            data[f"Vis_{m}"] = cv.number_input(f"Visites ({m})", key=f"v_{m}", value=0)

    st.markdown("---")
    if st.button("💾 ENREGISTRER LE BILAN COMPLET", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Félicitations ! Vos données sont enregistrées dans Google Sheets.")
            st.balloons()

elif choix == "📊 Suivi des Saisies":
    st.title("📊 État d'avancement des bilans")
    df = load_all_data()
    col_m, col_a = st.columns(2)
    m_filtre = col_m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    a_filtre = col_a.number_input("Année", 2025, 2030, 2026)

    if not df.empty:
        saisies = df[(df['Mois'] == m_filtre) & (df['Annee'] == a_filtre)]['Accompagnateur'].unique()
        c_ok, c_no = st.columns(2)
        with c_ok:
            st.success(f"✅ Reçus ({len(saisies)})")
            for n in saisies: st.write(f"- {n}")
        with c_no:
            en_attente = [n for n in LISTE_NOMS if n not in saisies]
            st.error(f"❌ En attente ({len(en_attente)})")
            for n in en_attente: st.write(f"- {n}")
    else: st.warning("Le fichier Excel est vide.")

elif choix == "🔑 Liste des Codes":
    st.title("🔑 Codes d'accès")
    st.table([{"Nom": k, "Code": v} for k, v in USERS_DB.items()])
