import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import io
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #f4f4f4; }
    .stButton>button { background-color: #006233; color: white; border-radius: 5px; font-weight: bold;}
    h1, h2, h3 { color: #006233; }
    div[data-testid="stMetricValue"] { font-size: 1.1rem; border-left: 5px solid #006233; padding-left: 10px; background: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try: return conn.read(ttl=0)
    except: return pd.DataFrame()

def save_data(new_entry):
    df_existing = load_db()
    if not df_existing.empty:
        mask = (df_existing["Accompagnateur"] == new_entry["Accompagnateur"]) & \
               (df_existing["Mois"] == new_entry["Mois"]) & \
               (df_existing["Annee"] == int(new_entry["Annee"]))
        df_existing = df_existing[~mask]
    df_final = pd.concat([df_existing, pd.DataFrame([new_entry])], ignore_index=True)
    conn.update(data=df_final)

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
        else: st.error("Erreur de mot de passe")
    st.stop()

# --- MENU ---
with st.sidebar:
    st.write(f"Connecté : **{st.session_state.user}**")
    if st.session_state.user == "admin":
        st.link_button("📂 Ouvrir Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    
    menu = ["📝 Ma Saisie Mensuelle"]
    if st.session_state.user == "admin":
        menu = ["📝 Saisie (Mode Admin)", "📊 Suivi & Bilan Général", "📋 Liste des Accès"]
    choix = st.radio("Navigation", menu)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- ESPACE SAISIE COMPLET ---
if "Saisie" in choix:
    st.title("📝 Bilan Mensuel Approfondi")
    agent = st.session_state.user if st.session_state.user != "admin" else st.selectbox("Agent", LISTE_NOMS)
    
    c1, c2, c3 = st.columns(3)
    mois = c1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
    annee = c2.number_input("Année", 2025, 2030, 2026)
    agence = c3.text_input("Agence", "Alger Ouest")

    df_gs = load_db()
    existing = None
    if not df_gs.empty:
        res = df_gs[(df_gs["Accompagnateur"]==agent) & (df_gs["Mois"]==mois) & (df_gs["Annee"]==int(annee))]
        if not res.empty: existing = res.iloc[-1].to_dict()

    def v(k): return int(float(existing[k])) if existing and k in existing else 0
    def vf(k): return float(existing[k]) if existing and k in existing else 0.0

    data = {"Accompagnateur": agent, "Mois": mois, "Annee": annee, "Agence": agence, "Last_Update": datetime.now().strftime("%d/%m/%Y %H:%M")}
    
    tabs = st.tabs(["1-2. MP & Tri", "3. Appels", "4. CAM", "5-7. Dispositifs Spéciaux", "8. Auto-Ent.", "9. NESDA", "10. Rappels"])

    with tabs[0]: # MP & TRIANGULAIRE
        def render_full(prefix, titre):
            st.subheader(titre)
            col1, col2, col3, col4, col5 = st.columns(5)
            data[f"{prefix}_Dep"] = col1.number_input(f"{titre} - Déposés", value=v(f"{prefix}_Dep"), key=f"{prefix}1")
            data[f"{prefix}_Trt"] = col2.number_input("Traités CEF", value=v(f"{prefix}_Trt"), key=f"{prefix}2")
            data[f"{prefix}_Val"] = col3.number_input("Validés CEF", value=v(f"{prefix}_Val"), key=f"{prefix}3")
            data[f"{prefix}_Tms"] = col4.number_input("Transmis Bq", value=v(f"{prefix}_Tms"), key=f"{prefix}4")
            data[f"{prefix}_Fin"] = col5.number_input("Financés", value=v(f"{prefix}_Fin"), key=f"{prefix}5")
            st.markdown("---")
            colA, colB, colC, colD = st.columns(4)
            data[f"{prefix}_O10"] = colA.number_input("Ordre 10%", value=v(f"{prefix}_O10"), key=f"{prefix}6")
            data[f"{prefix}_O90"] = colB.number_input("Ordre 90%", value=v(f"{prefix}_O90"), key=f"{prefix}7")
            data[f"{prefix}_PVE"] = colC.number_input("PV Exist", value=v(f"{prefix}_PVE"), key=f"{prefix}8")
            data[f"{prefix}_PVD"] = colD.number_input("PV Démarr", value=v(f"{prefix}_PVD"), key=f"{prefix}9")

        render_full("MP", "1. Matière Première")
        render_full("Tri", "2. Triangulaire")

    with tabs[1]: # APPELS
        st.subheader("3. Liste Nominative Appels")
        df_app = pd.DataFrame([{"N°": i+1, "Nom": "", "Prénom": "", "Activité": "", "Tél": ""} for i in range(10)])
        st.data_editor(df_app, num_rows="dynamic", use_container_width=True, key="appels_ed")

    with tabs[2]: # CAM
        st.subheader("4. Accueil CAM")
        data["CAM_Total"] = st.number_input("Citoyens reçus", value=v("CAM_Total"))

    with tabs[3]: # 5, 6, 7
        render_full("AT", "5. Algérie Télécom")
        render_full("Rec", "6. Recyclage")
        render_full("Tc", "7. Tricycle")

    with tabs[4]: render_full("AE", "8. Auto-Entrepreneur")

    with tabs[5]: # NESDA
        st.subheader("9. Liste NESDA")
        df_nes = pd.DataFrame([{"N°": i+1, "Nom": "", "Activité": ""} for i in range(5)])
        st.data_editor(df_nes, num_rows="dynamic", use_container_width=True, key="nesda_ed")

    with tabs[6]: # RAPPELS
        st.subheader("10. Lettres de rappel")
        for m in ["27000", "40000", "100000", "400000", "1000000"]:
            ca, cb = st.columns(2)
            data[f"R_{m}"] = ca.number_input(f"L/R {m} DA", value=v(f"R_{m}"), key=f"r{m}")
            data[f"S_{m}"] = cb.number_input(f"Sortie {m} DA", value=v(f"S_{m}"), key=f"s{m}")

    st.markdown("---")
    if st.button("💾 ENREGISTRER TOUT DANS LE CLOUD", type="primary", use_container_width=True):
        save_data(data)
        st.success("✅ Données sauvegardées sur Google Sheets !")
        st.balloons()

# --- ESPACE ADMIN : SUIVI & BILAN ---
elif choix == "📊 Suivi & Bilan Général":
    st.title("📊 Contrôle Administrateur")
    df = load_db()
    if df.empty: st.info("Aucune donnée.")
    else:
        f1, f2 = st.columns(2); m_f = f1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]); a_f = f2.number_input("Année", 2025, 2030, 2026)
        df_m = df[(df["Mois"]==m_f) & (df["Annee"]==a_f)]
        
        st.subheader("🚀 État d'avancement")
        fait = df_m["Accompagnateur"].unique()
        pas_fait = [a for a in LISTE_NOMS if a not in fait]
        c_a, c_b = st.columns(2)
        c_a.success(f"✅ Reçus ({len(fait)}) : " + ", ".join(fait))
        c_b.error(f"❌ En attente ({len(pas_fait)}) : " + ", ".join(pas_fait))
        
        st.markdown("---")
        st.subheader(f"🌍 Cumul Réseau {m_f}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total MP Déposés", int(df_m["MP_Dep"].sum()) if "MP_Dep" in df_m else 0)
        m2.metric("Total Tri Déposés", int(df_m["Tri_Dep"].sum()) if "Tri_Dep" in df_m else 0)
        m3.metric("Total AE Déposés", int(df_m["AE_Dep"].sum()) if "AE_Dep" in df_m else 0)
        st.dataframe(df_m, use_container_width=True)

elif choix == "📋 Liste des Accès":
    st.title("📋 Codes d'accès")
    st.table([{"Nom": k, "Code": v} for k, v in USERS.items()])
