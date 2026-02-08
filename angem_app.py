import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="ANGEM PRO - Bilans Individuels", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE GOOGLE SHEETS ---
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
        
        # --- LOGIQUE DE SÉPARATION PAR ONGLET ---
        try:
            worksheet = sh.worksheet(user_name)
        except gspread.exceptions.WorksheetNotFound:
            # Création automatique de l'onglet si inexistant
            worksheet = sh.add_worksheet(title=user_name, rows="1000", cols="100")
            headers = list(data_dict.keys())
            worksheet.append_row(headers)
        
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement : {e}")
        return False

def load_data_from_sheet(sheet_name):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except:
        return pd.DataFrame()

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
    st.title("🔐 Système de Bilans ANGEM PRO")
    u_select = st.selectbox("Sélectionnez votre nom", [""] + list(USERS_DB.keys()))
    p_input = st.text_input("Code d'accès", type="password")
    if st.button("Connexion"):
        if u_select in USERS_DB and USERS_DB[u_select] == p_input:
            st.session_state.auth, st.session_state.user = True, u_select
            st.rerun()
        else:
            st.error("Code incorrect.")
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    st.link_button("📂 Ouvrir le Bilan Excel", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    
    menu = ["📝 Saisie du Bilan"]
    if st.session_state.user == "admin":
        menu += ["📊 Suivi des Saisies", "🔑 Liste des Codes"]
    
    choix = st.radio("Navigation", menu)
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if choix == "📝 Saisie du Bilan":
    st.title(f"Bilan Mensuel : {st.session_state.user}")
    
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois du Bilan", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    data = {
        "Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Agence": agence,
        "Date_Saisie": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    tabs = st.tabs([
        "1. Matière Première", "2. Formule Triangulaire", "3. Appels", "4. CAM", 
        "5. Algérie Télécom", "6. Recyclage", "7. Tricycle", 
        "8. Auto-Entrepreneur", "9. NESDA", "10. Rappels"
    ])

    def render_rubrique(prefix, title, d):
        st.subheader(title)
        col1, col2, col3, col4, col5 = st.columns(5)
        d[f"{prefix}_Deposes"] = col1.number_input("Déposés", key=f"{prefix}d", value=0)
        d[f"{prefix}_Traites_CEF"] = col2.number_input("Traités CEF", key=f"{prefix}t", value=0)
        d[f"{prefix}_Valides_CEF"] = col3.number_input("Validés CEF", key=f"{prefix}v", value=0)
        d[f"{prefix}_Transmis_Bq"] = col4.number_input("Transmis Banque", key=f"{prefix}m", value=0)
        d[f"{prefix}_Finances"] = col5.number_input("Financés", key=f"{prefix}f", value=0)
        
        colA, colB, colC, colD = st.columns(4)
        d[f"{prefix}_BC_10%"] = colA.number_input("BC 10%", key=f"{prefix}o1", value=0)
        d[f"{prefix}_BC_90%"] = colB.number_input("BC 90%", key=f"{prefix}o9", value=0)
        d[f"{prefix}_PV_Existence"] = colC.number_input("PV Existence", key=f"{prefix}pe", value=0)
        d[f"{prefix}_PV_Demarrage"] = colD.number_input("PV Démarrage", key=f"{prefix}pd", value=0)
        
        st.write("**💰 Remboursements**")
        colR1, colR2 = st.columns(2)
        d[f"{prefix}_Nb_Recus"] = colR1.number_input("Nb Reçus", key=f"{prefix}rn", value=0)
        d[f"{prefix}_Montant_DA"] = colR2.number_input("Montant (DA)", key=f"{prefix}rm", value=0.0)

    with tabs[0]: render_rubrique("MP", "1. Achat de Matière Première", data)
    with tabs[1]: render_rubrique("Tri", "2. Formule Triangulaire", data)
    with tabs[2]: data["Appels_Total"] = st.number_input("3. Liste nominative des appels", value=0)
    with tabs[3]: data["CAM_Total"] = st.number_input("4. Citoyens reçus au CAM", value=0)
    with tabs[4]: render_rubrique("AT", "5. Dispositif Algérie Télécom", data)
    with tabs[5]: render_rubrique("Rec", "6. Dispositif Recyclage", data)
    with tabs[6]: render_rubrique("Tc", "7. Dispositif Tricycle", data)
    with tabs[7]: render_rubrique("AE", "8. Statut Auto-Entrepreneur", data)
    with tabs[8]: data["NESDA_Total"] = st.number_input("9. Dossiers NESDA", value=0)
    with tabs[9]:
        st.subheader("10. Lettres de Rappel & Visites")
        for m in ["27k", "40k", "100k", "400k", "1M"]:
            cl, cv = st.columns(2)
            data[f"Let_Rappel_{m}"] = cl.number_input(f"Lettres ({m})", key=f"l{m}", value=0)
            data[f"Vis_Terrain_{m}"] = cv.number_input(f"Visites ({m})", key=f"v{m}", value=0)

    st.markdown("---")
    if st.button("💾 ENREGISTRER MON BILAN", type="primary", use_container_width=True):
        if save_to_gsheet(data, st.session_state.user):
            st.success(f"✅ Bilan enregistré avec succès dans l'onglet '{st.session_state.user}' !")
            st.balloons()

# --- GESTION ADMIN ---
elif choix == "📊 Suivi des Saisies":
    st.title("📊 État de remplissage des bilans")
    m_check = st.selectbox("Mois à vérifier", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    a_check = st.number_input("Année à vérifier", 2025, 2030, 2026)
    
    # Pour l'admin, on vérifie l'onglet de chaque personne
    reçus, en_attente = [], []
    for nom in LISTE_NOMS:
        df_temp = load_data_from_sheet(nom)
        if not df_temp.empty and not df_temp[(df_temp['Mois'] == m_check) & (df_temp['Annee'] == a_check)].empty:
            reçus.append(nom)
        else:
            en_attente.append(nom)
    
    c1, c2 = st.columns(2)
    c1.success(f"✅ Reçus ({len(reçus)})")
    for r in reçus: c1.write(f"- {r}")
    c2.error(f"❌ En attente ({len(en_attente)})")
    for e in en_attente: c2.write(f"- {e}")

elif choix == "🔑 Liste des Codes":
    st.title("🔑 Codes d'accès")
    st.table([{"Accompagnateur": k, "Code": v} for k, v in USERS_DB.items()])
