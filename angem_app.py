import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import io
from datetime import datetime
import base64
from supabase import create_client, Client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Intra-Service ANGEM v16.0 Cloud", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]

# --- CONNEXION CLOUD SUPABASE (STORAGE) ---
SUPABASE_URL = "https://greyjhgiytajxpvucbrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyZXlqaGdpeXRhanhwdnVjYnJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTU0MjksImV4cCI6MjA4NzU5MTQyOX0.jCNan1Y1hvfGog6Zcu8Rr8d5PkeFRFvipAGGB09ztxo"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LE STYLE CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f4f7f6; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e1e5eb; padding: 20px;
        border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        border-left: 6px solid #1f77b4; transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s; border: none; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
    .login-container {
        background: #ffffff; padding: 40px; border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center;
        max-width: 400px; margin: 0 auto; border: 1px solid #f0f2f6;
    }
    .modern-card {
        background-color: #ffffff; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); margin-top: 15px; margin-bottom: 15px;
        border: 1px solid #e1e5eb;
    }
    .alerte-urgente {
        background-color: #fff3f3; border-left: 6px solid #dc3545; padding: 15px 20px;
        border-radius: 8px; color: #b02a37; font-weight: bold; margin-bottom: 20px;
    }
    .profil-header {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); padding: 20px;
        border-radius: 10px; border-left: 6px solid #28a745; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .profil-header h3 { margin-top: 0; color: #2c3e50; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { padding-top: 15px; padding-bottom: 15px; }
    .stTabs [aria-selected="true"] { background-color: transparent; border-bottom: 4px solid #1f77b4; font-weight: bold; color: #1f77b4; }
    .action-btn-container { display: flex; gap: 10px; margin-top: 10px; margin-bottom: 20px; }
    .btn-call { background-color: #007bff; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; width: 100%; display: block; transition: 0.3s; }
    .btn-wa { background-color: #25D366; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; width: 100%; display: block; transition: 0.3s; }
    .btn-call:hover, .btn-wa:hover { opacity: 0.8; color: white; }
    .doc-link { display: block; background-color: #f0f2f6; padding: 12px; border-radius: 8px; text-decoration: none; color: #1f77b4; font-weight: bold; margin-bottom: 8px; border: 1px solid #e1e5eb; transition: 0.2s;}
    .doc-link:hover { background-color: #e1e5eb; color: #0d47a1; }
</style>
""", unsafe_allow_html=True)

# --- CONNEXION BASE DE DONNÉES (POSTGRESQL) ---
Base = declarative_base()
engine = create_engine("postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require", echo=False)
Session = sessionmaker(bind=engine)

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
    documents = Column(String, default="") 
    historique_visites = Column(String, default="") 
    prochaine_visite = Column(String, default="")

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, unique=True)
    nom = Column(String)
    mot_de_passe = Column(String)
    role = Column(String)
    daira = Column(String, default="")

Base.metadata.create_all(engine)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS statut_dossier VARCHAR DEFAULT 'Phase dépôt du dossier'"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS documents VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS historique_visites VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS prochaine_visite VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE utilisateurs_auth ADD COLUMN IF NOT EXISTS daira VARCHAR DEFAULT ''"))
        conn.commit()
except: pass

def get_session(): return Session()

def init_db_users():
    session = get_session()
    admin = session.query(UtilisateurAuth).filter_by(identifiant="admin").first()
    if not admin:
        session.add(UtilisateurAuth(identifiant="admin", nom="Administrateur", mot_de_passe="angem", role="admin"))
    
    noms_agents = [
        "SALMI HOUDA", "BERRABEH DOUADI", "AIT OUAREB AMINA", "METMAR OMAR", 
        "MAASOUM SAIDA", "GUESSMIA ZAHIRA", "MAHREZ MOHAMED", "BELAID FAZIA", 
        "BEN AICHE MOUNIRA", "MEDJEDOUB AMEL", "BOUCHAREB MOUNIA", "MERAKEB FAIZA", 
        "MILOUDI AMEL", "BERROUANE SAMIRA", "MEDJHOUM RAOUIA", "FELFOUL SAMIRA", 
        "SAHNOUNE IMENE", "BOULAHLIB REDOUANE", "NASRI RYM", "BENSAHNOUN LILA", 
        "DJAOUDI SARAH", "MECHALIKHE FATMA", "KADRI SIHEM", "TALAMALI IMAD", "TOUAKNI SARAH"
    ]
    
    for nom in noms_agents:
        if not session.query(UtilisateurAuth).filter_by(nom=nom).first():
            base_id = nom.split()[0].lower()
            identifiant = base_id
            compteur = 1
            while session.query(UtilisateurAuth).filter_by(identifiant=identifiant).first():
                identifiant = f"{base_id}{compteur}"
                compteur += 1
            session.add(UtilisateurAuth(identifiant=identifiant, nom=nom, mot_de_passe="angem2026", role="agent"))
    
    session.commit()
    session.close()

init_db_users()

LISTE_STATUTS = ["Phase dépôt du dossier", "En attente de la commission d'éligibilité", "Accordé / En cours de financement", "En phase d'exploitation", "Contentieux / Retard de remboursement"]

def afficher_logo(largeur=250):
    try:
        with open("logo_angem.png", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            st.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="data:image/png;base64,{encoded_string}" width="{largeur}"></div>', unsafe_allow_html=True)
    except:
        st.markdown(f'<div style="text-align: center; color: #1f77b4; font-size: 24px; font-weight: bold; border: 2px solid #1f77b4; padding: 10px; border-radius: 10px; margin-bottom: 20px;">🔵 ANGEM Intra-Service</div>', unsafe_allow_html=True)

def clean_pdf_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')

# --- COORDONNÉES GPS POUR CARTOGRAPHIE ---
def get_lat_lon(commune_name):
    c = str(commune_name).upper().strip()
    if "ZÉRALDA" in c or "ZERALDA" in c or "STAOUELI" in c: return 36.7115, 2.8425
    if "CHÉRAGA" in c or "CHERAGA" in c or "AIN BENIAN" in c: return 36.7667, 2.9500
    if "DRARIA" in c or "BABA HASSEN" in c: return 36.7167, 2.9833
    if "BIR MOURAD RAIS" in c or "BIR MOURAD" in c: return 36.7333, 3.0500
    if "BOUZAREAH" in c or "BEN AKNOUN" in c: return 36.7833, 3.0167
    if "BIRTOUTA" in c or "TESSALA" in c: return 36.6500, 2.9833
    return 36.7300, 3.0000

# --- FONCTIONS PDF ---
def generer_fiche_promoteur_pdf(dos):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "FICHE OFFICIELLE DE SUIVI PROMOTEUR", ln=True, align='C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 1. IDENTIFICATION DU PROMOTEUR", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Identifiant : {clean_pdf_text(dos.identifiant)}", border='L')
    pdf.cell(95, 8, f" Accompagnateur : {clean_pdf_text(dos.gestionnaire)}", border='R', ln=True)
    pdf.cell(95, 8, f" Nom/Prenom : {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", border='L')
    pdf.cell(95, 8, f" Telephone : {clean_pdf_text(dos.telephone)}", border='R', ln=True)
    pdf.cell(0, 8, f" Adresse : {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)}", border='LRB', ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 2. PROJET & FINANCEMENT", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Activite : {clean_pdf_text(dos.activite)}", border='L')
    pdf.cell(95, 8, f" Statut : {clean_pdf_text(dos.statut_dossier)}", border='R', ln=True)
    pdf.cell(63, 8, f" Credit PNR : {dos.montant_pnr:,.0f} DA", border='L')
    pdf.cell(63, 8, f" Apport : {dos.apport_personnel:,.0f} DA")
    pdf.cell(64, 8, f" Banque : {dos.credit_bancaire:,.0f} DA", border='R', ln=True)
    pdf.cell(0, 8, f" Date de versement (OV) : {clean_pdf_text(dos.date_financement)}", border='LRB', ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 3. ETAT DU RECOUVREMENT", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Montant Recouvre : {dos.montant_rembourse:,.0f} DA", border='L')
    pdf.cell(95, 8, f" Reste a Rembourser : {dos.reste_rembourser:,.0f} DA", border='R', ln=True)
    pdf.cell(0, 8, f" Echeances tombees (Retard) : {clean_pdf_text(dos.nb_echeance_tombee)}", border='LRB', ln=True)
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 4. NOTES ET RAPPORT DE VISITE", ln=True)
    pdf.set_font("Arial", '', 11)
    if dos.historique_visites:
        notes = dos.historique_visites.split('\n')
        for note in notes[-5:]: 
            if note.strip(): pdf.cell(0, 6, clean_pdf_text(note), ln=True)
    pdf.ln(5)
    for _ in range(5): pdf.cell(0, 8, ".............................................................................................................................................................", ln=True)
    pdf.ln(10)
    pdf.cell(95, 8, " Signature de l'Accompagnateur :", align='C')
    pdf.cell(95, 8, " Cachet de l'Agence :", align='C', ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

def generer_bilan_global_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "BILAN GLOBAL DE DIRECTION - ANGEM", ln=True, align='C')
    pdf.ln(5)
    total_pnr = df['montant_pnr'].astype(float).sum()
    total_remb = df['montant_rembourse'].astype(float).sum()
    total_reste = df['reste_rembourser'].astype(float).sum()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. RESUME FINANCIER GLOBAL", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Total Dossiers : {len(df)}", ln=True)
    pdf.cell(0, 8, f"Total Credit PNR Engage : {total_pnr:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Montant Recouvre : {total_remb:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Dette Globale (Reste a payer) : {total_reste:,.0f} DA", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. RAPPORT DU PIPELINE DES DOSSIERS", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    statuts = df['statut_dossier'].value_counts()
    for stat, count in statuts.items():
        pdf.cell(0, 8, f"- {clean_pdf_text(stat)} : {count} dossiers", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

def generer_bilan_agent_pdf(df, nom_agent):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "BILAN DE PERFORMANCE ACCOMPAGNATEUR", ln=True, align='C')
    pdf.ln(5)
    nom_clean = str(nom_agent).upper()
    mots_agent = set([m for m in re.split(r'\W+', nom_clean) if len(m) >= 3])
    def match_agent(val):
        val_clean = str(val).upper()
        if not val_clean: return False
        if val_clean == nom_clean or nom_clean in val_clean or val_clean in nom_clean: return True
        mots_val = set([m for m in re.split(r'\W+', val_clean) if len(m) >= 3])
        if mots_agent.intersection(mots_val): return True
        return False
    df_agent = df[df['gestionnaire'].apply(match_agent)]
    total_pnr = df_agent['montant_pnr'].astype(float).sum()
    total_remb = df_agent['montant_rembourse'].astype(float).sum()
    taux = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"ACCOMPAGNATEUR : {clean_pdf_text(nom_agent)}", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Nombre total de dossiers en charge : {len(df_agent)}", ln=True)
    pdf.cell(0, 8, f"Total Credit PNR : {total_pnr:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Recouvre : {total_remb:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Taux de recouvrement global : {taux:.1f}%", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "REPARTITION DES DOSSIERS", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    statuts = df_agent['statut_dossier'].value_counts()
    for stat, count in statuts.items():
        pdf.cell(0, 8, f"- {clean_pdf_text(stat)} : {count} dossiers", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

def generer_creances_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 20, "ETAT DES CREANCES EN SOUFFRANCE", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    df_retard = df[df.apply(calculer_alerte_bool, axis=1)]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"Total des dossiers en retard ou contentieux : {len(df_retard)}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    for _, row in df_retard.iterrows():
        nom = clean_pdf_text(f"{row['nom']} {row['prenom']}")[:20] 
        agent = clean_pdf_text(row['gestionnaire'])[:15]
        txt = f"ID: {row['identifiant']} | {nom}... | Reste: {row['reste_rembourser']:,.0f} DA | Gest: {agent}"
        pdf.cell(0, 8, txt, ln=True, border='B')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

def generer_analytique_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "BILAN ANALYTIQUE (SECTEURS & ZONES)", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. REPARTITION PAR SECTEUR D'ACTIVITE", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    if 'secteur' in df.columns:
        secteurs = df[df['secteur'] != '']['secteur'].value_counts()
        for sect, count in secteurs.items():
            pdf.cell(0, 8, f"- {clean_pdf_text(sect)} : {count} dossiers", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. REPARTITION GEOGRAPHIQUE (Top 10 Communes)", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    if 'commune' in df.columns:
        communes = df[df['commune'] != '']['commune'].value_counts().head(10)
        for com, count in communes.items():
            pdf.cell(0, 8, f"- Commune de {clean_pdf_text(com)} : {count} dossiers", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

# --- UTILITAIRES ---
def trouver_agent_intelligent(nom_excel, liste_officielle):
    nom_ex = str(nom_excel).strip().upper()
    if not nom_ex or nom_ex == "NAN": return ""
    for agent in liste_officielle:
        if agent.upper() == nom_ex: return agent
    for agent in liste_officielle:
        agent_clean = agent.upper().replace("M. ", "").replace("MME ", "")
        if nom_ex in agent_clean or agent_clean in nom_ex: return agent
    mots_excel = nom_ex.split()
    for agent in liste_officielle:
        agent_upper = agent.upper()
        for mot in mots_excel:
            if len(mot) >= 3 and mot in agent_upper: return agent
    return nom_excel.strip().upper()

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
    return s

MAPPING_CONFIG = {
    'identifiant': ['IDENTIFIANT', 'CNI', 'NCINPC', 'CARTENAT'],
    'nom': ['NOM', 'NOMETPRENOM', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'gestionnaire': ['GEST', 'ACCOMPAGNATEUR', 'SUIVIPAR'],
    'daira': ['DAIRA'],
    'commune': ['COMMUNE', 'APC'],
    'secteur': ['SECTEURDACTIVITE', 'SECTEUR'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'montant_pnr': ['PNR', 'MONTANTPNR29', 'MTDUPNR', 'MONTANT'],
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'telephone': ['TEL', 'TELEPHONE', 'MOB', 'MOBILE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
    'date_financement': ['DATEOV', 'DATEDEVIREMENT', 'DATEVIREMENT', 'DATEDEFINANCEMENT'], 
}
COLONNES_ARGENT = ['montant_pnr', 'montant_rembourse', 'reste_rembourser']

if 'user' not in st.session_state: st.session_state.user = None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        afficher_logo(220)
        st.markdown("<h3 style='color: #2c3e50; margin-bottom: 25px;'>Portail Intra-Service</h3>", unsafe_allow_html=True)
        
        session = get_session()
        try:
            users_db = session.query(UtilisateurAuth).order_by(UtilisateurAuth.nom).all()
            noms_disponibles = [u.nom for u in users_db]
        except: noms_disponibles = ["Administrateur"]
        session.close()

        nom_choisi = st.selectbox("👤 Sélectionnez votre profil", noms_disponibles, label_visibility="collapsed")
        password = st.text_input("🔑 Mot de passe", type="password", placeholder="Votre mot de passe...", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Se Connecter", type="primary", use_container_width=True):
            session = get_session()
            user_db = session.query(UtilisateurAuth).filter_by(nom=nom_choisi).first()
            session.close()
            if user_db and user_db.mot_de_passe == password:
                st.session_state.user = {"identifiant": user_db.identifiant, "nom": user_db.nom, "role": user_db.role, "daira": user_db.daira}
                st.rerun()
            else: st.error("Mot de passe incorrect.")
        st.markdown("</div>", unsafe_allow_html=True)

def sidebar_menu():
    afficher_logo(180)
    daira_info = f" ({st.session_state.user.get('daira')})" if st.session_state.user.get('daira') else ""
    st.sidebar.markdown(f"<div style='text-align: center; padding: 10px; background: #e9ecef; border-radius: 8px; margin-bottom: 20px;'><b>👤 {st.session_state.user['nom']}</b><br><small>{daira_info}</small></div>", unsafe_allow_html=True)
    
    options = ["🗂️ Mes Dossiers Promoteurs"]
    if st.session_state.user['role'] == "admin":
        options = ["📊 Espace Direction", "🗂️ Base Globale", "📥 Intégration Fichiers"]
        
    choix = st.sidebar.radio("Navigation Menu", options, label_visibility="collapsed")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    return choix

def calculer_alerte_bool(row):
    ech = str(row.get('nb_echeance_tombee', '')).strip()
    if any(char.isdigit() for char in ech):
        num = int(re.search(r'\d+', ech).group())
        if num > 0: return True
    if row.get('statut_dossier') == "Contentieux / Retard de remboursement": return True
    return False

def calculer_alerte_texte(row):
    if calculer_alerte_bool(row): return "🚨 Retard (Échéance)"
    return "✅ À jour"

def page_gestion(vue_admin=False):
    st.title("🗂️ Espace de Suivi & Gestion")
    
    try: df = pd.read_sql_query("SELECT * FROM dossiers ORDER BY id DESC", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info("📌 La base de données est actuellement vide.")
        return
        
    df['Alerte'] = df.apply(calculer_alerte_texte, axis=1)

    if not vue_admin:
        nom_daira = st.session_state.user.get('daira', '')
        titre_corbeille = f"🔍 Corbeille ({nom_daira})" if nom_daira else "🔍 Corbeille dossiers non affectés"
        tab_main, tab_orphan = st.tabs(["🗂️ Mes Dossiers & Profil", titre_corbeille])
    else:
        tab_main = st.container()
        tab_orphan = None

    with tab_main:
        df_agent = df.copy()
        if not vue_admin: 
            nom_agent_connecte = str(st.session_state.user['nom']).upper()
            mots_agent = set([m for m in re.split(r'\W+', nom_agent_connecte) if len(m) >= 3])
            def match_agent_flexible(val):
                val_clean = str(val).upper()
                if not val_clean: return False
                if val_clean == nom_agent_connecte or nom_agent_connecte in val_clean or val_clean in nom_agent_connecte: return True
                mots_val = set([m for m in re.split(r'\W+', val_clean) if len(m) >= 3])
                if mots_agent.intersection(mots_val): return True
                return False
            df_agent = df_agent[df_agent['gestionnaire'].apply(match_agent_flexible)]

            df_visites = df_agent[df_agent['prochaine_visite'].str.strip() != ''].copy()
            if not df_visites.empty:
                with st.expander(f"🗓️ Mon Agenda : {len(df_visites)} visite(s) programmée(s)", expanded=True):
                    st.dataframe(df_visites[['identifiant', 'nom', 'commune', 'prochaine_visite', 'telephone']], hide_index=True, use_container_width=True)

        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        col_recherche, col_filtre = st.columns([2, 1])
        with col_recherche:
            search = st.text_input("🔍 Recherche rapide :", placeholder="Tapez un nom, un ID, une commune...")
        with col_filtre:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            filtre_alerte = st.radio("🚦 Filtrer l'affichage :", ["🟢 Tous les dossiers", "🚨 Contentieux & Retards"], horizontal=True, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        df_filtered = df_agent.copy()
        if search:
            mask = df_filtered.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
            df_filtered = df_filtered[mask]
        if "🚨" in filtre_alerte:
            df_filtered = df_filtered[df_filtered['Alerte'] != "✅ À jour"]
            
        if not vue_admin and "🚨" not in filtre_alerte:
            dossiers_alerte = df_agent[df_agent.apply(calculer_alerte_bool, axis=1)]
            if not dossiers_alerte.empty:
                st.markdown(f"<div class='alerte-urgente'>⚠️ Attention : Vous avez {len(dossiers_alerte)} dossier(s) nécessitant une intervention prioritaire ! (Utilisez le filtre ci-dessus)</div>", unsafe_allow_html=True)

        try:
            df_agents_auth = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=engine)
            agents_officiels = df_agents_auth['nom'].tolist()
        except: agents_officiels = []
        
        agents_dans_base = df['gestionnaire'].unique().tolist()
        liste_agents_complete = [""] + sorted(list(set(agents_officiels + agents_dans_base)))

        st.caption(f"Affichage de {len(df_filtered)} dossiers.")

        edited_df = st.data_editor(
            df_filtered, use_container_width=True, hide_index=True, height=350,
            column_config={
                "id": None, "documents": None, "historique_visites": None, "prochaine_visite": None,
                "Alerte": st.column_config.TextColumn("Statut", disabled=True),
                "identifiant": st.column_config.TextColumn("Identifiant", disabled=True),
                "date_financement": st.column_config.TextColumn("Date OV", disabled=True),
                "nom": "Nom Promoteur",
                "statut_dossier": st.column_config.SelectboxColumn("Étape Actuelle", options=LISTE_STATUTS, width="medium"),
                "gestionnaire": st.column_config.SelectboxColumn("Accompagnateur", options=liste_agents_complete, disabled=not vue_admin),
                "montant_pnr": st.column_config.NumberColumn("PNR", format="%d DA", disabled=True),
                "reste_rembourser": st.column_config.NumberColumn("Reste à payer", format="%d DA", disabled=True),
            }
        )

        if st.button("💾 Enregistrer les modifications du tableau", type="primary"):
            session = get_session()
            try:
                for _, row in edited_df.iterrows():
                    dos = session.query(Dossier).get(row['id'])
                    if dos:
                        setattr(dos, 'statut_dossier', row['statut_dossier'])
                        if vue_admin: setattr(dos, 'gestionnaire', row['gestionnaire'])
                session.commit()
                st.toast("✅ Base de données mise à jour !")
                st.rerun()
            except Exception as e: session.rollback(); st.error(f"Erreur : {e}")
            finally: session.close()

        # --- LE PROFIL PROMOTEUR (AVEC CLOUD STORAGE) ---
        st.markdown("<br><h2 style='color: #2c3e50; border-bottom: 2px solid #1f77b4; padding-bottom: 10px;'>📂 Profil Numérique du Promoteur</h2>", unsafe_allow_html=True)
        
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        recherche_indiv = st.text_input("🔍 Ouvrir un profil spécifique (Entrez Nom ou ID) :", placeholder="Ex: Metmar ou 12345...")
        
        if recherche_indiv:
            base_recherche = df if vue_admin else df_agent
            mask_indiv = base_recherche.apply(lambda x: x.astype(str).str.contains(recherche_indiv, case=False).any(), axis=1)
            df_recherche = base_recherche[mask_indiv]
            
            if not df_recherche.empty:
                options_dossiers = ["Sélectionnez un profil..."] + df_recherche.apply(lambda x: f"{x['identifiant']} - {x['nom']} {x['prenom']} (OV: {x['date_financement']})", axis=1).tolist()
                dossier_choisi = st.selectbox("🎯 Profils trouvés :", options_dossiers)

                if dossier_choisi != "Sélectionnez un profil...":
                    identifiant_choisi = dossier_choisi.split(" - ")[0]
                    session = get_session()
                    dos_db = session.query(Dossier).filter_by(identifiant=identifiant_choisi).first()
                    
                    if dos_db:
                        taux = (dos_db.montant_rembourse / dos_db.montant_pnr) if dos_db.montant_pnr > 0 else 0
                        st.markdown(f"""
                        <div class='profil-header'>
                            <h2 style='margin:0; color:#1f77b4;'>👤 {dos_db.nom} {dos_db.prenom}</h2>
                            <p style='margin:5px 0 0 0; font-size:16px;'><b>Identifiant:</b> {dos_db.identifiant} &nbsp;|&nbsp; <b>Projet:</b> {dos_db.activite} ({dos_db.commune})</p>
                            <p style='margin:10px 0 5px 0;'><b>Avancement du Remboursement : {taux*100:.1f}%</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(taux, 1.0))
                        
                        tel_brut = str(dos_db.telephone).strip()
                        if tel_brut and len(tel_brut) >= 9:
                            tel_clean = re.sub(r'\D', '', tel_brut)
                            tel_wa = '213' + tel_clean[1:] if tel_clean.startswith('0') else tel_clean
                            msg_wa = f"Bonjour {clean_pdf_text(dos_db.nom)}, c'est votre accompagnateur ANGEM."
                            st.markdown(f"""
                            <div class='action-btn-container'>
                                <a href='tel:{tel_clean}' class='btn-call' target='_blank'>📞 Appeler le {tel_brut}</a>
                                <a href='https://wa.me/{tel_wa}?text={msg_wa}' class='btn-wa' target='_blank'>💬 Envoyer un WhatsApp</a>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.caption("⚠️ Pas de numéro de téléphone valide enregistré pour les raccourcis d'appel.")

                        st.markdown("<br>", unsafe_allow_html=True)
                        col_gauche, col_droite = st.columns([1.3, 1])
                        
                        with col_gauche:
                            st.markdown("### 🗓️ Agenda : Planifier une visite")
                            col_d1, col_d2 = st.columns([2,1])
                            date_visite = col_d1.date_input("Date prévue :")
                            if col_d2.button("💾 Fixer la date"):
                                dos_db.prochaine_visite = date_visite.strftime("%d/%m/%Y")
                                session.commit()
                                st.success("Visite planifiée et ajoutée à votre agenda !")
                                st.rerun()
                                
                            if dos_db.prochaine_visite:
                                st.info(f"📍 Prochaine visite sur site programmée le : **{dos_db.prochaine_visite}**")
                                if st.button("❌ Annuler cette visite"):
                                    dos_db.prochaine_visite = ""
                                    session.commit()
                                    st.rerun()
                                    
                            st.markdown("---")
                            st.markdown("### 📝 Rapport de Visite")
                            nouvelle_note = st.text_area("Rédiger un nouveau compte-rendu :", placeholder="Observations suite à la visite sur site...")
                            if st.button("Enregistrer ce rapport"):
                                date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                                note_format = f"🔹 **[{date_str}]** {nouvelle_note}\n"
                                dos_db.historique_visites = note_format + (dos_db.historique_visites or "")
                                dos_db.prochaine_visite = "" 
                                session.commit()
                                st.success("Rapport ajouté à l'historique !")
                                st.rerun()
                            
                            st.markdown("**Historique des échanges :**")
                            st.markdown("<div style='background-color:#ffffff; border:1px solid #e1e5eb; padding:15px; border-radius:8px; height: 300px; overflow-y: auto; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);'>", unsafe_allow_html=True)
                            if dos_db.historique_visites: st.markdown(dos_db.historique_visites.replace('\n', '  \n'))
                            else: st.markdown("<span style='color:#888;'>Aucun rapport enregistré.</span>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        with col_droite:
                            st.markdown("### 📎 Dossier Administratif")
                            pdf_bytes = generer_fiche_promoteur_pdf(dos_db)
                            st.download_button("📄 Éditer la Fiche PDF Officielle", data=pdf_bytes, file_name=f"Fiche_{dos_db.identifiant}.pdf", mime="application/pdf", use_container_width=True)
                            
                            st.markdown("---")
                            # --- UPLOAD CLOUD SUPABASE ---
                            with st.expander("☁️ 📸 Scanner vers le Cloud sécurisé"):
                                st.info("Vos photos seront sauvegardées à vie sur le serveur ANGEM.")
                                photo_camera = st.camera_input("Prise de vue", label_visibility="collapsed")
                                if photo_camera is not None:
                                    if st.button("☁️ Envoyer sur le Cloud", use_container_width=True):
                                        file_bytes = photo_camera.getvalue()
                                        nom_fichier = f"{dos_db.identifiant}_SCAN_{int(datetime.now().timestamp())}.jpg"
                                        try:
                                            supabase_client.storage.from_("scans_angem").upload(file=file_bytes, path=nom_fichier, file_options={"content-type": "image/jpeg"})
                                            dos_db.documents = (dos_db.documents or "") + nom_fichier + "|"
                                            session.commit()
                                            st.success("✅ Photo archivée sur le Cloud avec succès !")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erreur de connexion au Cloud : {e}")

                            with st.expander("☁️ 📁 Importer un document (PDF/Image)"):
                                nouveau_scan = st.file_uploader("Choisir un fichier", type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed")
                                if nouveau_scan is not None:
                                    if st.button("☁️ Envoyer le fichier sur le Cloud", use_container_width=True):
                                        file_bytes = nouveau_scan.getvalue()
                                        nom_safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', nouveau_scan.name)
                                        nom_fichier = f"{dos_db.identifiant}_{int(datetime.now().timestamp())}_{nom_safe}"
                                        try:
                                            supabase_client.storage.from_("scans_angem").upload(file=file_bytes, path=nom_fichier, file_options={"content-type": nouveau_scan.type})
                                            dos_db.documents = (dos_db.documents or "") + nom_fichier + "|"
                                            session.commit()
                                            st.success("✅ Fichier archivé sur le Cloud avec succès !")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erreur de connexion au Cloud : {e}")
                                    
                            st.markdown("**🗄️ Archives Cloud du Dossier :**")
                            if dos_db.documents:
                                docs_list = [d for d in dos_db.documents.split("|") if d]
                                if not docs_list:
                                    st.caption("Aucune pièce jointe.")
                                else:
                                    for doc in docs_list:
                                        # Récupération du lien public depuis Supabase
                                        public_url = supabase_client.storage.from_("scans_angem").get_public_url(doc)
                                        if doc.lower().endswith(('.png', '.jpg', '.jpeg')):
                                            st.image(public_url, caption=doc, use_container_width=True)
                                        else:
                                            st.markdown(f"<a href='{public_url}' class='doc-link' target='_blank'>📥 Consulter le document PDF</a>", unsafe_allow_html=True)
                            else: st.caption("Aucune pièce jointe.")
                            
                    session.close()
            else:
                st.warning("⚠️ Aucun promoteur ne correspond à cette recherche.")
        st.markdown("</div>", unsafe_allow_html=True)

    if tab_orphan is not None:
        with tab_orphan:
            agent_daira = st.session_state.user.get('daira', '')
            if not agent_daira:
                st.warning("⚠️ L'administrateur ne vous a pas encore assigné à une Cellule d'Accompagnement (Daïra). Veuillez le contacter pour qu'il mette à jour votre profil.")
            else:
                st.info(f"💡 Voici la liste des dossiers importés qui n'ont pas encore d'Accompagnateur et qui se trouvent dans les communes de la **Daïra de {agent_daira}**. Cochez ceux qui vous appartiennent pour les récupérer dans votre liste !")
                
                mask_vide = (df['gestionnaire'].astype(str).str.strip() == "")
                mask_cellule = df['daira'].str.contains(agent_daira, case=False, na=False) | df['commune'].str.contains(agent_daira, case=False, na=False)
                df_orphans = df[mask_vide & mask_cellule].copy()
                
                if df_orphans.empty:
                    st.success(f"🎉 Bonne nouvelle ! Il n'y a aucun dossier orphelin dans la Cellule de {agent_daira} pour le moment.")
                else:
                    df_orphans["C'est mon dossier !"] = False
                    edited_orphans = st.data_editor(
                        df_orphans,
                        column_config={
                            "C'est mon dossier !": st.column_config.CheckboxColumn("S'attribuer", default=False),
                            "id": None, "documents": None, "historique_visites": None, "Alerte": None, "prochaine_visite": None
                        },
                        disabled=["identifiant", "nom", "prenom", "commune", "activite", "date_financement", "montant_pnr"],
                        hide_index=True,
                        use_container_width=True
                    )
                    ids_a_recuperer = edited_orphans[edited_orphans["C'est mon dossier !"] == True]['id'].tolist()
                    
                    if st.button(f"📥 Récupérer ces {len(ids_a_recuperer)} dossier(s) dans mon espace", type="primary", disabled=(len(ids_a_recuperer)==0)):
                        session = get_session()
                        nom_agent_connecte = st.session_state.user['nom']
                        try:
                            for cid in ids_a_recuperer:
                                dos = session.query(Dossier).get(cid)
                                if dos: dos.gestionnaire = nom_agent_connecte
                            session.commit()
                            st.success(f"✅ Félicitations ! {len(ids_a_recuperer)} dossier(s) ajouté(s) à votre espace personnel.")
                            st.rerun()
                        except Exception as e:
                            session.rollback(); st.error(f"Erreur : {e}")
                        finally:
                            session.close()

def page_import():
    st.title("📥 Intégration des Données")
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.info("L'outil de synchronisation met à jour les montants et crée les nouveaux financements automatiquement (Anti-Doublons activé).")
    uploaded_file = st.file_uploader("📂 Glissez votre fichier Excel de la Banque ou du Recouvrement", type=['xlsx', 'xls', 'csv'])
    if uploaded_file and st.button("🚀 Lancer l'Intégration Globale", type="primary"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
            agents_db = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_noms = [a.nom for a in agents_db]

            with st.status("Analyse et fusion en cours...", expanded=True) as status:
                count_add, count_upd = 0, 0
                for s_name, df_raw in xl.items():
                    df_raw = df_raw.fillna('')
                    header_idx = -1
                    for i in range(min(30, len(df_raw))):
                        row_cl = [clean_header(str(x)) for x in df_raw.iloc[i].values]
                        score = sum([1 for k in ["IDENTIFIANT", "CNI", "REF", "NOM", "GEST"] if k in row_cl])
                        if score >= 2: header_idx = i; break
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
                            if pd.isna(valeur_brute) or str(valeur_brute).strip() == "" or str(valeur_brute).strip().upper() == "NAN": continue 
                            if db_f in COLONNES_ARGENT: data[db_f] = clean_money(valeur_brute)
                            elif db_f == 'identifiant': data[db_f] = clean_identifiant(valeur_brute)
                            elif db_f == 'gestionnaire': data[db_f] = trouver_agent_intelligent(valeur_brute, agents_noms)
                            else: data[db_f] = str(valeur_brute).strip().upper()

                        ident = data.get('identifiant', '')
                        date_fin = data.get('date_financement', '')
                        if not ident: continue

                        exist = session.query(Dossier).filter_by(identifiant=ident, date_financement=date_fin).first()
                        if not exist and date_fin != "":
                            exist_empty = session.query(Dossier).filter_by(identifiant=ident, date_financement='').first()
                            if exist_empty: exist = exist_empty

                        if exist:
                            for k, v in data.items(): setattr(exist, k, v)
                            count_upd += 1
                        else:
                            session.add(Dossier(**data))
                            count_add += 1
                session.commit()
                status.update(label=f"Traitement terminé : {count_add} nouveaux dossiers créés, {count_upd} dossiers mis à jour.", state="complete")
            st.balloons()
        except Exception as e: session.rollback(); st.error(f"Erreur d'importation : {e}")
        finally: session.close()
    st.markdown("</div>", unsafe_allow_html=True)

def page_admin():
    st.title("📊 Espace Direction (Admin)")
    tab1, tab2, tab3 = st.tabs(["📈 Tableau de Bord & Bilans", "🔐 Gestion des Équipes", "⚙️ Maintenance Serveur"])

    with tab1:
        try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
        except: df = pd.DataFrame()
        
        if df.empty: st.warning("La base de dossiers est vide.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📌 Total Dossiers", len(df))
            c2.metric("💰 Crédit PNR Engagé", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
            c3.metric("📈 Recouvrement", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA")
            c4.metric("🚨 Reste à Recouvrer", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", delta_color="inverse")
            
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#2c3e50;'>🗺️ Cartographie des Dossiers & Contentieux</h4>", unsafe_allow_html=True)
            df_map = df.copy()
            df_map['lat'] = df_map['commune'].apply(lambda x: get_lat_lon(x)[0])
            df_map['lon'] = df_map['commune'].apply(lambda x: get_lat_lon(x)[1])
            df_map_grouped = df_map.groupby(['commune', 'lat', 'lon']).size().reset_index(name='Total Dossiers')
            df_retards = df_map[df_map.apply(calculer_alerte_bool, axis=1)]
            retards_counts = df_retards.groupby('commune').size().reset_index(name='Dossiers en Retard')
            df_map_grouped = df_map_grouped.merge(retards_counts, on='commune', how='left').fillna(0)
            
            fig_map = px.scatter_mapbox(
                df_map_grouped, lat="lat", lon="lon", hover_name="commune", 
                hover_data=["Total Dossiers", "Dossiers en Retard"],
                size="Total Dossiers", color="Dossiers en Retard",
                color_continuous_scale="Reds", size_max=40, zoom=9,
                mapbox_style="carto-positron"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            col_l, col_r = st.columns(2)
            with col_l:
                if 'statut_dossier' in df.columns: st.plotly_chart(px.pie(df, names='statut_dossier', title="Le Pipeline (Statuts)", hole=0.3), use_container_width=True)
                if 'banque_nom' in df.columns: st.plotly_chart(px.bar(df[df['banque_nom'] != '']['banque_nom'].value_counts().reset_index(), x='banque_nom', y='count', title="Répartition par Banque"), use_container_width=True)
            with col_r:
                if 'commune' in df.columns: st.plotly_chart(px.bar(df[df['commune'] != '']['commune'].value_counts().reset_index(), x='count', y='commune', orientation='h', title="Top 10 des Communes").update_yaxes(categoryorder='total ascending'), use_container_width=True)
                st.plotly_chart(px.bar(df[df['gestionnaire'] != '']['gestionnaire'].value_counts().reset_index(), x='gestionnaire', y='count', title="Charge par Accompagnateur"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#2c3e50;'>📥 Générateur de Rapports (PDF/Excel)</h4>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                pdf_bilan = generer_bilan_global_pdf(df)
                st.download_button("📊 Bilan Global de l'Antenne (PDF)", data=pdf_bilan, file_name="Bilan_Global.pdf", mime="application/pdf", use_container_width=True)
                pdf_creances = generer_creances_pdf(df)
                st.download_button("🔴 Exporter la Liste des Contentieux (PDF)", data=pdf_creances, file_name="Liste_Rouge.pdf", mime="application/pdf", use_container_width=True)
            with col_b2:
                pdf_analytique = generer_analytique_pdf(df)
                st.download_button("🗺️ Bilan Analytique par Zone (PDF)", data=pdf_analytique, file_name="Bilan_Analytique.pdf", mime="application/pdf", use_container_width=True)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.drop(columns=['id', 'documents', 'historique_visites'], errors='ignore').to_excel(writer, index=False, sheet_name='Base_ANGEM')
                st.download_button("🟢 Sauvegarde Complète (Excel)", data=buffer.getvalue(), file_name="Base_ANGEM.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            st.markdown("---")
            st.markdown("<b>👨‍💼 Générer le Bilan de Performance d'un Agent :</b>", unsafe_allow_html=True)
            agents_dispo = [a for a in df['gestionnaire'].unique() if str(a).strip() != ""]
            agent_selectionne = st.selectbox("Sélectionner l'agent", agents_dispo, label_visibility="collapsed")
            if agent_selectionne:
                pdf_agent = generer_bilan_agent_pdf(df, agent_selectionne)
                st.download_button(f"📄 Télécharger le bilan de {agent_selectionne}", data=pdf_agent, file_name=f"Bilan_Agent_{agent_selectionne}.pdf", mime="application/pdf")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.markdown("### 🔄 Assigner un Accompagnateur à une Cellule")
        st.info("Utilisez ces deux menus déroulants pour affecter facilement un agent à sa zone.")
        
        session = get_session()
        try:
            utilisateurs_agents = session.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()
            noms_agents_form = [a.nom for a in utilisateurs_agents]
        except:
            noms_agents_form = []
            
        if noms_agents_form:
            with st.form("affectation_rapide"):
                col_a, col_d = st.columns(2)
                agent_a_modifier = col_a.selectbox("👤 Choisir l'accompagnateur :", noms_agents_form)
                nouvelle_daira = col_d.selectbox("📍 Choisir sa Daïra :", LISTE_DAIRAS)
                submit_affectation = st.form_submit_button("✅ Valider l'affectation", type="primary")
                
                if submit_affectation:
                    agent_db = session.query(UtilisateurAuth).filter_by(nom=agent_a_modifier).first()
                    if agent_db:
                        agent_db.daira = nouvelle_daira
                        session.commit()
                        st.success(f"L'agent {agent_a_modifier} est maintenant affecté à la Cellule de {nouvelle_daira} !")
                        st.rerun()
        session.close()

        st.markdown("---")
        st.markdown("### 🔑 Mots de passe et Recrutement")
        try: df_users = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
        except: df_users = pd.DataFrame()
            
        if not df_users.empty:
            edited_users = st.data_editor(
                df_users, use_container_width=True, hide_index=True,
                column_config={
                    "id": None, 
                    "identifiant": st.column_config.TextColumn("Identifiant", disabled=True), 
                    "nom": st.column_config.TextColumn("Nom de l'Accompagnateur", disabled=True), 
                    "daira": st.column_config.TextColumn("Cellule actuelle", disabled=True),
                    "mot_de_passe": st.column_config.TextColumn("Mot de passe")
                }
            )
            if st.button("💾 Sauvegarder les mots de passe", type="secondary"):
                session = get_session()
                try:
                    for _, row in edited_users.iterrows():
                        user_db = session.query(UtilisateurAuth).get(row['id'])
                        if user_db: user_db.mot_de_passe = row['mot_de_passe']
                    session.commit()
                    st.success("✅ Mots de passe sécurisés avec succès !")
                except Exception as e: session.rollback(); st.error(f"Erreur : {e}")
                finally: session.close()
                
        st.markdown("---")
        st.markdown("#### ➕ Recruter un nouvel agent")
        with st.form("ajout_agent"):
            c1, c2, c3 = st.columns([1, 1.5, 1])
            new_id = c1.text_input("Identifiant (ex: benaissa)")
            new_nom = c2.text_input("Nom Complet (ex: BENAISSA Ahmed)")
            new_daira = c3.selectbox("Cellule", LISTE_DAIRAS)
            submit = st.form_submit_button("Créer le compte")
            if submit and new_id and new_nom:
                session = get_session()
                if not session.query(UtilisateurAuth).filter_by(identifiant=new_id.lower()).first():
                    session.add(UtilisateurAuth(identifiant=new_id.lower(), nom=new_nom.upper(), daira=new_daira, mot_de_passe="angem2026", role="agent"))
                    session.commit()
                    st.success(f"Agent {new_nom} configuré avec succès !")
                    st.rerun()
                else: st.error("Cet identifiant est déjà pris par un autre agent.")
                session.close()

        st.markdown("---")
        st.markdown("### 🗑️ Supprimer un compte en double")
        st.warning("Si vous supprimez un agent, ses dossiers ne seront pas effacés. Ils retourneront simplement dans la 'Corbeille' pour être récupérés.")
        
        session_suppr = get_session()
        try:
            agents_pour_suppr = session_suppr.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()
            options_suppression = [f"{a.nom} (ID: {a.identifiant})" for a in agents_pour_suppr]
        except:
            options_suppression = []
        finally:
            session_suppr.close()
            
        if options_suppression:
            with st.form("suppression_agent"):
                agent_a_effacer = st.selectbox("Sélectionnez le compte à supprimer :", options_suppression)
                btn_suppr = st.form_submit_button("🗑️ Supprimer définitivement")
                if btn_suppr and agent_a_effacer:
                    id_to_delete = agent_a_effacer.split("(ID: ")[1].replace(")", "")
                    sess_del = get_session()
                    sess_del.query(UtilisateurAuth).filter_by(identifiant=id_to_delete).delete()
                    sess_del.commit()
                    sess_del.close()
                    st.success("✅ L'agent a été supprimé de la liste !")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.markdown("### 🧹 Optimisation de la base")
        st.info("Utilisez cette fonction si vous pensez avoir importé le même fichier plusieurs fois par erreur. Cela garde les doubles financements intacts.")
        if st.button("🧼 Lancer l'Algorithme Anti-Doublons"):
            try:
                df_dup = pd.read_sql_query("SELECT id, identifiant, date_financement FROM dossiers", con=engine)
                duplicates = df_dup[df_dup.duplicated(subset=['identifiant', 'date_financement'], keep='first')]
                ids_to_delete = duplicates['id'].tolist()
                
                if ids_to_delete:
                    session = get_session()
                    session.query(Dossier).filter(Dossier.id.in_(ids_to_delete)).delete(synchronize_session=False)
                    session.commit()
                    session.close()
                    st.success(f"✅ Opération réussie : {len(ids_to_delete)} doublons strict effacés !")
                    st.rerun()
                else: st.success("Parfait, la base est parfaitement propre !")
            except Exception as e: st.error(f"Erreur : {e}")
        
        st.markdown("---")
        st.markdown("### 🧨 Remise à Zéro")
        st.error("Action irréversible : Supprime tous les promoteurs. Les comptes de tes agents seront conservés.")
        if st.button("🗑️ FORMARTER LA BASE DE DONNÉES", type="primary"):
            session = get_session()
            session.query(Dossier).delete(); session.commit(); session.close()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- DEMARRAGE DE L'APPLICATION ---
if st.session_state.user is None: login_page()
else:
    page = sidebar_menu()
    if page == "🗂️ Base Globale" and st.session_state.user['role'] == "admin": page_gestion(vue_admin=True)
    elif page == "🗂️ Mes Dossiers Promoteurs": page_gestion(vue_admin=False)
    elif page == "📥 Intégration Fichiers" and st.session_state.user['role'] == "admin": page_import()
    elif page == "📊 Espace Direction" and st.session_state.user['role'] == "admin": page_admin()
