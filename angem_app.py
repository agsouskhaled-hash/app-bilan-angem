import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import io
import os
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="ANGEM PRO - Cloud", layout="wide", page_icon="🇩🇿")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #f4f4f4; }
    .stButton>button { background-color: #006233; color: white; border-radius: 5px; font-weight: bold;}
    h1, h2, h3 { color: #006233; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS (Sauvegarde permanente) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        # On lit la base de données en temps réel
        return conn.read(ttl=0)
    except:
        return pd.DataFrame()

def save_data(new_entry):
    df_existing = load_db()
    if not df_existing.empty:
        # On évite les doublons (même agent, même mois, même année)
        mask = (df_existing["Accompagnateur"] == new_entry["Accompagnateur"]) & \
               (df_existing["Mois"] == new_entry["Mois"]) & \
               (df_existing["Annee"] == int(new_entry["Annee"]))
        df_existing = df_existing[~mask]
    
    df_final = pd.concat([df_existing, pd.DataFrame([new_entry])], ignore_index=True)
    # On met à jour la Google Sheet
    conn.update(data=df_final)

# --- LISTE DES UTILISATEURS & MOTS DE PASSE ---
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
base_code = 1234
for i, nom in enumerate(LISTE_NOMS):
    USERS[nom] = str(base_code + (i * 4444))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Connexion Réseau ANGEM")
    user = st.selectbox("Utilisateur", list(USERS.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if USERS.get(user) == pwd:
            st.session_state.auth, st.session_state.user = True, user
            st.rerun()
        else: st.error("Mot de passe incorrect")
    st.stop()

# --- MENU ---
with st.sidebar:
    st.write(f"Connecté : **{st.session_state.user}**")
    menu = ["📝 Saisie Mensuelle"]
    if st.session_state.user == "admin":
        menu += ["📊 Stats & Cumuls", "🛠️ Gestion de la Base", "📋 Liste des Accès"]
    choix = st.radio("Navigation", menu)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if choix == "📝 Saisie Mensuelle":
    st.title("Espace Accompagnateur")
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent (Admin)", LISTE_NOMS)
    
    c1, c2, c3 = st.columns(3)
    agence = c1.text_input("Agence", "Alger Ouest")
    mois = c2.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c3.number_input("Année", 2026, step=1)

    df_gs = load_db()
    existing = None
    if not df_gs.empty:
        res = df_gs[(df_gs["Accompagnateur"] == agent) & (df_gs["Mois"] == mois) & (df_gs["Annee"] == int(annee))]
        if not res.empty: existing = res.iloc[-1].to_dict()

    def val(k): return int(float(existing[k])) if existing and k in existing else 0
    def val_f(k): return float(existing[k]) if existing and k in existing else 0.0

    data = {"Agence": agence, "Accompagnateur": agent, "Mois": mois, "Annee": annee, "Last_Update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    tabs = st.tabs(["1. Mat. Première", "2. Triangulaire", "4. Accueil CAM", "8. Auto-Ent.", "10. Rappels"])

    def render_full_section(prefix, title):
        st.subheader(title)
        c1, c2, c3, c4, c5 = st.columns(5)
        data[f"{prefix}_Deposes"] = c1.number_input("Dossiers déposés", value=val(f"{prefix}_Deposes"), key=f"{prefix}1")
        data[f"{prefix}_Traites_CEF"] = c2.number_input("Traités par CEF", value=val(f"{prefix}_Traites_CEF"), key=f"{prefix}2")
        data[f"{prefix}_Valides_CEF"] = c3.number_input("Validés par CEF", value=val(f"{prefix}_Valides_CEF"), key=f"{prefix}3")
        data[f"{prefix}_Transmis_Banque"] = c4.number_input("Transmis Banque/AR", value=val(f"{prefix}_Transmis_Banque"), key=f"{prefix}4")
        data[f"{prefix}_Notif_Bancaire"] = c5.number_input("Notif./Financés", value=val(f"{prefix}_Notif_Bancaire"), key=f"{prefix}5")
        st.markdown("---")
        c6, c7, c8, c9 = st.columns(4)
        data[f"{prefix}_Transmis_AR"] = c6.number_input("Transmis à l'AR", value=val(f"{prefix}_Transmis_AR"), key=f"{prefix}6")
        data[f"{prefix}_Finances"] = c7.number_input("Dossiers financés", value=val(f"{prefix}_Finances"), key=f"{prefix}7")
        data[f"{prefix}_Ordre_10"] = c8.number_input("Ordre 10%", value=val(f"{prefix}_Ordre_10"), key=f"{prefix}8")
        data[f"{prefix}_Ordre_90"] = c9.number_input("Ordre 90%", value=val(f"{prefix}_Ordre_90"), key=f"{prefix}9")
        st.markdown("---")
        c10, c11, c12, c13 = st.columns(4)
        data[f"{prefix}_PV_Exist"] = c10.number_input("PV Existence", value=val(f"{prefix}_PV_Exist"), key=f"{prefix}10")
        data[f"{prefix}_PV_Demarr"] = c11.number_input("PV Démarrage", value=val(f"{prefix}_PV_Demarr"), key=f"{prefix}11")
        data[f"{prefix}_Remb_Recus"] = c12.number_input("Reçus Remb.", value=val(f"{prefix}_Remb_Recus"), key=f"{prefix}12")
        data[f"{prefix}_Remb_Montant"] = c13.number_input("Montant Remb. (DA)", value=val_f(f"{prefix}_Remb_Montant"), key=f"{prefix}13")

    with tabs[0]: render_full_section("MP", "1. Achat de matière premières")
    with tabs[1]: render_full_section("Tri", "2. Formule Triangulaire")
    with tabs[3]: render_full_section("AE", "8. Auto-Entrepreneur")

    st.markdown("---")
    if st.button("💾 ENREGISTRER DANS LE CLOUD", type="primary", use_container_width=True):
        save_data(data)
        st.success("✅ Données sauvegardées sur Google Sheets !")
        st.balloons()

# --- ESPACE ADMIN ---
elif choix == "📊 Stats & Cumuls":
    st.title("📊 Statistiques")
    df = load_db()
    if df.empty: st.warning("Base vide")
    else:
        df_stats = df.groupby("Accompagnateur").sum(numeric_only=True).drop(columns=["Annee"])
        st.dataframe(df_stats, use_container_width=True)

elif choix == "📋 Liste des Accès":
    st.title("📋 Codes d'accès")
    data_acces = [{"Nom": k, "Code": v} for k, v in USERS.items()]
    st.table(pd.DataFrame(data_acces))
