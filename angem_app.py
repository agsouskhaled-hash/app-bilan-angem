import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

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
    except:
        return pd.DataFrame()

def save_data_to_gs(new_entry):
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.get_worksheet(0)
        
        # On convertit les valeurs en liste simple pour l'insertion
        valeurs_ligne = list(new_entry.values())
        
        # Ajout direct (append_row est plus stable pour les gros bilans)
        worksheet.append_row(valeurs_ligne)
        return True
    except Exception as e:
        st.error(f"Erreur de communication avec Google : {e}")
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

# --- MENU LATÉRAL ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    menu = ["📝 Saisie Mensuelle", "📊 Suivi Admin", "📋 Codes d'accès"]
    if st.session_state.user != "admin": menu = ["📝 Saisie Mensuelle"]
    choix = st.radio("Navigation", menu)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if choix == "📝 Saisie Mensuelle":
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent", LISTE_NOMS)
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    # Initialisation du dictionnaire de données
    data = {"Accompagnateur": agent, "Mois": mois, "Annee": annee, "Agence": agence, "Dernière MAJ": datetime.now().strftime("%d/%m/%Y %H:%M")}

    # --- TABS POUR LES 10 RUBRIQUES ---
    tabs = st.tabs(["1. MP", "2. Tri", "3. Appels", "4. CAM", "5. AT", "6. Rec", "7. Tc", "8. AE", "9. NESDA", "10. Rappels"])

    def create_rubrique(prefix, title):
        st.subheader(title)
        col1, col2, col3, col4, col5 = st.columns(5)
        data[f"{prefix}_Dep"] = col1.number_input("Déposés", key=f"{prefix}d", value=0)
        data[f"{prefix}_Trt"] = col2.number_input("Traités CEF", key=f"{prefix}t", value=0)
        data[f"{prefix}_Val"] = col3.number_input("Validés CEF", key=f"{prefix}v", value=0)
        data[f"{prefix}_Tms"] = col4.number_input("Transmis Bq", key=f"{prefix}m", value=0)
        data[f"{prefix}_Fin"] = col5.number_input("Financés", key=f"{prefix}f", value=0)
        
        colA, colB, colC, colD = st.columns(4)
        data[f"{prefix}_O10"] = colA.number_input("Ordre 10%", key=f"{prefix}o1", value=0)
        data[f"{prefix}_O90"] = colB.number_input("Ordre 90%", key=f"{prefix}o9", value=0)
        data[f"{prefix}_PVE"] = colC.number_input("PV Existence", key=f"{prefix}pe", value=0)
        data[f"{prefix}_PVD"] = colD.number_input("PV Démarrage", key=f"{prefix}pd", value=0)
        
        st.markdown("**Remboursements**")
        colR1, colR2 = st.columns(2)
        data[f"{prefix}_RNbr"] = colR1.number_input("Nb Reçus", key=f"{prefix}rn", value=0)
        data[f"{prefix}_RMnt"] = colR2.number_input("Montant (DA)", key=f"{prefix}rm", value=0.0)

    with tabs[0]: create_rubrique("MP", "1. Matière Première")
    with tabs[1]: create_rubrique("Tri", "2. Formule Triangulaire")
    with tabs[2]:
        st.subheader("3. Appels Téléphoniques")
        data["Appels_Total"] = st.number_input("Total Appels", value=0)
    with tabs[3]:
        st.subheader("4. Accueil CAM")
        data["CAM_Recus"] = st.number_input("Total Citoyens reçus", value=0)
    with tabs[4]: create_rubrique("AT", "5. Algérie Télécom")
    with tabs[5]: create_rubrique("Rec", "6. Recyclage")
    with tabs[6]: create_rubrique("Tc", "7. Tricycle")
    with tabs[7]: create_rubrique("AE", "8. Auto-Entrepreneur")
    with tabs[8]:
        st.subheader("9. NESDA")
        data["NESDA_Doss"] = st.number_input("Nombre de dossiers", value=0)
    with tabs[9]:
        st.subheader("10. Rappels & Visites")
        for m in ["27k", "40k", "100k", "400k", "1M"]:
            cl, cv = st.columns(2)
            data[f"Let_{m}"] = cl.number_input(f"Lettres ({m})", key=f"l{m}", value=0)
            data[f"Vis_{m}"] = cv.number_input(f"Visites ({m})", key=f"v{m}", value=0)

    st.markdown("---")
    if st.button("💾 ENREGISTRER TOUT LE BILAN", type="primary", use_container_width=True):
        if save_data_to_gs(data):
            st.success("✅ Données transmises avec succès à Google Sheets !")
            st.balloons()

elif choix == "📊 Suivi Admin":
    st.title("📊 Tableau de Bord")
    df = load_data_from_gs()
    if not df.empty:
        st.dataframe(df)
    else: st.info("Aucune donnée disponible.")

elif choix == "📋 Liste des Accès":
    st.table([{"Nom": k, "Code": v} for k, v in USERS.items()])
