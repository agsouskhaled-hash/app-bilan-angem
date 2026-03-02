import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Intra-Service ANGEM v4.1", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

# --- STYLE CSS (Design Moderne) ---
st.markdown("""
<style>
    .stMetric {background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #1f77b4; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .stTabs [aria-selected="true"] {background-color: #f0f2f6; border-bottom: 4px solid #1f77b4; font-weight: bold;}
    .login-box {max-width: 400px; margin: auto; padding: 30px; background-color: #ffffff; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# --- CONNEXION BASE DE DONNÉES SUPABASE ---
Base = declarative_base()
engine = create_engine("postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require", echo=False)
Session = sessionmaker(bind=engine)

# Table des Dossiers
class Dossier(Base):
    __tablename__ = 'dossiers'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, index=True)
    nom = Column(String)
    prenom = Column(String)
    genre = Column(String)
    date_naissance = Column(String)
    adresse = Column(String)
    telephone = Column(String)
    niveau_instruction = Column(String)
    age = Column(String)
    activite = Column(String)
    code_activite = Column(String)
    secteur = Column(String)
    daira = Column(String)
    commune = Column(String)
    gestionnaire = Column(String)
    zone = Column(String)
    montant_pnr = Column(Float, default=0.0)
    apport_personnel = Column(Float, default=0.0)
    credit_bancaire = Column(Float, default=0.0)
    montant_total_credit = Column(Float, default=0.0)
    banque_nom = Column(String)
    agence_bancaire = Column(String)
    numero_compte = Column(String)
    num_ordre_versement = Column(String)
    date_financement = Column(String)
    debut_consommation = Column(String)
    montant_rembourse = Column(Float, default=0.0)
    reste_rembourser = Column(Float, default=0.0)
    nb_echeance_tombee = Column(String)
    etat_dette = Column(String)
    statut_dossier = Column(String, default="Phase dépôt du dossier")

# Table : Sécurité et Mots de passe
class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, unique=True)
    nom = Column(String)
    mot_de_passe = Column(String)
    role = Column(String)

# Création des tables
Base.metadata.create_all(engine)

# Ajout automatique de la colonne statut (si elle n'existe pas)
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS statut_dossier VARCHAR DEFAULT 'Phase dépôt du dossier'"))
        conn.commit()
except:
    pass

def get_session(): return Session()

# INITIALISATION DES COMPTES 
def init_db_users():
    session = get_session()
    if session.query(UtilisateurAuth).count() == 0:
        utilisateurs_base = [
            UtilisateurAuth(identifiant="admin", nom="Administrateur", mot_de_passe="angem", role="admin"),
            UtilisateurAuth(identifiant="mahrez", nom="M. MAHREZ MOHAMED", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="aitouarab", nom="Mme AIT OUARAB AMINA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="felfoul", nom="FELFOUL Samira", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="medjhoum", nom="MEDJHOUM Raouia", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="chemmamdji", nom="CHEMMAMDJI REDA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="djaoudi", nom="DJAOUDI SARA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="berrabah", nom="BERRABAH Douadi", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="boulahlib", nom="BOULAHLIB Redouane", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="nasri", nom="NASRI Riym", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="kadri", nom="KADRI Mohamed amine", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="sekat", nom="SEKAT Manel", mot_de_passe="angem2026", role="agent")
        ]
        session.add_all(utilisateurs_base)
        session.commit()
    session.close()

init_db_users()

LISTE_STATUTS = [
    "Phase dépôt du dossier", 
    "En attente de la commission d'éligibilité", 
    "Accordé / En cours de financement", 
    "En phase d'exploitation", 
    "Contentieux / Retard de remboursement"
]

# --- OUTILS DE NETTOYAGE ---
def clean_header(val):
    if pd.isna(val): return ""
    val = str(val).upper()
    val = ''.join(c for c in unicodedata.normalize('NFD', val) if unicodedata.category(c) != 'Mn')
    return ''.join(filter(str.isalnum, val))

def clean_money(val):
    if pd.isna(val) or val == '': return 0.0
    s = str(val).upper().replace('DA', '').replace(' ', '').replace(',', '.')
    s = re.sub(r'[^\d\.]', '', s)
    try: return float(s)
    except: return 0.0

def clean_identifiant(val):
    if pd.isna(val): return ""
    s = str(val).strip().upper()
    if 'E' in s: 
        try: s = f"{float(s):.0f}"
        except: pass
    if s.endswith('.0'): s = s[:-2]
    s = re.sub(r'\D', '', s)
    return s

MAPPING_CONFIG = {
    'identifiant': ['IDENTIFIANT', 'CNI', 'NCINPC', 'CARTENAT'],
    'nom': ['NOM', 'NOMETPRENOM', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'genre': ['GENRE', 'G', 'HF'],
    'date_naissance': ['DATEDENAISSANCE', 'NELE', 'DN'],
    'adresse': ['ADRESSE', 'RESIDENCE'],
    'telephone': ['TEL', 'PHONE', 'MOBILE'],
    'niveau_instruction': ['NIVEAUDINSTRUCTION', 'INSTRUCTION'],
    'age': ['TRANCHEDAGE', 'AGE'],
    'activite': ['ACTIVITE', 'PROJET', 'AVTIVITE'],
    'code_activite': ['CODEDACTIVITE', 'CODEACTIVITE'],
    'secteur': ['SECTEURDACTIVITE', 'SECTEUR'],
    'daira': ['DAIRA'],
    'commune': ['COMMUNE', 'APC'],
    'gestionnaire': ['GEST', 'ACCOMPAGNATEUR', 'SUIVIPAR'],
    'zone': ['ZONEDACTIVIEURBAINERURALE', 'ZONE'],
    'montant_pnr': ['PNR', 'MONTANTPNR29', 'MTDUPNR', 'MONTANT'],
    'apport_personnel': ['APPERS1', 'APPERS', 'AP', 'APPORTPERSONNEL'],
    'credit_bancaire': ['CBANCAIRE70', 'CBANCAIRE', 'CMT', 'CREDITBANCAIRE'],
    'montant_total_credit': ['TOTALCREDIT', 'COUTDUPROJET'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'agence_bancaire': ['LAGENCEBANCAIREDUPROMOTEUR', 'CODEAGENCE', 'AGENCE'],
    'numero_compte': ['NDUCOMPTE'],
    'num_ordre_versement': ['NUMOV', 'NDORDREDEVIREMENT', 'OV'], 
    'date_financement': ['DATEOV', 'DATEDEVIREMENT', 'DATEVIREMENT'],
    'debut_consommation': ['DEBUTCONSOM', 'DEBUTCONSOMMATION'],
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
    'etat_dette': ['ETAT', 'SITUATION', 'OBS']
}

COLONNES_ARGENT = ['montant_pnr', 'apport_personnel', 'credit_bancaire', 'montant_total_credit', 'montant_rembourse', 'reste_rembourser']

# --- SYSTÈME DE CONNEXION ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_angem.png", width=250)
        except: st.warning("Logo ANGEM introuvable. Placez l'image 'logo_angem.png' dans le dossier.")
        
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.subheader("🔐 Accès Intra-Service")
        username = st.text_input("Identifiant", placeholder="Ex: admin ou nasri")
        password = st.text_input("Mot de passe", type="password")
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            user_input = username.lower().strip()
            session = get_session()
            user_db = session.query(UtilisateurAuth).filter_by(identifiant=user_input).first()
            session.close()
            
            if user_db and user_db.mot_de_passe == password:
                st.session_state.user = {
                    "identifiant": user_db.identifiant, 
                    "nom": user_db.nom, 
                    "role": user_db.role
                }
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
        st.markdown("</div>", unsafe_allow_html=True)

# --- INTERFACE ET NAVIGATION ---
def sidebar_menu():
    try: st.sidebar.image("logo_angem.png", use_container_width=True)
    except: pass
    
    st.sidebar.markdown(f"**👤 Connecté :** {st.session_state.user['nom']}")
    st.sidebar.markdown("---")
    
    options = ["🗂️ Mes Dossiers Promoteurs"]
    
    if st.session_state.user['role'] == "admin":
        options = ["📊 Espace Administrateur", "🗂️ Tous les Dossiers", "📥 Importation des Fichiers"]
        
    choix = st.sidebar.radio("📌 Navigation :", options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state.user = None
        st.rerun()
        
    return choix

# --- PAGE GESTION ---
def page_gestion(vue_admin=False):
    st.title("🗂️ Suivi des Dossiers Promoteurs")
    if not vue_admin:
        st.markdown(f"**Espace Accompagnateur :** Bienvenue {st.session_state.user['nom']}. Voici uniquement vos dossiers assignés.")
    
    try: df = pd.read_sql_query("SELECT * FROM dossiers ORDER BY id DESC", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info("📌 Aucun dossier trouvé.")
        return

    if not vue_admin:
        df = df[df['gestionnaire'] == st.session_state.user['nom']]

    search = st.text_input("🔍 Chercher un dossier :", placeholder="Nom, Identifiant...")
    df_filtered = df.copy()
    if search:
        mask = df_filtered.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_filtered = df_filtered[mask]

    try:
        df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=engine)
        liste_agents = [""] + df_agents['nom'].tolist()
    except:
        liste_agents = [""]

    st.success(f"{len(df_filtered)} dossiers trouvés.")

    edited_df = st.data_editor(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "id": None,
            "identifiant": st.column_config.TextColumn("Identifiant", disabled=True),
            "nom": "Nom Promoteur",
            "statut_dossier": st.column_config.SelectboxColumn("🚦 Statut actuel", options=LISTE_STATUTS, width="large"),
            "gestionnaire": st.column_config.SelectboxColumn("👨‍💼 Accompagnateur", options=liste_agents, disabled=not vue_admin),
            "montant_pnr": st.column_config.NumberColumn("PNR", format="%d DA", disabled=True),
            "reste_rembourser": st.column_config.NumberColumn("Reste à payer", format="%d DA", disabled=True),
        }
    )

    if st.button("💾 Enregistrer les modifications", type="primary"):
        session = get_session()
        try:
            for _, row in edited_df.iterrows():
                dos = session.query(Dossier).get(row['id'])
                if dos:
                    setattr(dos, 'statut_dossier', row['statut_dossier'])
                    if vue_admin: setattr(dos, 'gestionnaire', row['gestionnaire'])
            session.commit()
            st.toast("✅ Modifications sauvegardées avec succès !")
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")
        finally: session.close()

# --- IMPORTATION (LE BUG EST CORRIGÉ ICI) ---
def page_import():
    st.title("📥 Moteur d'Intégration Excel")
    st.info("Importez vos fichiers financiers ou d'identification. Les montants seront mis à jour automatiquement.")
    uploaded_file = st.file_uploader("📂 Glissez le fichier Excel", type=['xlsx', 'xls', 'csv'])
    if uploaded_file and st.button("🚀 Lancer l'Intégration", type="primary"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
            
            agents_db = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_noms = [a.nom for a in agents_db]

            with st.status("Analyse et fusion des données...", expanded=True) as status:
                count_add, count_upd = 0, 0
                for s_name, df_raw in xl.items():
                    df_raw = df_raw.fillna('')
                    header_idx = -1
                    for i in range(min(30, len(df_raw))):
                        row_cl = [clean_header(str(x)) for x in df_raw.iloc[i].values]
                        score = 0
                        if any(k in row_cl for k in ["IDENTIFIANT", "CNI", "REF"]): score += 2
                        if "NOM" in row_cl: score += 1
                        if score >= 2: 
                            header_idx = i
                            break
                    if header_idx == -1: continue
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    df_cols = [clean_header(c) for c in df.columns]
                    col_map = {db_f: df.columns[df_cols.index(clean_header(v))] for db_f, variants in MAPPING_CONFIG.items() for v in variants if clean_header(v) in df_cols}
                    
                    for _, row in df.iterrows():
                        data = {}
                        for db_f, xl_c in col_map.items():
                            valeur_brute = row[xl_c]
                            
                            # LA CORRECTION EST ICI : Si la case Excel est vide, on l'ignore totalement
                            if pd.isna(valeur_brute) or str(valeur_brute).strip() == "":
                                continue 
                                
                            if db_f in COLONNES_ARGENT:
                                data[db_f] = clean_money(valeur_brute)
                            elif db_f == 'identifiant':
                                data[db_f] = clean_identifiant(valeur_brute)
                            elif db_f == 'gestionnaire':
                                nom_brut = str(valeur_brute).strip()
                                nom_final = nom_brut.upper()
                                for agent in agents_noms:
                                    if agent.upper() == nom_brut.upper():
                                        nom_final = agent
                                        break
                                data[db_f] = nom_final
                            else:
                                data[db_f] = str(valeur_brute).strip().upper()

                        ident = data.get('identifiant', '')
                        if not ident: continue

                        exist = session.query(Dossier).filter_by(identifiant=ident).first()
                        if exist:
                            # LA MISE A JOUR PARFAITE EST ICI
                            for k, v in data.items():
                                setattr(exist, k, v)
                            count_upd += 1
                        else:
                            session.add(Dossier(**data))
                            count_add += 1
                session.commit()
                status.update(label=f"Opération terminée : {count_add} créés, {count_upd} mis à jour.", state="complete")
            st.balloons()
        except Exception as e:
            session.rollback()
            st.error(f"Erreur d'importation : {e}")
        finally: session.close()

# --- ADMIN ---
def page_admin():
    st.title("📊 Espace Administrateur")
    
    tab1, tab2, tab3 = st.tabs(["📈 Statistiques", "🔐 Gestion des Accès", "⚙️ Système"])

    with tab1:
        try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
        except: df = pd.DataFrame()
        
        if df.empty: 
            st.warning("La base de dossiers est vide.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Dossiers", len(df))
            c2.metric("Crédit PNR Engagé", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
            c3.metric("Recouvrement", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA")
            c4.metric("Dette Globale", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", delta_color="inverse")
            
            col_l, col_r = st.columns(2)
            with col_l:
                if 'statut_dossier' in df.columns:
                    st.plotly_chart(px.pie(df, names='statut_dossier', title="Répartition par Étapes", hole=0.3), use_container_width=True)
            with col_r:
                st.plotly_chart(px.bar(df[df['gestionnaire'] != '']['gestionnaire'].value_counts().reset_index(), x='count', y='gestionnaire', orientation='h', title="Charge par Accompagnateur"), use_container_width=True)

    with tab2:
        st.markdown("### 🔑 Liste des Accompagnateurs et Mots de passe")
        st.info("Modifiez le mot de passe directement dans le tableau ci-dessous et cliquez sur Sauvegarder.")
        
        try: 
            df_users = pd.read_sql_query("SELECT id, identifiant, nom, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
        except: 
            df_users = pd.DataFrame()
            
        if not df_users.empty:
            edited_users = st.data_editor(
                df_users,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None, 
                    "identifiant": st.column_config.TextColumn("Identifiant (Login)", disabled=True),
                    "nom": st.column_config.TextColumn("Nom de l'Accompagnateur", disabled=True),
                    "mot_de_passe": st.column_config.TextColumn("Mot de passe (Modifiable)")
                }
            )
            
            if st.button("💾 Sauvegarder les nouveaux mots de passe", type="primary"):
                session = get_session()
                try:
                    for _, row in edited_users.iterrows():
                        user_db = session.query(UtilisateurAuth).get(row['id'])
                        if user_db:
                            user_db.mot_de_passe = row['mot_de_passe']
                    session.commit()
                    st.success("✅ Mots de passe mis à jour avec succès dans la base de données !")
                except Exception as e:
                    session.rollback()
                    st.error(f"Erreur lors de la sauvegarde : {e}")
                finally:
                    session.close()

    with tab3:
        st.error("Zone de danger")
        st.markdown("Attention, ce bouton supprime tous les dossiers. Les comptes accompagnateurs seront conservés.")
        if st.button("🗑️ Vider la base de données (Dossiers uniquement)", type="primary"):
            session = get_session()
            session.query(Dossier).delete()
            session.commit()
            session.close()
            st.rerun()

# --- DEMARRAGE DE L'APPLICATION ---
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if page == "🗂️ Tous les Dossiers": page_gestion(vue_admin=True)
    elif page == "🗂️ Mes Dossiers Promoteurs": page_gestion(vue_admin=False)
    elif page == "📥 Importation des Fichiers": page_import()
    elif page == "📊 Espace Administrateur": page_admin()
