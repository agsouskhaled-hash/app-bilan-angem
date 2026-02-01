import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Suivi Global", layout="wide", page_icon="🇩🇿")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        return conn.read(ttl=0)
    except:
        return pd.DataFrame()

def save_data(new_entry):
    df_existing = load_db()
    if not df_existing.empty:
        mask = (df_existing["Accompagnateur"] == new_entry["Accompagnateur"]) & \
               (df_existing["Mois"] == new_entry["Mois"]) & \
               (df_existing["Annee"] == int(new_entry["Annee"]))
        df_existing = df_existing[~mask]
    df_final = pd.concat([df_existing, pd.DataFrame([new_entry])], ignore_index=True)
    conn.update(data=df_final)

# --- LISTE OFFICIELLE ---
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
    user = st.selectbox("Utilisateur", list(USERS.keys()))
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if USERS.get(user) == pwd:
            st.session_state.auth, st.session_state.user = True, user
            st.rerun()
        else: st.error("Mot de passe incorrect")
    st.stop()

# --- MENU LATÉRAL ---
with st.sidebar:
    st.write(f"Connecté : **{st.session_state.user}**")
    if st.session_state.user == "admin":
        st.markdown("---")
        st.link_button("📂 Ouvrir Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit?usp=sharing")
        st.markdown("---")
    
    menu = ["📝 Ma Saisie"]
    if st.session_state.user == "admin":
        menu = ["📝 Saisie (Admin)", "📊 Suivi & Bilan Général", "📋 Liste des Accès"]
    
    choix = st.radio("Navigation", menu)
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE ---
if "Saisie" in choix:
    st.title("📝 Formulaire de Bilan Mensuel")
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Sélectionner l'agent", LISTE_NOMS)
    
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    df_gs = load_db()
    existing = None
    if not df_gs.empty:
        res = df_gs[(df_gs["Accompagnateur"] == agent) & (df_gs["Mois"] == mois) & (df_gs["Annee"] == int(annee))]
        if not res.empty: existing = res.iloc[-1].to_dict()

    def val(k): return int(float(existing[k])) if existing and k in existing else 0

    data = {"Accompagnateur": agent, "Mois": mois, "Annee": annee, "Agence": agence, "Last_Update": datetime.now().strftime("%d/%m/%Y %H:%M")}
    
    tabs = st.tabs(["Matière Première", "Triangulaire"])
    with tabs[0]:
        st.subheader("1. Achat de Matière Première")
        colA, colB = st.columns(2)
        data["MP_Deposes"] = colA.number_input("Dossiers Déposés", value=val("MP_Deposes"), key="mp1")
        data["MP_Finances"] = colB.number_input("Dossiers Financés", value=val("MP_Finances"), key="mp2")
    with tabs[1]:
        st.subheader("2. Formule Triangulaire")
        colA, colB = st.columns(2)
        data["Tri_Deposes"] = colA.number_input("Déposés (Tri)", value=val("Tri_Deposes"), key="tr1")
        data["Tri_Finances"] = colB.number_input("Financés (Tri)", value=val("Tri_Finances"), key="tr2")

    if st.button("💾 ENREGISTRER LE BILAN", type="primary", use_container_width=True):
        save_data(data)
        st.success("✅ Enregistré avec succès dans le Cloud !")

# --- ESPACE ADMIN : SUIVI & BILAN GÉNÉRAL ---
elif choix == "📊 Suivi & Bilan Général":
    st.title("📊 Tableau de Bord Administrateur")
    df = load_db()
    
    if df.empty:
        st.info("Aucune donnée disponible pour le moment.")
    else:
        # 1. FILTRE PAR MOIS/ANNÉE
        st.subheader("Filtre de recherche")
        f1, f2 = st.columns(2)
        m_filtre = f1.selectbox("Mois à surveiller", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
        a_filtre = f2.number_input("Année", 2025, 2030, 2026, key="filtre_annee")

        # Données du mois sélectionné
        df_mois = df[(df["Mois"] == m_filtre) & (df["Annee"] == a_filtre)]
        agents_ayant_saisi = df_mois["Accompagnateur"].unique()

        # 2. SUIVI DES PRÉSENCES (QUI A FAIT / QUI N'A PAS FAIT)
        st.subheader(f"📈 État des saisies pour {m_filtre} {a_filtre}")
        c_fait, c_pas_fait = st.columns(2)
        
        with c_fait:
            st.success(f"✅ Ont envoyé leur bilan ({len(agents_ayant_saisi)})")
            st.write(", ".join(agents_ayant_saisi) if len(agents_ayant_saisi)>0 else "Aucun")

        with c_pas_fait:
            pas_fait = [a for a in LISTE_NOMS if a not in agents_ayant_saisi]
            st.error(f"❌ N'ont pas encore saisi ({len(pas_fait)})")
            st.write(", ".join(pas_fait))

        # 3. BILAN GÉNÉRAL (CUMUL DU RÉSEAU)
        st.markdown("---")
        st.subheader(f"🌍 Bilan Général du Réseau ({m_filtre} {a_filtre})")
        
        if not df_mois.empty:
            total_mp_dep = df_mois["MP_Deposes"].sum()
            total_mp_fin = df_mois["MP_Finances"].sum()
            total_tri_dep = df_mois["Tri_Deposes"].sum()
            total_tri_fin = df_mois["Tri_Finances"].sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total MP Déposés", int(total_mp_dep))
            m2.metric("Total MP Financés", int(total_mp_fin))
            m3.metric("Total Tri Déposés", int(total_tri_dep))
            m4.metric("Total Tri Financés", int(total_tri_fin))
            
            st.write("### Détail par accompagnateur")
            st.dataframe(df_mois[["Accompagnateur", "MP_Deposes", "MP_Finances", "Tri_Deposes", "Tri_Finances", "Last_Update"]], use_container_width=True)
        else:
            st.warning("Aucun chiffre cumulé pour ce mois.")

elif choix == "📋 Liste des Accès":
    st.title("📋 Codes d'accès confidentiels")
    st.table([{"Nom": k, "Code": v} for k, v in USERS.items()])
