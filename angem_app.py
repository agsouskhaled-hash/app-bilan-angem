import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

# --- STYLE VISUEL ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #006233; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    .stHeader { color: #006233; border-bottom: 2px solid #006233; padding-bottom: 10px; }
    h1, h2, h3 { color: #006233; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; color: #006233; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS VIA SECRETS ---
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
        else:
            df_final = new_row
        worksheet.clear()
        set_with_dataframe(worksheet, df_final)
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- LISTE DES ACCOMPAGNATEURS ET MOTS DE PASSE ---
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
    USERS[nom] = str(1234 + (i * 111)) # Codes uniques simplifiés

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Connexion ANGEM PRO")
    u = st.selectbox("Sélectionnez votre nom", [""] + list(USERS.keys()))
    p = st.text_input("Code d'accès", type="password")
    if st.button("Se connecter"):
        if u in USERS and USERS[u] == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    if st.session_state.user == "admin":
        st.link_button("📂 Ouvrir Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    menu = ["📝 Saisie Mensuelle", "📊 Suivi & Bilan Admin", "📋 Codes d'accès"]
    if st.session_state.user != "admin": menu = ["📝 Saisie Mensuelle"]
    choix = st.radio("Navigation", menu)
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- LOGIQUE DE SAISIE ---
if choix == "📝 Saisie Mensuelle":
    st.title("📝 Formulaire de Bilan Mensuel")
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent (Admin)", LISTE_NOMS)
    
    col_m, col_a, col_ag = st.columns(3)
    mois = col_m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = col_a.number_input("Année", 2025, 2030, 2026)
    agence = col_ag.text_input("Agence", "Alger Ouest")

    # Charger données existantes pour pré-remplir
    df_db = load_data_from_gs()
    existing = None
    if not df_db.empty:
        res = df_db[(df_db["Accompagnateur"] == agent) & (df_db["Mois"] == mois) & (df_db["Annee"] == str(annee))]
        if not res.empty: existing = res.iloc[-1].to_dict()

    def gv(k, default=0): 
        try: return int(float(existing[k])) if existing and k in existing else default
        except: return default

    data = {"Accompagnateur": agent, "Mois": mois, "Annee": annee, "Agence": agence, "Date": datetime.now().strftime("%d/%m/%Y")}

    # --- LES 10 ONGLETS ---
    tabs = st.tabs(["1-2. MP & Tri", "3. Appels", "4. CAM", "5-7. Spéciaux", "8. Auto-Ent.", "9. NESDA", "10. Rappels"])

    def render_rubrique(prefix, titre):
        st.subheader(titre)
        c1, c2, c3, c4, c5 = st.columns(5)
        data[f"{prefix}_Dep"] = c1.number_input("Déposés", value=gv(f"{prefix}_Dep"), key=f"{prefix}a")
        data[f"{prefix}_Trt"] = c2.number_input("Traités CEF", value=gv(f"{prefix}_Trt"), key=f"{prefix}b")
        data[f"{prefix}_Val"] = c3.number_input("Validés CEF", value=gv(f"{prefix}_Val"), key=f"{prefix}c")
        data[f"{prefix}_Tms"] = c4.number_input("Transmis Bq", value=gv(f"{prefix}_Tms"), key=f"{prefix}d")
        data[f"{prefix}_Fin"] = c5.number_input("Financés", value=gv(f"{prefix}_Fin"), key=f"{prefix}e")
        
        c6, c7, c8, c9 = st.columns(4)
        data[f"{prefix}_O10"] = c6.number_input("Ordre 10%", value=gv(f"{prefix}_O10"), key=f"{prefix}f")
        data[f"{prefix}_O90"] = c7.number_input("Ordre 90%", value=gv(f"{prefix}_O90"), key=f"{prefix}g")
        data[f"{prefix}_PVE"] = c8.number_input("PV Exist", value=gv(f"{prefix}_PVE"), key=f"{prefix}h")
        data[f"{prefix}_PVD"] = c9.number_input("PV Démarr", value=gv(f"{prefix}_PVD"), key=f"{prefix}i")
        
        c10, c11 = st.columns(2)
        data[f"{prefix}_RNbr"] = c10.number_input("Nb Reçus Remb.", value=gv(f"{prefix}_RNbr"), key=f"{prefix}j")
        data[f"{prefix}_RMnt"] = c11.number_input("Montant Remb. (DA)", value=float(gv(f"{prefix}_RMnt")), key=f"{prefix}k")
        st.markdown("---")

    with tabs[0]:
        render_rubrique("MP", "1. Achat Matière Première")
        render_rubrique("Tri", "2. Formule Triangulaire")
    
    with tabs[1]:
        st.subheader("3. Appels Téléphoniques")
        data["Appels_Effectues"] = st.number_input("Nombre total d'appels", value=gv("Appels_Effectues"))
        
    with tabs[2]:
        st.subheader("4. Accueil CAM")
        data["CAM_Recus"] = st.number_input("Nombre de citoyens reçus", value=gv("CAM_Recus"))

    with tabs[3]:
        render_rubrique("AT", "5. Algérie Télécom")
        render_rubrique("Rec", "6. Recyclage")
        render_rubrique("Tc", "7. Tricycle")

    with tabs[4]:
        render_rubrique("AE", "8. Auto-Entrepreneur")

    with tabs[5]:
        st.subheader("9. NESDA")
        data["NESDA_Dossiers"] = st.number_input("Dossiers NESDA traités", value=gv("NESDA_Dossiers"))

    with tabs[6]:
        st.subheader("10. Lettres de Rappel & Visites")
        for m in ["27k", "40k", "100k", "400k", "1M"]:
            c_l, c_v = st.columns(2)
            data[f"R_Let_{m}"] = c_l.number_input(f"Lettres Rappel ({m})", value=gv(f"R_Let_{m}"), key=f"l{m}")
            data[f"R_Vis_{m}"] = c_v.number_input(f"Visites Terrain ({m})", value=gv(f"R_Vis_{m}"), key=f"v{m}")

    if st.button("💾 ENREGISTRER LE BILAN COMPLET", type="primary"):
        if save_data_to_gs(data):
            st.success("✅ Données sauvegardées sur Google Sheets !")
            st.balloons()

# --- ADMINISTRATION ---
elif choix == "📊 Suivi & Bilan Admin":
    st.title("📊 Tableau de Bord Admin")
    df = load_data_from_gs()
    if df.empty:
        st.warning("Aucune donnée dans la base.")
    else:
        f_m = st.selectbox("Filtrer par Mois", ["Tous"] + ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
        df_show = df if f_m == "Tous" else df[df["Mois"] == f_m]
        
        st.subheader("🚀 État des saisies")
        reçus = df_show["Accompagnateur"].unique()
        manquants = [a for a in LISTE_NOMS if a not in reçus]
        
        c1, c2 = st.columns(2)
        c1.success(f"✅ Reçus : {len(reçus)}")
        c2.error(f"❌ En attente : {len(manquants)}")
        if manquants: st.write(f"Liste : {', '.join(manquants)}")
        
        st.markdown("---")
        st.subheader("📈 Cumul Général")
        st.dataframe(df_show, use_container_width=True)

elif choix == "📋 Codes d'accès":
    st.title("📋 Liste des Accès")
    st.table([{"Nom": k, "Code": v} for k, v in USERS.items()])
