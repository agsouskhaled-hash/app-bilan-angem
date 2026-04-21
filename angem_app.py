import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import io
import base64
import urllib.parse
from datetime import datetime
from fpdf import FPDF
import tempfile
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURATION DE LA PAGE ET CLOUD
# ==========================================
st.set_page_config(
    page_title="ANGEM Workspace Ultra", 
    page_icon="🇩🇿", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]
LISTE_STATUTS = [
    "Phase dépôt du dossier", 
    "En attente de la commission", 
    "Accordé / En cours", 
    "En phase d'exploitation", 
    "Contentieux / Retard"
]

# --- Identifiants Supabase (Storage pour les scans) ---
SUPABASE_URL = "https://greyjhgiytajxpvucbrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyZXlqaGdpeXRhanhwdnVjYnJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTU0MjksImV4cCI6MjA4NzU5MTQyOX0.jCNan1Y1hvfGog6Zcu8Rr8d5PkeFRFvipAGGB09ztxo"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Initialisation des variables de session ---
if 'user' not in st.session_state: 
    st.session_state.user = None

if 'portal_selection' not in st.session_state: 
    st.session_state.portal_selection = None

if 'search_query' not in st.session_state: 
    st.session_state.search_query = ""

# --- Dynamique des couleurs ---
if st.session_state.user is not None:
    if st.session_state.user.get('env') == "PNR PROJET":
        theme_color = "#1f77b4"
        theme_bg = "#f4f9fc"
    else:
        theme_color = "#28a745"
        theme_bg = "#f4fcf5"
else:
    theme_color = "#2c3e50"
    theme_bg = "#f8f9fa"

# ==========================================
# 2. STYLE CSS PREMIUM DÉTAILLÉ
# ==========================================
st.markdown(f"""
<style>
    .stApp {{ 
        background-color: {theme_bg}; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }}
    
    /* --- Cartes Modernes --- */
    .modern-card {{ 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 16px; 
        box-shadow: 0 8px 24px rgba(0,0,0,0.04); 
        margin-top: 15px; 
        margin-bottom: 25px; 
        border: 1px solid #edf2f7; 
        border-top: 4px solid {theme_color}; 
        transition: transform 0.2s ease, box-shadow 0.2s ease; 
    }}
    .modern-card:hover {{ 
        transform: translateY(-2px); 
        box-shadow: 0 12px 32px rgba(0,0,0,0.08); 
    }}
    
    /* --- Cartes Statistiques (Supervision) --- */
    .metric-card {{ 
        background: #ffffff; 
        border-radius: 16px; 
        padding: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); 
        border-left: 6px solid {theme_color}; 
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        margin-bottom: 20px; 
    }}
    .metric-info {{ 
        display: flex; 
        flex-direction: column; 
    }}
    .metric-value {{ 
        font-size: 26px; 
        font-weight: 800; 
        color: #1e293b; 
        margin-top: 5px; 
    }}
    .metric-label {{ 
        font-size: 13px; 
        color: #64748b; 
        text-transform: uppercase; 
        font-weight: 700; 
    }}
    .metric-danger {{ 
        border-left-color: #ef4444; 
    }}
    
    /* --- Portail de Connexion --- */
    .portal-card {{ 
        background: #ffffff; 
        padding: 30px 20px; 
        border-radius: 16px; 
        text-align: center; 
        border: 2px solid #edf2f7; 
        cursor: pointer; 
        transition: all 0.3s ease; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
    }}
    .portal-card:hover {{ 
        border-color: {theme_color}; 
        transform: translateY(-5px); 
        box-shadow: 0 12px 24px rgba(0,0,0,0.1); 
    }}
    
    /* --- Profil Promoteur --- */
    .profil-header {{ 
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); 
        padding: 25px; 
        border-radius: 12px; 
        border-left: 8px solid {theme_color}; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
    }}
    .block-finance {{ 
        background-color: #eff6ff; 
        border-left: 5px solid #3b82f6; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 15px; 
    }}
    .block-recouvrement {{ 
        background-color: #f0fdf4; 
        border-left: 5px solid #22c55e; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 15px; 
    }}
    .block-title {{ 
        font-weight: bold; 
        color: #1e293b; 
        margin-bottom: 10px; 
        font-size: 16px; 
        text-transform: uppercase; 
    }}
    
    /* --- Boutons d'Action (Appel, WhatsApp, Maps) --- */
    .action-btn-container {{ 
        display: flex; 
        gap: 12px; 
        margin-top: 15px; 
        margin-bottom: 25px; 
        flex-wrap: wrap; 
    }}
    .btn-action {{ 
        flex: 1; 
        min-width: 160px; 
        padding: 12px 20px; 
        border-radius: 10px; 
        text-decoration: none; 
        font-weight: bold; 
        text-align: center; 
        color: white !important; 
        transition: all 0.3s; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        gap: 8px; 
        font-size: 15px; 
    }}
    .btn-call {{ background-color: #3b82f6; }} 
    .btn-call:hover {{ background-color: #2563eb; transform: translateY(-2px); }}
    .btn-wa {{ background-color: #22c55e; }} 
    .btn-wa:hover {{ background-color: #16a34a; transform: translateY(-2px); }}
    .btn-maps {{ background-color: #ef4444; }} 
    .btn-maps:hover {{ background-color: #dc2626; transform: translateY(-2px); }}
    
    /* --- Divers --- */
    .search-title {{ 
        color: {theme_color}; 
        font-weight: 800; 
        font-size: 20px; 
        margin-bottom: 15px; 
        text-transform: uppercase; 
        letter-spacing: 1px; 
    }}
    .alerte-nouveau {{ 
        background-color: #f0fdf4; 
        border-left: 6px solid #22c55e; 
        padding: 15px 20px; 
        border-radius: 8px; 
        color: #15803d; 
        font-weight: 600; 
        margin-bottom: 20px; 
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. MODÈLES DE BASE DE DONNÉES (DÉTAILLÉS)
# ==========================================
Base = declarative_base()
engine = create_engine("postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require", echo=False)
Session = sessionmaker(bind=engine)

class Dossier(Base):
    __tablename__ = 'dossiers'
    
    # --- Identité Système ---
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, index=True)
    type_dispositif = Column(String, default="PNR PROJET") 
    
    # --- Identité Promoteur ---
    nom = Column(String)
    prenom = Column(String)
    genre = Column(String)
    date_naissance = Column(String)
    adresse = Column(String)
    telephone = Column(String)
    niveau_instruction = Column(String)
    age = Column(String)
    
    # --- Projet & Localisation ---
    activite = Column(String)
    code_activite = Column(String)
    secteur = Column(String)
    daira = Column(String)
    commune = Column(String)
    gestionnaire = Column(String)
    zone = Column(String)
    
    # --- Informations Financières (Rubrique Finance) ---
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
    
    # --- Informations Recouvrement (Rubrique Recouvrement) ---
    montant_rembourse = Column(Float, default=0.0)
    reste_rembourser = Column(Float, default=0.0)
    nb_echeance_tombee = Column(String)
    date_ech_tomb = Column(String, default="")
    prochaine_ech = Column(String, default="")
    total_echue = Column(Float, default=0.0)
    etat_dette = Column(String)
    
    # --- Gestion et Documents ---
    statut_dossier = Column(String, default="Phase dépôt du dossier")
    documents = Column(String, default="") 
    historique_visites = Column(String, default="") # Sert aussi de Coffre Fourre-Tout
    prochaine_visite = Column(String, default="")
    est_nouveau = Column(String, default="NON")
    
    # --- SYSTEME DE BADGES (Séparation Finance / Recouvrement) ---
    in_finance = Column(String, default="NON")
    in_recouvrement = Column(String, default="NON")

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, unique=True)
    nom = Column(String)
    mot_de_passe = Column(String)
    role = Column(String)
    daira = Column(String, default="")

# Création physique des tables
Base.metadata.create_all(engine)

# --- Migrations automatiques de sécurité ---
try:
    with engine.connect() as conn:
        colonnes_string = [
            "type_dispositif", 
            "date_naissance", 
            "num_ordre_versement", 
            "debut_consommation", 
            "etat_dette", 
            "est_nouveau", 
            "date_ech_tomb", 
            "prochaine_ech", 
            "in_finance", 
            "in_recouvrement"
        ]
        
        for col in colonnes_string: 
            conn.execute(text(f"ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS {col} VARCHAR DEFAULT ''"))
        
        colonnes_float = [
            "apport_personnel", 
            "total_echue", 
            "credit_bancaire"
        ]
        
        for col in colonnes_float: 
            conn.execute(text(f"ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS {col} FLOAT DEFAULT 0.0"))
        
        # Mettre à jour les anciens dossiers pour qu'ils s'affichent partout par défaut s'ils n'ont pas de badge
        conn.execute(text("UPDATE dossiers SET in_finance='OUI' WHERE in_finance='' OR in_finance IS NULL"))
        conn.execute(text("UPDATE dossiers SET in_recouvrement='OUI' WHERE in_recouvrement='' OR in_recouvrement IS NULL"))
        
        conn.commit()
except Exception as e: 
    print("Erreur silencieuse migration DB :", e)

def get_session(): 
    return Session()

def init_db_users():
    session = get_session()
    
    admin_exist = session.query(UtilisateurAuth).filter_by(identifiant="admin").first()
    if not admin_exist: 
        session.add(UtilisateurAuth(
            identifiant="admin", 
            nom="Administrateur", 
            mot_de_passe="angem", 
            role="admin"
        ))
        
    finance_exist = session.query(UtilisateurAuth).filter_by(identifiant="finance").first()
    if not finance_exist: 
        session.add(UtilisateurAuth(
            identifiant="finance", 
            nom="Service Finance", 
            mot_de_passe="angem", 
            role="finance"
        ))
        
    session.commit()
    session.close()

init_db_users()

# ==========================================
# 4. DICTIONNAIRE RADAR ET UTILITAIRES
# ==========================================
MAPPING_CONFIG_KEYWORDS = {
    'identifiant': ['IDENTIFIANT', 'CNI', 'NCINPC', 'NAT', 'ID'], 
    'nom': ['NOMETPRENOM', 'NOM', 'PROMOTEUR'], 
    'prenom': ['PRENOM'],
    'date_naissance': ['NAISSANCE', 'DATENAISS', 'NELE'], 
    'adresse': ['ADRESSE', 'LIEU'], 
    'telephone': ['TEL', 'MOB', 'TELEPHONE'],
    'commune': ['COMMUNE', 'APC'], 
    'activite': ['ACTIVITE', 'PROJET', 'INTITULE'], 
    'gestionnaire': ['GEST', 'ACCOMPAGNATEUR', 'AGENT'],
    'banque_nom': ['BANQUE', 'CCP', 'AGENCE'], 
    'num_ordre_versement': ['NUMOV', 'ORDREVERSEMENT', 'OV'], 
    'date_financement': ['DATEOV', 'DATEVIREMENT', 'DATEFINAN'],
    'debut_consommation': ['DEBUTCONSOM', 'CONSOMMATION'], 
    'montant_pnr': ['PNR', 'MONTANTPNR', 'MONTANT', 'CREDIT'],
    'montant_rembourse': ['TOTALREMB', 'VERSEMENT', 'REMBOURSE', 'TOTALVERS'], 
    'reste_rembourser': ['RESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'nb_echeance_tombee': ['ECHTOMB', 'ECHEANCES', 'NBRECHTOMB'], 
    'date_ech_tomb': ['DATEECHTOMB', 'DATEECHEANCETOMBEE', 'DATEECH'],
    'prochaine_ech': ['PROCHAINEECH', 'PROCHECH'], 
    'total_echue': ['TOTALECHUE', 'MONTECHEAN'], 
    'etat_dette': ['ETATDETTE', 'ETAT']
}

COLONNES_ARGENT = [
    'montant_pnr', 
    'montant_rembourse', 
    'reste_rembourser', 
    'total_echue', 
    'apport_personnel', 
    'credit_bancaire'
]

def clean_pdf_text(t): 
    if not t: 
        return ""
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('utf-8')

def clean_money(v):
    if pd.isna(v) or str(v).strip() == '': 
        return None
    try: 
        val_propre = re.sub(r'[^\d\.-]', '', str(v).replace('DA', '').replace(' ', '').replace(',', '.'))
        return float(val_propre)
    except: 
        return None

def clean_identifiant(v):
    s = str(v).strip().upper()
    if 'E' in s and s.replace('E','').replace('.','').replace('+','').isdigit():
        try:
            return f"{float(s):.0f}"
        except:
            pass
    if s.endswith('.0'):
        return s[:-2]
    return s

def clean_header(v): 
    return ''.join(filter(str.isalnum, str(v).upper()))

def trouver_agent_intelligent(nom_excel, liste_officielle):
    nom_ex = str(nom_excel).strip().upper()
    if not nom_ex or nom_ex == "NAN": 
        return ""
        
    for agent in liste_officielle:
        if agent.upper() in nom_ex or nom_ex in agent.upper(): 
            return agent
            
    return nom_ex

def calculer_alerte_bool(row):
    ech = str(row.get('nb_echeance_tombee', '')).strip()
    if any(char.isdigit() for char in ech):
        chiffre = int(re.search(r'\d+', ech).group())
        if chiffre > 0:
            return True
            
    statut = row.get('statut_dossier')
    etat = row.get('etat_dette')
    if statut == "Contentieux / Retard" or etat == "CONTENTIEUX": 
        return True
        
    return False

# ==========================================
# 5. MOTEURS DE GÉNÉRATION PDF
# ==========================================
def generer_fiche_promoteur_pdf(dos):
    pdf = FPDF()
    pdf.add_page()
    
    # Titre
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "FICHE OFFICIELLE PROMOTEUR - ANGEM", ln=True, align='C')
    
    # Bloc 1 : Identification
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "1. IDENTIFICATION", border=1, ln=True, fill=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"ID : {clean_pdf_text(dos.identifiant)}", border='L')
    pdf.cell(95, 8, f"Agent : {clean_pdf_text(dos.gestionnaire)}", border='R', ln=True)
    
    pdf.cell(95, 8, f"Nom : {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", border='L')
    pdf.cell(95, 8, f"Tel : {clean_pdf_text(dos.telephone)}", border='R', ln=True)
    
    pdf.cell(0, 8, f"Adresse : {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)}", border='LRB', ln=True)
    pdf.ln(3)
    
    # Bloc 2 : Financement
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "2. FINANCEMENT", border=1, ln=True, fill=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"Dispositif : {clean_pdf_text(dos.type_dispositif)}", border='L')
    pdf.cell(95, 8, f"Banque : {clean_pdf_text(dos.banque_nom)}", border='R', ln=True)
    
    pdf.cell(95, 8, f"Activite : {clean_pdf_text(dos.activite)}", border='L')
    pdf.cell(95, 8, f"Num OV : {clean_pdf_text(dos.num_ordre_versement)}", border='R', ln=True)
    
    pdf.cell(0, 8, f"Credit PNR : {dos.montant_pnr:,.0f} DA", border='LRB', ln=True)
    pdf.ln(3)
    
    # Bloc 3 : Recouvrement
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "3. RECOUVREMENT", border=1, ln=True, fill=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"Rembourse : {dos.montant_rembourse:,.0f} DA", border='L')
    pdf.cell(95, 8, f"Reste : {dos.reste_rembourser:,.0f} DA", border='R', ln=True)
    
    pdf.cell(95, 8, f"Ech. Tombees : {clean_pdf_text(dos.nb_echeance_tombee)} ({clean_pdf_text(dos.date_ech_tomb)})", border='L')
    pdf.cell(95, 8, f"Echue : {dos.total_echue:,.0f} DA", border='R', ln=True)
    
    pdf.cell(0, 8, f"Etat : {clean_pdf_text(dos.etat_dette)} | Prochaine : {clean_pdf_text(dos.prochaine_ech)}", border='LRB', ln=True)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def generer_rapport_global_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "ETAT GLOBAL DES DOSSIERS", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Total Dossiers : {len(df)}", ln=True)
    pdf.cell(0, 10, f"PNR Engage : {df['montant_pnr'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 10, f"Total Recouvre : {df['montant_rembourse'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 10, f"Reste a Recouvrer : {df['reste_rembourser'].astype(float).sum():,.0f} DA", ln=True)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def generer_creances_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 20, "DOSSIERS EN SOUFFRANCE", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    
    df_retard = df[df.apply(calculer_alerte_bool, axis=1)]
    pdf.set_font("Arial", '', 10)
    
    for _, row in df_retard.iterrows():
        texte = f"ID: {row['identifiant']} | Nom: {clean_pdf_text(row['nom'])} | Reste: {row['reste_rembourser']:,.0f} DA | Agent: {clean_pdf_text(row['gestionnaire'])}"
        pdf.cell(0, 8, texte, ln=True, border='B')
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

# ==========================================
# 6. PORTAIL DE CONNEXION ET SIDEBAR
# ==========================================
def login_page():
    st.markdown("<br><h2 style='text-align: center; color: #1e293b; font-weight: 800;'>Portail de Connexion</h2>", unsafe_allow_html=True)
    
    if st.session_state.portal_selection is None:
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("👩‍💻\n\nAccompagnateurs", use_container_width=True): 
                st.session_state.portal_selection = "agent"
        with c2: 
            if st.button("💰\n\nService Finance", use_container_width=True): 
                st.session_state.portal_selection = "finance"
        with c3: 
            if st.button("👑\n\nDirection & Admin", use_container_width=True): 
                st.session_state.portal_selection = "admin"
    else:
        if st.button("⬅️ Retour"): 
            st.session_state.portal_selection = None
            st.rerun()
            
        session = get_session()
        users = session.query(UtilisateurAuth).filter_by(role=st.session_state.portal_selection).all()
        session.close()
        
        if users:
            st.markdown("<div class='modern-card' style='max-width: 500px; margin: 0 auto;'>", unsafe_allow_html=True)
            nom = st.selectbox("👤 Profil", [u.nom for u in users])
            pwd = st.text_input("🔑 Mot de passe", type="password")
            env = st.selectbox("🏢 Dispositif", ["PNR PROJET", "PNR AMP"])
            
            if st.button("🚀 Connexion", type="primary", use_container_width=True):
                user_db = next(u for u in users if u.nom == nom)
                if user_db.mot_de_passe == pwd:
                    st.session_state.user = {
                        "nom": user_db.nom, 
                        "role": user_db.role, 
                        "daira": user_db.daira, 
                        "env": env
                    }
                    st.rerun()
                else: 
                    st.error("Mot de passe incorrect.")
            st.markdown("</div>", unsafe_allow_html=True)

def sidebar_menu():
    role = st.session_state.user['role']
    env = st.session_state.user['env']
    daira = st.session_state.user.get('daira', '')
    
    st.sidebar.markdown(f"""
    <div style='background:#ffffff; padding:20px; border-radius:16px; border:1px solid #e2e8f0; text-align:center; margin-bottom:25px;'>
        <div style='font-size: 30px;'>👤</div>
        <div style='font-weight: 800;'>{st.session_state.user['nom']}</div>
        <div style='color: #64748b; font-size: 12px;'>{daira}</div>
        <div style='margin-top:5px; background:{theme_color}; color:white; padding:4px; border-radius:10px; font-size:11px;'>{env}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if role == "finance": 
        opts = ["📥 Import Financement", "🗂️ Vue Financement"] 
    elif role == "admin": 
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement", "📊 Supervision Direction", "⚙️ Intégration Admin"] 
    else: 
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement", "🗑️ Corbeille"]
    
    choice = st.sidebar.radio("Navigation", opts, label_visibility="collapsed")
    
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True): 
        st.session_state.user = None
        st.session_state.portal_selection = None
        st.rerun()
        
    return choice

# ==========================================
# 7. VUES PRINCIPALES (FICHES & TABLEAUX)
# ==========================================
def afficher_profil_complet(dos_db, session):
    if dos_db.est_nouveau == "OUI" and dos_db.gestionnaire == st.session_state.user['nom']: 
        dos_db.est_nouveau = "NON"
        session.commit()
        
    taux = (dos_db.montant_rembourse / dos_db.montant_pnr) if dos_db.montant_pnr > 0 else 0
    
    st.markdown(f"""
    <div class='profil-header'>
        <div>
            <h2 style='margin:0;'>{dos_db.nom} {dos_db.prenom}</h2>
            <p style='margin:0;'>ID: {dos_db.identifiant} | {dos_db.activite}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1: 
        st.markdown(f"""
        <div class='block-finance'>
            <div class='block-title'>🏦 Financement</div>
            <b>PNR :</b> {dos_db.montant_pnr:,.0f} DA<br>
            <b>OV :</b> {dos_db.num_ordre_versement}<br>
            <b>Banque :</b> {dos_db.banque_nom}
        </div>
        """, unsafe_allow_html=True)
        
    with c2: 
        st.markdown(f"""
        <div class='block-recouvrement'>
            <div class='block-title'>📈 Recouvrement</div>
            <b>Remboursé :</b> {dos_db.montant_rembourse:,.0f} DA<br>
            <b>Reste :</b> <span style='color:#dc2626;'>{dos_db.reste_rembourser:,.0f} DA</span><br>
            <b>Échue :</b> {dos_db.total_echue:,.0f} DA<br>
            <b>Échéances :</b> {dos_db.nb_echeance_tombee} ({dos_db.date_ech_tomb})<br>
            <b>État :</b> {dos_db.etat_dette}
        </div>
        """, unsafe_allow_html=True)
        
        # --- LA BARRE DE PROGRESSION DU REMBOURSEMENT ---
        st.progress(min(taux, 1.0))
        st.caption(f"Progression du remboursement : {taux*100:.1f}%")
    
    tel = re.sub(r'\D', '', str(dos_db.telephone or ""))
    st.markdown("<div class='action-btn-container'>", unsafe_allow_html=True)
    
    if len(tel) >= 9: 
        num_wa = '213' + tel[1:] if tel.startswith('0') else tel
        # --- BOUTONS D'APPELS ET MESSAGES ---
        st.markdown(f"<a href='tel:{tel}' class='btn-action btn-call' target='_blank'>📞 Appeler le promoteur</a>", unsafe_allow_html=True)
        st.markdown(f"<a href='https://wa.me/{num_wa}' class='btn-action btn-wa' target='_blank'>💬 Message WhatsApp</a>", unsafe_allow_html=True)
        
    lien_maps = f"http://maps.google.com/?q={dos_db.adresse}+{dos_db.commune}"
    st.markdown(f"<a href='{lien_maps}' class='btn-action btn-maps' target='_blank'>🗺️ Ouvrir Maps</a></div>", unsafe_allow_html=True)

    col_g, col_d = st.columns([1.5, 1])
    
    with col_g:
        st.markdown("<div class='modern-card'>### 📝 Historique & Notes Importées", unsafe_allow_html=True)
        note = st.text_area("Ajouter une observation :", key=f"n_{dos_db.id}")
        
        if st.button("Enregistrer", key=f"bn_{dos_db.id}"): 
            date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            dos_db.historique_visites = f"🔹 **[{date_str}]** {note}\n" + (dos_db.historique_visites or "")
            session.commit()
            st.rerun()
            
        hist_propre = (dos_db.historique_visites or 'Aucun rapport enregistré').replace(chr(10), '<br>')
        st.markdown(f"<div style='background:#f8fafc; padding:15px; border-radius:8px; height: 200px; overflow-y: auto;'>{hist_propre}</div></div>", unsafe_allow_html=True)
        
    with col_d:
        st.markdown("<div class='modern-card'>### 📎 Documents Cloud", unsafe_allow_html=True)
        pdf_data = generer_fiche_promoteur_pdf(dos_db)
        st.download_button("📄 Télécharger Fiche PDF", data=pdf_data, file_name=f"ANGEM_{dos_db.identifiant}.pdf", mime="application/pdf", use_container_width=True)
        
        with st.expander("📸 Scanner ou Joindre un document"):
            cam = st.camera_input("Caméra", key=f"c_{dos_db.id}")
            file_up = st.file_uploader("Fichier image", key=f"f_{dos_db.id}")
            
            if st.button("☁️ Archiver sur Supabase", key=f"u_{dos_db.id}"):
                data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                if data:
                    try: 
                        fname = f"{dos_db.identifiant}_{int(datetime.now().timestamp())}.jpg"
                        supabase_client.storage.from_("scans_angem").upload(file=data, path=fname, file_options={"content-type": "image/jpeg"})
                        dos_db.documents = (dos_db.documents or "") + fname + "|"
                        session.commit()
                        st.success("Document archivé !")
                    except Exception as e: 
                        st.error(f"Erreur Cloud: {e}")
                        
        if dos_db.documents:
            docs = [x for x in dos_db.documents.split('|') if x]
            for d in docs: 
                url = supabase_client.storage.from_('scans_angem').get_public_url(d)
                st.markdown(f"📥 <a href='{url}' target='_blank'>Voir le document joint</a>", unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)

def page_gestion(mode="financement", vue_admin=False):
    env = st.session_state.user['env']
    role = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    
    # --- LA RÈGLE DES BADGES POUR LE ZÉRO CROISEMENT ---
    colonne_badge = "in_finance" if mode == "financement" else "in_recouvrement"
    
    try: 
        # On ne charge QUE les dossiers qui ont le badge de la rubrique demandée
        query = f"SELECT * FROM dossiers WHERE type_dispositif='{env}' AND {colonne_badge}='OUI' ORDER BY id DESC"
        df = pd.read_sql_query(query, con=engine).fillna('')
    except: 
        df = pd.DataFrame()
        
    if df.empty: 
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    # Notification de nouveaux dossiers pour les agents
    if role == 'agent' and mode == 'financement':
        nvx = len(df[(df['gestionnaire'].str.upper() == nom_agent) & (df['est_nouveau'] == "OUI")])
        if nvx > 0: 
            st.markdown(f"<div class='alerte-nouveau'>🎉 Vous avez {nvx} nouveau(x) dossier(s) affecté(s) !</div>", unsafe_allow_html=True)

    # Moteur de recherche
    st.markdown(f"<div class='modern-card'><div class='search-title'>🔍 Recherche {mode}</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([4, 1, 1])
    tmp_s = c1.text_input("Recherche rapide...", value=st.session_state.search_query, label_visibility="collapsed")
    
    if c2.button("🔍 Chercher", type="primary", use_container_width=True): 
        st.session_state.search_query = tmp_s
        st.rerun()
        
    if c3.button("❌ Effacer", use_container_width=True): 
        st.session_state.search_query = ""
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)

    # Filtrage par recherche
    if st.session_state.search_query: 
        df = df[df.apply(lambda x: x.astype(str).str.contains(st.session_state.search_query, case=False).any(), axis=1)]
        
    # Filtrage par agent (sauf admin et finance)
    if not vue_admin and role == "agent": 
        df = df[df['gestionnaire'].str.upper() == nom_agent]

    df.insert(0, "Ouvrir 📂", False)
    
    # Préparation de la liste des agents pour le menu déroulant
    try:
        df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=engine)
        noms_db = df_agents['nom'].dropna().tolist()
        noms_dossiers = df['gestionnaire'].dropna().tolist()
        liste_agents = [""] + sorted(list(set(noms_db + noms_dossiers)))
    except: 
        liste_agents = [""]
    
    # --- CONFIGURATION DES COLONNES PAR RUBRIQUE ---
    if mode == "financement":
        cols = [
            "Ouvrir 📂", 
            "identifiant", 
            "nom", 
            "prenom", 
            "statut_dossier", 
            "gestionnaire", 
            "montant_pnr", 
            "num_ordre_versement", 
            "banque_nom", 
            "date_financement", 
            "id"
        ]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False), 
            "id": None, 
            # --- LES MENUS DÉROULANTS RESTAURÉS ---
            "statut_dossier": st.column_config.SelectboxColumn("Étape du dossier", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent Affecté", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR Débloqué", format="%d DA")
        }
    else:
        # --- LES 7 COLONNES ULTRA-EPURÉES + GESTIONNAIRE ---
        cols = [
            "Ouvrir 📂", 
            "identifiant", 
            "nom", 
            "prenom", 
            "telephone", 
            "montant_pnr", 
            "montant_rembourse", 
            "reste_rembourser", 
            "gestionnaire", 
            "id"
        ]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False), 
            "id": None,
            "identifiant": st.column_config.TextColumn("Identifiant", disabled=True), 
            "nom": st.column_config.TextColumn("Nom", disabled=True),
            "prenom": st.column_config.TextColumn("Prénom", disabled=True), 
            "telephone": st.column_config.TextColumn("Téléphone", disabled=True),
            "montant_pnr": st.column_config.NumberColumn("Montant Crédit", format="%d DA", disabled=True),
            "montant_rembourse": st.column_config.NumberColumn("Total Remboursé", format="%d DA", disabled=True), 
            "reste_rembourser": st.column_config.NumberColumn("Reste à Rembourser", format="%d DA", disabled=True),
            "gestionnaire": st.column_config.TextColumn("Agent Affecté", disabled=True)
        }

    st.markdown("<div class='modern-card' style='padding: 10px;'>", unsafe_allow_html=True)
    
    # Affichage du tableau interactif
    edited = st.data_editor(
        df[cols], 
        use_container_width=True, 
        hide_index=True, 
        column_config=config, 
        height=600
    )
    
    # Sauvegarde des modifications (Seulement en mode finance ou admin)
    if mode == "financement" and st.button("💾 Sauvegarder les modifications", type="primary"):
        session = get_session()
        for _, r in edited.iterrows():
            dos = session.query(Dossier).get(r['id'])
            if dos: 
                dos.statut_dossier = r['statut_dossier']
                if role != 'agent':
                    dos.gestionnaire = str(r['gestionnaire']).strip().upper()
        session.commit()
        session.close()
        st.toast("✅ Base de données mise à jour !")
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)

    # Affichage du profil complet si une ligne est cochée
    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        session = get_session()
        dos = session.query(Dossier).get(int(sel.iloc[0]['id']))
        if dos: 
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            afficher_profil_complet(dos, session)
            st.markdown("</div>", unsafe_allow_html=True)
        session.close()

# ==========================================
# 8. MAPPING INTERACTIF & FOURRE-TOUT
# ==========================================
def get_header_row(df_raw):
    for i in range(min(30, len(df_raw))):
        row_cl = [clean_header(str(x)) for x in df_raw.iloc[i].values]
        if sum([1 for k in ["IDENTIFIANT", "CNI", "NOM", "GEST", "PRENOM", "ID"] if k in row_cl]) >= 1: 
            return i
    return -1

def page_integration_admin():
    env = st.session_state.user['env']
    role = st.session_state.user['role']
    
    st.title("⚙️ Intégration : Mapping & Fourre-Tout")
    
    if role == "finance":
        tabs = st.tabs(["💰 IMPORT FINANCE (CRÉATION)"])
        t1 = tabs[0]
        t2, t3, t4 = None, None, None
    else:
        t1, t2, t3, t4 = st.tabs(["💰 IMPORT FINANCE", "📈 IMPORT RECOUVREMENT", "🧹 DOUBLONS", "🔐 EQUIPES"])
    
    # --- ONGLET 1 : IMPORTATION FINANCE ---
    with t1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("💡 **FINANCE (Création) :** Attribue le Gestionnaire et crée la fiche UNIQUEMENT pour la rubrique Finance.")
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx', 'xls', 'csv'], key="ff")
        
        if f_fin:
            if f_fin.name.endswith('.csv'):
                df_raw = pd.read_csv(f_fin, sep=None, engine='python', dtype=str)
            else:
                df_raw = pd.read_excel(f_fin, dtype=str)
                
            df_raw = df_raw.fillna('')
            header_idx = get_header_row(df_raw)
            
            if header_idx != -1:
                # Etape 1 : Lecture propre de l'Excel
                df = df_raw.iloc[header_idx:].copy()
                df.columns = df.iloc[0].astype(str).tolist()
                df = df.iloc[1:].reset_index(drop=True)
                excel_cols = ["-- Ignorer --"] + list(df.columns)
                
                # Etape 2 : L'interface de Mapping
                st.write("### 🎛️ Étape 2 : Mapping des Colonnes (Finance)")
                mapping = {}
                
                with st.form("form_fin"):
                    c1, c2 = st.columns(2)
                    targets_fin = [
                        'identifiant', 'nom', 'prenom', 'date_naissance', 
                        'adresse', 'telephone', 'commune', 'activite', 
                        'gestionnaire', 'banque_nom', 'num_ordre_versement', 
                        'date_financement', 'montant_pnr', 'apport_personnel', 
                        'credit_bancaire'
                    ]
                    
                    for idx, db_f in enumerate(targets_fin):
                        def_idx = 0
                        if db_f in MAPPING_CONFIG_KEYWORDS:
                            for i, col in enumerate(df.columns):
                                if any(kw in clean_header(col) for kw in MAPPING_CONFIG_KEYWORDS[db_f]): 
                                    def_idx = i + 1
                                    break
                        with (c1 if idx % 2 == 0 else c2): 
                            mapping[db_f] = st.selectbox(f"Colonne pour '{db_f}'", excel_cols, index=def_idx)
                            
                    sub = st.form_submit_button("🚀 Créer les dossiers en base", type="primary")
                
                if sub:
                    session = get_session()
                    agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
                    c_add = 0
                    c_upd = 0
                    total_rows = len(df)
                    
                    # --- LA BARRE DE PROGRESSION RESTAURÉE ---
                    with st.status("Importation Finance en cours...", expanded=True) as status:
                        progress_bar = st.progress(0)
                        
                        for idx, row in df.iterrows():
                            # Mise à jour visuelle de la barre
                            if idx % max(1, (total_rows // 100)) == 0 or idx == total_rows - 1:
                                progress_bar.progress(min(1.0, (idx + 1) / total_rows))
                                
                            data = {}
                            mapped_cols = [v for v in mapping.values() if v != "-- Ignorer --"]
                            
                            # Extraction des données mappées
                            for db_f, xl_col in mapping.items():
                                if xl_col != "-- Ignorer --":
                                    val = row[xl_col]
                                    if pd.isna(val) or str(val).strip() in ["", "NAN", "None"]: 
                                        continue
                                        
                                    if db_f in COLONNES_ARGENT: 
                                        data[db_f] = clean_money(val)
                                    elif db_f == 'identifiant': 
                                        data[db_f] = clean_identifiant(val)
                                    elif db_f == 'gestionnaire': 
                                        data[db_f] = trouver_agent_intelligent(val, agents_db)
                                    else: 
                                        data[db_f] = str(val).strip().upper()
                            
                            ident = data.get('identifiant')
                            if not ident: 
                                continue
                                
                            # --- CORRECTION DU BOGUE PNR VIDE ---
                            valeur_pnr = data.get('montant_pnr')
                            if valeur_pnr is None:
                                valeur_pnr = 0.0
                            else:
                                valeur_pnr = float(valeur_pnr)
                                
                            # Construction du Coffre Fourre-Tout
                            notes = ""
                            for col in df.columns:
                                if col not in mapped_cols and str(row[col]).strip() not in ["", "NAN", "None"]: 
                                    notes += f"- {col} : {str(row[col]).strip()}\n"
                            
                            # Sauvegarde en base de données
                            exist = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).first()
                            
                            if exist:
                                for k, v in data.items():
                                    if v is not None and v != "": 
                                        setattr(exist, k, v)
                                
                                # C'est un import Finance, on active le badge Finance
                                exist.in_finance = "OUI"
                                
                                if notes: 
                                    date_str = datetime.now().strftime('%d/%m/%Y')
                                    exist.historique_visites = f"🔹 **[Import Finance {date_str}] Infos supp :**\n{notes}\n" + (exist.historique_visites or "")
                                c_upd += 1
                            else:
                                if valeur_pnr <= 40000: 
                                    continue
                                    
                                data['type_dispositif'] = env
                                data['est_nouveau'] = 'OUI'
                                
                                # C'est une création Finance, on active UNIQUEMENT le badge Finance
                                data['in_finance'] = 'OUI'
                                data['in_recouvrement'] = 'NON'
                                
                                if notes: 
                                    date_str = datetime.now().strftime('%d/%m/%Y')
                                    data['historique_visites'] = f"🔹 **[Import Finance {date_str}] Infos supp :**\n{notes}\n"
                                    
                                session.add(Dossier(**data))
                                c_add += 1
                                
                        session.commit()
                        session.close()
                        status.update(label=f"✅ Terminé ! {c_add} créés, {c_upd} mis à jour.", state="complete")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 2 : IMPORTATION RECOUVREMENT ---
    if t2:
        with t2:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.warning("🛡️ **RECOUVREMENT (MAJ) :** Met à jour l'argent. Crée les nouveaux dossiers UNIQUEMENT dans la rubrique Recouvrement. Ne modifie JAMAIS le Gestionnaire.")
            f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx', 'xls', 'csv'], key="fr")
            
            if f_rec:
                if f_rec.name.endswith('.csv'):
                    df_raw = pd.read_csv(f_rec, sep=None, engine='python', dtype=str)
                else:
                    df_raw = pd.read_excel(f_rec, dtype=str)
                    
                df_raw = df_raw.fillna('')
                header_idx = get_header_row(df_raw)
                
                if header_idx != -1:
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    excel_cols = ["-- Ignorer --"] + list(df.columns)
                    
                    st.write("### 🎛️ Étape 2 : Validation des Colonnes (Recouvrement 7 colonnes)")
                    mapping_rec = {}
                    
                    with st.form("form_rec"):
                        c1, c2 = st.columns(2)
                        
                        # Seulement les colonnes nécessaires pour le recouvrement
                        targets_rec = [
                            'identifiant', 'nom', 'prenom', 'telephone', 
                            'montant_pnr', 'montant_rembourse', 'reste_rembourser'
                        ]
                        
                        for idx, db_f in enumerate(targets_rec):
                            def_idx = 0
                            if db_f in MAPPING_CONFIG_KEYWORDS:
                                for i, col in enumerate(df.columns):
                                    if any(kw in clean_header(col) for kw in MAPPING_CONFIG_KEYWORDS[db_f]): 
                                        def_idx = i + 1
                                        break
                            with (c1 if idx % 2 == 0 else c2): 
                                mapping_rec[db_f] = st.selectbox(f"Colonne pour '{db_f}'", excel_cols, index=def_idx)
                                
                        sub_rec = st.form_submit_button("🚀 Mettre à jour la base Recouvrement", type="primary")
                    
                    if sub_rec:
                        session = get_session()
                        c_upd = 0
                        c_new = 0
                        total_rows = len(df)
                        
                        # --- LA BARRE DE PROGRESSION RESTAURÉE ---
                        with st.status("Importation Recouvrement en cours...", expanded=True) as status:
                            progress_bar = st.progress(0)
                            
                            for idx, row in df.iterrows():
                                # Mise à jour visuelle
                                if idx % max(1, (total_rows // 100)) == 0 or idx == total_rows - 1:
                                    progress_bar.progress(min(1.0, (idx + 1) / total_rows))
                                    
                                xl_id = mapping_rec.get('identifiant')
                                ident = clean_identifiant(row[xl_id]) if xl_id != "-- Ignorer --" else ""
                                if not ident: 
                                    continue
                                
                                # Coffre Fourre-Tout Recouvrement
                                notes = ""
                                mapped_cols = [v for v in mapping_rec.values() if v != "-- Ignorer --"]
                                for col in df.columns:
                                    if col not in mapped_cols and str(row[col]).strip() not in ["", "NAN", "None"]: 
                                        notes += f"- {col} : {str(row[col]).strip()}\n"

                                exist = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).first()
                                
                                if exist:
                                    # Le dossier existe déjà. On met à jour UNIQUEMENT l'argent et l'identité de base.
                                    for db_f, xl_col in mapping_rec.items():
                                        if xl_col != "-- Ignorer --" and db_f != 'identifiant':
                                            val = row[xl_col]
                                            if pd.isna(val) or str(val).strip() in ["", "NAN", "None"]: 
                                                continue
                                                
                                            if db_f in COLONNES_ARGENT:
                                                setattr(exist, db_f, clean_money(val))
                                            else:
                                                setattr(exist, db_f, str(val).strip().upper())
                                                
                                    # On active le badge Recouvrement pour qu'il apparaisse dans l'onglet
                                    exist.in_recouvrement = "OUI"
                                                
                                    if notes: 
                                        date_str = datetime.now().strftime('%d/%m/%Y')
                                        exist.historique_visites = f"🔹 **[Import Recouv {date_str}] Infos supp :**\n{notes}\n" + (exist.historique_visites or "")
                                    c_upd += 1
                                    
                                else: 
                                    # Le dossier n'existe pas. On le crée UNIQUEMENT pour le Recouvrement
                                    data_new = {}
                                    for db_f, xl_col in mapping_rec.items():
                                        if xl_col != "-- Ignorer --":
                                            val = row[xl_col]
                                            if pd.isna(val) or str(val).strip() in ["", "NAN", "None"]: 
                                                continue
                                                
                                            if db_f in COLONNES_ARGENT: 
                                                data_new[db_f] = clean_money(val)
                                            elif db_f == 'identifiant': 
                                                data_new[db_f] = clean_identifiant(val)
                                            else: 
                                                data_new[db_f] = str(val).strip().upper()
                                            
                                    data_new['type_dispositif'] = env
                                    
                                    # C'est une création Recouvrement, on active UNIQUEMENT le badge Recouvrement
                                    data_new['in_recouvrement'] = 'OUI' 
                                    data_new['in_finance'] = 'NON'      
                                    
                                    if notes: 
                                        date_str = datetime.now().strftime('%d/%m/%Y')
                                        data_new['historique_visites'] = f"🔹 **[Import Recouv {date_str}] Infos supp :**\n{notes}\n"
                                    
                                    session.add(Dossier(**data_new))
                                    c_new += 1
                                    
                            session.commit()
                            session.close()
                            status.update(label=f"✅ {c_upd} dossiers mis à jour, {c_new} nouveaux (Visibles uniquement Recouvrement).", state="complete")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 3 : MAINTENANCE ---
    if t3:
        with t3:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            if st.button("🚨 Nettoyer Doublons Stricts (Même ID + Même OV)", type="primary"):
                session = get_session()
                dossiers_db = session.query(Dossier).all()
                
                df_dup = pd.DataFrame([
                    {
                        'id': d.id, 
                        'identifiant': str(d.identifiant).strip(), 
                        'ov': str(d.num_ordre_versement).strip(), 
                        'type': d.type_dispositif
                    } 
                    for d in dossiers_db
                ])
                df_dup = df_dup[df_dup['identifiant'] != ""]
                
                if not df_dup.empty:
                    ids_to_keep = df_dup.groupby(['identifiant', 'ov', 'type'])['id'].max().tolist()
                    ids_del = df_dup[~df_dup['id'].isin(ids_to_keep)]['id'].tolist()
                    
                    if ids_del: 
                        session.query(Dossier).filter(Dossier.id.in_(ids_del)).delete(synchronize_session=False)
                        session.commit()
                        st.success(f"Opération réussie. {len(ids_del)} doublons ont été supprimés.")
                    else: 
                        st.info("La base est propre. Aucun doublon détecté.")
                session.close()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 4 : EQUIPES ---
    if t4:
        with t4:
            st.markdown("<div class='modern-card'>### 🔑 Équipes", unsafe_allow_html=True)
            try: 
                df_u = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
            except: 
                df_u = pd.DataFrame()
                
            if not df_u.empty:
                ed_u = st.data_editor(
                    df_u, 
                    use_container_width=True, 
                    hide_index=True, 
                    column_config={
                        "id": None, 
                        "identifiant": st.column_config.TextColumn(disabled=True), 
                        "nom": st.column_config.TextColumn(disabled=True), 
                        "daira": st.column_config.SelectboxColumn(options=LISTE_DAIRAS)
                    }
                )
                if st.button("💾 Sauvegarder Equipes", type="primary"):
                    session = get_session()
                    for _, r in ed_u.iterrows():
                        u = session.query(UtilisateurAuth).get(r['id'])
                        if u: 
                            u.mot_de_passe = r['mot_de_passe']
                            u.daira = r['daira']
                    session.commit()
                    session.close()
                    st.success("Mots de passe et Daïras mis à jour.")
                    
            with st.form("ajout_agent"):
                c1, c2, c3 = st.columns([1, 1.5, 1])
                n_id = c1.text_input("Identifiant de connexion")
                n_nom = c2.text_input("Nom Complet de l'agent")
                n_daira = c3.selectbox("Cellule assignée", LISTE_DAIRAS)
                
                if st.form_submit_button("Créer le compte Agent") and n_id and n_nom:
                    session = get_session()
                    if not session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first(): 
                        session.add(UtilisateurAuth(
                            identifiant=n_id.lower(), 
                            nom=n_nom.strip().upper(), 
                            daira=n_daira, 
                            mot_de_passe="angem2026", 
                            role="agent"
                        ))
                        session.commit()
                        st.success(f"Compte pour {n_nom} créé avec succès !")
                        st.rerun()
                    else:
                        st.error("Cet identifiant existe déjà.")
                    session.close()
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 9. SUPERVISION ET CORBEILLE
# ==========================================
def page_supervision():
    st.title("📊 Supervision Globale")
    env = st.session_state.user['env']
    
    df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{env}'", con=engine).fillna('')
    
    if df.empty: 
        st.warning("La base de données est vide pour cet environnement.")
        return
        
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        st.markdown(f"<div class='metric-card'><div class='metric-info'><div class='metric-label'>Total Dossiers</div><div class='metric-value'>{len(df)}</div></div></div>", unsafe_allow_html=True)
    with c2: 
        st.markdown(f"<div class='metric-card'><div class='metric-info'><div class='metric-label'>PNR Engagé</div><div class='metric-value'>{df['montant_pnr'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c3: 
        st.markdown(f"<div class='metric-card'><div class='metric-info'><div class='metric-label'>Total Recouvré</div><div class='metric-value'>{df['montant_rembourse'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c4: 
        st.markdown(f"<div class='metric-card metric-danger'><div class='metric-info'><div class='metric-label' style='color:#ef4444;'>Reste à Recouvrer</div><div class='metric-value' style='color:#dc2626;'>{df['reste_rembourser'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
        
    st.markdown("<div class='modern-card'>### 📥 Extractions Officielles", unsafe_allow_html=True)
    cb1, cb2, cb3 = st.columns(3)
    
    with cb1: 
        pdf_bilan = generer_rapport_global_pdf(df)
        st.download_button("📊 Bilan Global PDF", data=pdf_bilan, file_name="Bilan_Angem.pdf", mime="application/pdf", use_container_width=True)
    with cb2: 
        pdf_contentieux = generer_creances_pdf(df)
        st.download_button("🔴 Contentieux PDF", data=pdf_contentieux, file_name="Contentieux_Angem.pdf", mime="application/pdf", use_container_width=True)
    with cb3:
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        st.download_button("🟢 Sauvegarde Excel", data=buf.getvalue(), file_name="Backup_Base_Angem.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
    st.markdown("</div>", unsafe_allow_html=True)

def page_corbeille():
    env = st.session_state.user['env']
    agent = st.session_state.user['nom']
    daira = st.session_state.user['daira']
    
    if not daira: 
        st.warning("Vous n'avez pas de Daïra assignée.")
        return
        
    df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{env}'", con=engine).fillna('')
    
    mask_agent_vide = (df['gestionnaire'].str.strip() == "")
    mask_daira = (df['daira'].str.contains(daira, case=False) | df['commune'].str.contains(daira, case=False))
    
    orphans = df[mask_agent_vide & mask_daira].copy()
    
    st.markdown(f"<div class='modern-card'><h3 style='text-align:center;'>Dossiers non assignés à {daira} : {len(orphans)}</h3></div>", unsafe_allow_html=True)
    
    if not orphans.empty:
        orphans["C'est à moi !"] = False
        
        ed = st.data_editor(
            orphans, 
            hide_index=True, 
            column_config={"C'est à moi !": st.column_config.CheckboxColumn(default=False), "id": None}
        )
        
        ids = ed[ed["C'est à moi !"] == True]['id'].tolist()
        
        if st.button(f"📥 S'attribuer ces {len(ids)} dossiers", type="primary") and ids:
            session = get_session()
            session.query(Dossier).filter(Dossier.id.in_(ids)).update({"gestionnaire": agent.upper()}, synchronize_session=False)
            session.commit()
            session.close()
            st.success("Dossiers récupérés avec succès.")
            st.rerun()
    else:
        st.success("Félicitations, aucun dossier orphelin dans votre secteur.")

# ==========================================
# 10. ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None: 
    login_page()
else:
    page = sidebar_menu()
    
    if "Intégration" in page or "Import Admin" in page: 
        page_integration_admin()
    elif "Supervision" in page: 
        page_supervision()
    elif "Corbeille" in page: 
        page_corbeille()
    else: 
        if "Financement" in page:
            page_gestion(mode="financement", vue_admin=("Vue Globale" in page))
        else:
            page_gestion(mode="recouvrement", vue_admin=("Vue Globale" in page))
