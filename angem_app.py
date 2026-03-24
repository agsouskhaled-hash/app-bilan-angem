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
import urllib.parse
from supabase import create_client, Client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="ANGEM Workspace v21.1", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]

# --- CONNEXION CLOUD SUPABASE (STORAGE) ---
SUPABASE_URL = "https://greyjhgiytajxpvucbrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyZXlqaGdpeXRhanhwdnVjYnJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTU0MjksImV4cCI6MjA4NzU5MTQyOX0.jCNan1Y1hvfGog6Zcu8Rr8d5PkeFRFvipAGGB09ztxo"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DYNAMIQUE DES COULEURS (PROJET = Bleu, AMP = Vert) ---
if 'user' in st.session_state and st.session_state.user is not None:
    theme_color = "#1f77b4" if st.session_state.user.get('env') == "PNR PROJET" else "#28a745"
    theme_bg = "#f0f7fb" if st.session_state.user.get('env') == "PNR PROJET" else "#f0fbf2"
else:
    theme_color = "#2c3e50"
    theme_bg = "#f4f7f6"

# --- LE STYLE CSS MODERNE & RESPONSIVE (MOBILE) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {theme_bg}; }}
    div[data-testid="metric-container"] {{
        background-color: #ffffff; border: 1px solid #e1e5eb; padding: 20px;
        border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        border-left: 6px solid {theme_color}; transition: transform 0.2s ease-in-out;
    }}
    div[data-testid="metric-container"]:hover {{ transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); }}
    .stButton>button {{ border-radius: 8px; font-weight: 600; transition: all 0.3s; border: none; }}
    .stButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
    .login-container {{
        background: #ffffff; padding: 40px; border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center;
        max-width: 450px; margin: 0 auto; border: 1px solid #f0f2f6; border-top: 6px solid {theme_color};
    }}
    .modern-card {{
        background-color: #ffffff; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); margin-top: 15px; margin-bottom: 15px;
        border: 1px solid #e1e5eb; border-top: 3px solid {theme_color};
    }}
    .profil-header {{
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); padding: 20px;
        border-radius: 10px; border-left: 6px solid {theme_color}; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .alerte-urgente {{
        background-color: #fff3f3; border-left: 6px solid #dc3545; padding: 15px 20px;
        border-radius: 8px; color: #b02a37; font-weight: bold; margin-bottom: 20px; font-size: 16px;
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4); }}
        70% {{ box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }}
    }}
    .action-btn-container {{ display: flex; gap: 10px; margin-top: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
    .btn-call {{ background-color: #007bff; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; flex: 1; min-width: 150px; transition: 0.3s; box-shadow: 0 2px 5px rgba(0,123,255,0.3); }}
    .btn-wa {{ background-color: #25D366; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; flex: 1; min-width: 150px; transition: 0.3s; box-shadow: 0 2px 5px rgba(37,211,102,0.3); }}
    .btn-maps {{ background-color: #ea4335; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; flex: 1; min-width: 150px; transition: 0.3s; box-shadow: 0 2px 5px rgba(234,67,53,0.3); }}
    .btn-call:hover, .btn-wa:hover, .btn-maps:hover {{ opacity: 0.8; color: white; transform: translateY(-2px); }}
    .doc-link {{ display: block; background-color: #f0f2f6; padding: 12px; border-radius: 8px; text-decoration: none; color: #1f77b4; font-weight: bold; margin-bottom: 8px; border: 1px solid #e1e5eb; transition: 0.2s;}}
    .doc-link:hover {{ background-color: #e1e5eb; color: #0d47a1; }}
    .search-title {{ color: {theme_color}; font-weight: bold; font-size: 24px; margin-bottom: 10px; }}
    .compteur-orphelins {{ font-size: 40px; font-weight: bold; color: #dc3545; text-align: center; margin: 10px 0; }}
    
    /* RESPONSIVE DESIGN POUR LES TELEPHONES MOBILES */
    @media (max-width: 768px) {{
        .btn-call, .btn-wa, .btn-maps {{ min-width: 100%; margin-bottom: 5px; }}
        .profil-header {{ padding: 15px; }}
        .modern-card {{ padding: 15px; }}
        .action-btn-container {{ flex-direction: column; }}
    }}
</style>
""", unsafe_allow_html=True)

# --- CONNEXION BASE DE DONNÉES ---
Base = declarative_base()
engine = create_engine("postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require", echo=False)
Session = sessionmaker(bind=engine)

class Dossier(Base):
    __tablename__ = 'dossiers'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, index=True)
    type_dispositif = Column(String, default="PNR PROJET") 
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
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS type_dispositif VARCHAR DEFAULT 'PNR PROJET'"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS apport_personnel FLOAT DEFAULT 0.0"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS date_naissance VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS num_ordre_versement VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS debut_consommation VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS etat_dette VARCHAR DEFAULT ''"))
        conn.commit()
except: pass

def get_session(): return Session()

def init_db_users():
    session = get_session()
    admin = session.query(UtilisateurAuth).filter_by(identifiant="admin").first()
    if not admin:
        session.add(UtilisateurAuth(identifiant="admin", nom="Administrateur", mot_de_passe="angem", role="admin"))
    session.commit()
    session.close()

init_db_users()

LISTE_STATUTS = ["Phase dépôt du dossier", "En attente de la commission", "Accordé / En cours", "En phase d'exploitation", "Contentieux / Retard"]

def afficher_logo(largeur=250):
    try:
        with open("logo_angem.png", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            st.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="data:image/png;base64,{encoded_string}" width="{largeur}"></div>', unsafe_allow_html=True)
    except:
        st.markdown(f'<div style="text-align: center; color: {theme_color}; font-size: 24px; font-weight: bold; border: 2px solid {theme_color}; padding: 10px; border-radius: 10px; margin-bottom: 20px;">🔵 ANGEM Workspace</div>', unsafe_allow_html=True)

def clean_pdf_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')

# --- FONCTIONS PDF ---
def generer_fiche_promoteur_pdf(dos):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "DOSSIER OFFICIEL DU PROMOTEUR", ln=True, align='C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 1. IDENTIFICATION DU PROMOTEUR", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Identifiant : {clean_pdf_text(dos.identifiant)}", border='L')
    pdf.cell(95, 8, f" Accompagnateur : {clean_pdf_text(dos.gestionnaire)}", border='R', ln=True)
    pdf.cell(95, 8, f" Nom/Prenom : {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", border='L')
    pdf.cell(95, 8, f" Telephone : {clean_pdf_text(dos.telephone)}", border='R', ln=True)
    pdf.cell(0, 8, f" Date de naissance : {clean_pdf_text(dos.date_naissance)}", border='LR', ln=True)
    pdf.cell(0, 8, f" Adresse : {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)}", border='LRB', ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 2. PROJET & FINANCEMENT", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Dispositif : {clean_pdf_text(dos.type_dispositif)}", border='L')
    pdf.cell(95, 8, f" Statut : {clean_pdf_text(dos.statut_dossier)}", border='R', ln=True)
    pdf.cell(95, 8, f" Activite : {clean_pdf_text(dos.activite)}", border='L')
    pdf.cell(95, 8, f" Date de versement (OV) : {clean_pdf_text(dos.date_financement)}", border='R', ln=True)
    pdf.cell(95, 8, f" Num OV : {clean_pdf_text(dos.num_ordre_versement)}", border='L')
    pdf.cell(95, 8, f" Debut Consom. : {clean_pdf_text(dos.debut_consommation)}", border='R', ln=True)
    pdf.cell(63, 8, f" Credit PNR : {dos.montant_pnr:,.0f} DA", border='L')
    pdf.cell(63, 8, f" Apport : {dos.apport_personnel:,.0f} DA")
    pdf.cell(64, 8, f" Banque : {dos.credit_bancaire:,.0f} DA", border='R', ln=True)
    pdf.cell(0, 8, "", border='T', ln=True) 
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 3. ETAT DU RECOUVREMENT", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Montant Recouvre : {dos.montant_rembourse:,.0f} DA", border='L')
    pdf.cell(95, 8, f" Reste a Rembourser : {dos.reste_rembourser:,.0f} DA", border='R', ln=True)
    pdf.cell(95, 8, f" Echeances tombees : {clean_pdf_text(dos.nb_echeance_tombee)}", border='L')
    pdf.cell(95, 8, f" Etat : {clean_pdf_text(dos.etat_dette)}", border='R', ln=True)
    pdf.cell(0, 8, "", border='T', ln=True) 
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

def generer_rapport_global_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "ETAT GLOBAL DES DOSSIERS - ANGEM", ln=True, align='C')
    pdf.ln(5)
    total_pnr = df['montant_pnr'].astype(float).sum()
    total_remb = df['montant_rembourse'].astype(float).sum()
    total_reste = df['reste_rembourser'].astype(float).sum()
    df_projet = df[df['type_dispositif'] == 'PNR PROJET']
    df_amp = df[df['type_dispositif'] == 'PNR AMP']
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. VOLUME DES DOSSIERS", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Total Dossiers : {len(df)} (Projets: {len(df_projet)} | AMP: {len(df_amp)})", ln=True)
    pdf.cell(0, 8, f"Total Credit PNR Engage : {total_pnr:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"  -> PNR Projets : {df_projet['montant_pnr'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 8, f"  -> PNR AMP : {df_amp['montant_pnr'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Montant Recouvre : {total_remb:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Dette Globale (Reste a payer) : {total_reste:,.0f} DA", ln=True)
    pdf.ln(5)
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
    pdf.cell(0, 20, "EXTRACTION DES DOSSIERS EN SOUFFRANCE", ln=True, align='C')
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
        dispo = "AMP" if row['type_dispositif'] == "PNR AMP" else "PROJET"
        txt = f"[{dispo}] ID: {row['identifiant']} | {nom}... | Reste: {row['reste_rembourser']:,.0f} DA | Gest: {agent}"
        pdf.cell(0, 8, txt, ln=True, border='B')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

# --- UTILITAIRES DE NETTOYAGE ---
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
    if pd.isna(val) or str(val).strip() == '': return None # L'ANTI-ECRASEMENT : on renvoie None si c'est vide
    s = str(val).upper().replace('DA', '').replace(' ', '').replace(',', '.')
    s = re.sub(r'[^\d\.-]', '', s)
    try: return float(s)
    except: return None

def clean_identifiant(val):
    if pd.isna(val): return ""
    s = str(val).strip().upper()
    if 'E' in s: 
        try: s = f"{float(s):.0f}"
        except: pass
    if s.endswith('.0'): s = s[:-2]
    return s

# DICTIONNAIRE INTEGRAL POUR EXCEL
MAPPING_CONFIG = {
    'identifiant': ['IDENTIFIANT', 'CNI', 'NCINPC', 'CARTENAT'],
    'nom': ['NOM', 'NOMETPRENOM', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'date_naissance': ['DATEDENAISSANCE', 'DATENAISSANCE'],
    'adresse': ['ADRESSE', 'ADRESSEXACTE'],
    'telephone': ['TEL', 'TELEPHONE', 'MOB', 'MOBILE'],
    'commune': ['COMMUNE', 'APC'],
    'daira': ['DAIRA'],
    'activite': ['ACTIVITE', 'PROJET'],
    'secteur': ['SECTEURDACTIVITE', 'SECTEUR'],
    'gestionnaire': ['GEST', 'ACCOMPAGNATEUR', 'SUIVIPAR'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'num_ordre_versement': ['NUMOV', 'OV'],
    'date_financement': ['DATEOV', 'DATEDEVIREMENT', 'DATEVIREMENT', 'DATEDEFINANCEMENT'],
    'debut_consommation': ['DEBUTCONSOM', 'DEBUTCONSOMMATION'],
    'montant_pnr': ['PNR', 'MONTANTPNR29', 'MTDUPNR', 'MONTANT'],
    'apport_personnel': ['APPORT', 'APPORTPERSONNEL'], 
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
    'etat_dette': ['ETAT', 'ETATDETTE']
}
COLONNES_ARGENT = ['montant_pnr', 'montant_rembourse', 'reste_rembourser', 'apport_personnel']

def calculer_alerte_bool(row):
    ech = str(row.get('nb_echeance_tombee', '')).strip()
    if any(char.isdigit() for char in ech):
        num = int(re.search(r'\d+', ech).group())
        if num > 0: return True
    if row.get('statut_dossier') == "Contentieux / Retard" or row.get('etat_dette') == "CONTENTIEUX": return True
    return False

def get_badge(row):
    if calculer_alerte_bool(row): return "🔴 Retard"
    elif float(row.get('reste_rembourser', 0)) > 0: return "🟡 En cours"
    else: return "🟢 À jour"

if 'user' not in st.session_state: st.session_state.user = None

# --- ECRAN DE CONNEXION INTELLIGENT ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        afficher_logo(220)
        st.markdown("<h3 style='color: #2c3e50; margin-bottom: 25px;'>Portail Workspace ANGEM</h3>", unsafe_allow_html=True)
        
        session = get_session()
        try:
            users_db = session.query(UtilisateurAuth).order_by(UtilisateurAuth.nom).all()
            noms_disponibles = [u.nom for u in users_db]
        except: noms_disponibles = ["Administrateur"]
        session.close()

        nom_choisi = st.selectbox("👤 Profil Utilisateur", noms_disponibles)
        password = st.text_input("🔑 Mot de passe", type="password")
        
        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
        env_choisi = st.selectbox("🏢 Choisissez votre environnement de travail", ["PNR PROJET", "PNR AMP"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Entrer dans l'espace sécurisé", type="primary", use_container_width=True):
            session = get_session()
            user_db = session.query(UtilisateurAuth).filter_by(nom=nom_choisi).first()
            session.close()
            if user_db and user_db.mot_de_passe == password:
                st.session_state.user = {
                    "identifiant": user_db.identifiant, 
                    "nom": user_db.nom, 
                    "role": user_db.role, 
                    "daira": user_db.daira,
                    "env": env_choisi 
                }
                st.rerun()
            else: st.error("⚠️ Mot de passe incorrect.")
        st.markdown("</div>", unsafe_allow_html=True)

def sidebar_menu():
    afficher_logo(180)
    env = st.session_state.user.get('env')
    daira_info = f" ({st.session_state.user.get('daira')})" if st.session_state.user.get('daira') else ""
    
    st.sidebar.markdown(f"""
    <div style='text-align: center; padding: 15px; background: {theme_color}15; border: 1px solid {theme_color}40; border-radius: 8px; margin-bottom: 20px;'>
        <b style='color: #2c3e50; font-size:18px;'>👤 {st.session_state.user['nom']}</b><br>
        <small style='color: #555;'>📍 Cellule {daira_info}</small><br>
        <div style='margin-top:8px; display:inline-block; background:{theme_color}; color:white; padding:4px 10px; border-radius:15px; font-size:12px; font-weight:bold;'>
            🏢 {env}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    options = [
        f"🗂️ Espace de Travail ({env})", 
        "🗑️ Corbeille & Affectation"
    ]
    if st.session_state.user['role'] == "admin":
        options = [
            f"🗂️ Base Globale ({env})",
            "📊 Supervision Direction", 
            "⚙️ Intégration Fichiers"
        ]
        
    choix = st.sidebar.radio("Menu de Navigation", options, label_visibility="collapsed")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Changer d'environnement / Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    return choix

# --- AFFICHAGE DU PROFIL COMPLET ---
def afficher_profil_promoteur(dos_db, session):
    taux = (dos_db.montant_rembourse / dos_db.montant_pnr) if dos_db.montant_pnr > 0 else 0
    st.markdown(f"""
    <div class='profil-header'>
        <h2 style='margin:0; color:{theme_color};'>👤 {dos_db.nom} {dos_db.prenom}</h2>
        <p style='margin:5px 0 0 0; font-size:16px;'><b>ID:</b> {dos_db.identifiant}  |  <b>Projet:</b> {dos_db.activite} ({dos_db.commune})</p>
        <p style='margin:10px 0 5px 0;'><b>Remboursement ({dos_db.montant_rembourse:,.0f} / {dos_db.montant_pnr:,.0f} DA) : {taux*100:.1f}%</b></p>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(taux, 1.0))
    
    tel_brut = str(dos_db.telephone).strip()
    tel_clean = re.sub(r'\D', '', tel_brut) if tel_brut else ""
    tel_wa = '213' + tel_clean[1:] if tel_clean.startswith('0') else tel_clean
    msg_wa = f"Bonjour {clean_pdf_text(dos_db.nom)}, c'est votre accompagnateur ANGEM."
    
    adresse_complete = f"{dos_db.adresse} {dos_db.commune} Algerie"
    lien_maps = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(adresse_complete)}"

    st.markdown("<div class='action-btn-container'>", unsafe_allow_html=True)
    if tel_clean and len(tel_clean) >= 9:
        st.markdown(f"<a href='tel:{tel_clean}' class='btn-call' target='_blank'>📞 Appeler</a>", unsafe_allow_html=True)
        st.markdown(f"<a href='https://wa.me/{tel_wa}?text={urllib.parse.quote(msg_wa)}' class='btn-wa' target='_blank'>💬 WhatsApp</a>", unsafe_allow_html=True)
    st.markdown(f"<a href='{lien_maps}' class='btn-maps' target='_blank'>🗺️ Trouver sur Maps</a>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_gauche, col_droite = st.columns([1.3, 1])
    
    with col_gauche:
        st.markdown("### 🗓️ Planifier une visite")
        col_d1, col_d2 = st.columns([2,1])
        date_visite = col_d1.date_input("Date prévue :", key=f"date_{dos_db.id}")
        if col_d2.button("💾 Fixer la date", key=f"btn_date_{dos_db.id}"):
            dos_db.prochaine_visite = date_visite.strftime("%d/%m/%Y")
            session.commit()
            st.success("Visite planifiée !")
            st.rerun()
            
        if dos_db.prochaine_visite:
            st.info(f"📍 Prochaine visite prévue le : **{dos_db.prochaine_visite}**")
            if st.button("❌ Annuler cette visite", key=f"annul_{dos_db.id}"):
                dos_db.prochaine_visite = ""
                session.commit()
                st.rerun()
                
        st.markdown("---")
        st.markdown("### 📝 Rapport & Historique")
        nouvelle_note = st.text_area("Rédiger un compte-rendu :", placeholder="Observations...", key=f"note_{dos_db.id}")
        if st.button("Enregistrer le rapport", key=f"btn_note_{dos_db.id}"):
            date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
            note_format = f"🔹 **[{date_str}]** {nouvelle_note}\n"
            dos_db.historique_visites = note_format + (dos_db.historique_visites or "")
            dos_db.prochaine_visite = "" 
            session.commit()
            st.success("Rapport ajouté !")
            st.rerun()
        
        st.markdown(f"<div style='background-color:#ffffff; border:1px solid #e1e5eb; padding:15px; border-radius:8px; height: 300px; overflow-y: auto; border-left: 4px solid {theme_color};'>", unsafe_allow_html=True)
        if dos_db.historique_visites: st.markdown(dos_db.historique_visites.replace('\n', '  \n'))
        else: st.markdown("<span style='color:#888;'>Aucun rapport enregistré.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_droite:
        st.markdown("### 📎 Dossier & Pièces jointes")
        pdf_bytes = generer_fiche_promoteur_pdf(dos_db)
        st.download_button("📄 Exporter la Fiche (PDF)", data=pdf_bytes, file_name=f"Dossier_{dos_db.identifiant}.pdf", mime="application/pdf", use_container_width=True, key=f"pdf_{dos_db.id}")
        
        st.markdown("---")
        with st.expander("☁️ 📸 Scanner un document avec la caméra"):
            photo_camera = st.camera_input("Prise de vue", label_visibility="collapsed", key=f"cam_{dos_db.id}")
            if photo_camera is not None:
                if st.button("☁️ Archiver sur le Cloud", use_container_width=True, key=f"up_cam_{dos_db.id}"):
                    file_bytes = photo_camera.getvalue()
                    nom_fichier = f"{dos_db.identifiant}_SCAN_{int(datetime.now().timestamp())}.jpg"
                    try:
                        supabase_client.storage.from_("scans_angem").upload(file=file_bytes, path=nom_fichier, file_options={"content-type": "image/jpeg"})
                        dos_db.documents = (dos_db.documents or "") + nom_fichier + "|"
                        session.commit()
                        st.success("✅ Archivé sur le Cloud !")
                        st.rerun()
                    except Exception as e: st.error(f"Erreur Cloud : {e}")

        with st.expander("☁️ 📁 Joindre un fichier (PDF/Image)"):
            nouveau_scan = st.file_uploader("Choisir un fichier", type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed", key=f"file_{dos_db.id}")
            if nouveau_scan is not None:
                if st.button("☁️ Archiver sur le Cloud", use_container_width=True, key=f"up_file_{dos_db.id}"):
                    file_bytes = nouveau_scan.getvalue()
                    nom_safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', nouveau_scan.name)
                    nom_fichier = f"{dos_db.identifiant}_{int(datetime.now().timestamp())}_{nom_safe}"
                    try:
                        supabase_client.storage.from_("scans_angem").upload(file=file_bytes, path=nom_fichier, file_options={"content-type": nouveau_scan.type})
                        dos_db.documents = (dos_db.documents or "") + nom_fichier + "|"
                        session.commit()
                        st.success("✅ Archivé sur le Cloud !")
                        st.rerun()
                    except Exception as e: st.error(f"Erreur Cloud : {e}")
                
        st.markdown("**🗄️ Base Documentaire du Promoteur :**")
        if dos_db.documents:
            docs_list = [d for d in dos_db.documents.split("|") if d]
            if not docs_list: st.caption("Aucune pièce jointe.")
            else:
                for doc in docs_list:
                    public_url = supabase_client.storage.from_("scans_angem").get_public_url(doc)
                    if doc.lower().endswith(('.png', '.jpg', '.jpeg')):
                        st.image(public_url, caption=doc, use_container_width=True)
                    else:
                        st.markdown(f"<a href='{public_url}' class='doc-link' target='_blank'>📥 Consulter le document</a>", unsafe_allow_html=True)
        else: st.caption("Aucune pièce jointe.")
    
    # --- NOUVEAU : LE BOUTON POUR SUPPRIMER LES DOUBLONS ---
    st.markdown("---")
    with st.expander("⚠️ Options Avancées (Suppression de doublon)"):
        st.warning("Attention : Si vous cliquez ci-dessous, ce dossier (et toutes ses informations) sera définitivement effacé de la base de données de l'ANGEM.")
        if st.button("🗑️ Supprimer définitivement ce dossier", key=f"del_{dos_db.id}", type="primary"):
            session.delete(dos_db)
            session.commit()
            st.success("Dossier supprimé avec succès. Mise à jour de la liste...")
            st.rerun()

# --- PAGES DE L'APPLICATION ---
def page_gestion(vue_admin=False):
    env_actif = st.session_state.user.get('env')
    agent_daira = st.session_state.user.get('daira', '')
    
    try: df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{env_actif}' ORDER BY id DESC", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info(f"📌 Aucun dossier dans l'environnement {env_actif}.")
        return

    # ALERTE ROUGE ORPHELINS (Seulement pour les agents)
    if not vue_admin and agent_daira:
        mask_vide = (df['gestionnaire'].astype(str).str.strip() == "")
        mask_cellule = df['daira'].str.contains(agent_daira, case=False, na=False) | df['commune'].str.contains(agent_daira, case=False, na=False)
        nb_orphelins = len(df[mask_vide & mask_cellule])
        
        if nb_orphelins > 0:
            st.markdown(f"<div class='alerte-urgente'>🚨 URGENT : Il y a {nb_orphelins} dossier(s) non attribué(s) dans la Daïra de {agent_daira} ! Allez dans la 'Corbeille & Affectation' pour récupérer vos promoteurs.</div>", unsafe_allow_html=True)

    # BARRE DE RECHERCHE RAPIDE TOUT EN HAUT
    st.markdown("<div class='modern-card' style='padding-top:15px; padding-bottom: 15px;'>", unsafe_allow_html=True)
    st.markdown(f"<div class='search-title'>🔍 Moteur de recherche rapide ({env_actif})</div>", unsafe_allow_html=True)
    search_global = st.text_input("Tapez le Nom, l'Identifiant ou le Téléphone du promoteur et appuyez sur Entrée...", key="search_bar")
    st.markdown("</div>", unsafe_allow_html=True)

    if search_global:
        mask_search = df.apply(lambda x: x.astype(str).str.contains(search_global, case=False).any(), axis=1)
        df_trouve = df[mask_search]
        
        if not df_trouve.empty:
            st.success(f"🎯 {len(df_trouve)} résultat(s) trouvé(s)")
            for _, row in df_trouve.iterrows():
                with st.expander(f"📁 Ouvrir le dossier de : {row['nom']} {row['prenom']} (ID: {row['identifiant']})", expanded=(len(df_trouve)==1)):
                    session = get_session()
                    dos_db = session.query(Dossier).get(row['id'])
                    if dos_db: afficher_profil_promoteur(dos_db, session)
                    session.close()
            st.markdown("---")
        else:
            st.warning("⚠️ Aucun promoteur trouvé pour cette recherche.")

    if not vue_admin:
        nom_agent = str(st.session_state.user['nom']).upper()
        mots_agent = set([m for m in re.split(r'\W+', nom_agent) if len(m) >= 3])
        def match_agent(val):
            val_clean = str(val).upper()
            if not val_clean: return False
            if val_clean == nom_agent or nom_agent in val_clean or val_clean in nom_agent: return True
            if mots_agent.intersection(set([m for m in re.split(r'\W+', val_clean) if len(m) >= 3])): return True
            return False
        df = df[df['gestionnaire'].apply(match_agent)]

    df['Badge'] = df.apply(get_badge, axis=1)

    df_visites = df[df['prochaine_visite'].str.strip() != ''].copy()
    if not df_visites.empty:
        with st.expander(f"🗓️ Mon Agenda : {len(df_visites)} visite(s) programmée(s)", expanded=True):
            st.dataframe(df_visites[['identifiant', 'nom', 'commune', 'prochaine_visite', 'telephone']], hide_index=True, use_container_width=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    col_t, col_f = st.columns([1, 2])
    col_t.markdown(f"#### 🗂️ Pipeline {env_actif}")
    filtre_badge = col_f.radio("Filtrer la liste :", ["Tous", "🔴 Retard", "🟡 En cours", "🟢 À jour"], horizontal=True, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    df_filtered = df.copy()
    if filtre_badge != "Tous":
        df_filtered = df_filtered[df_filtered['Badge'].str.contains(filtre_badge.split(" ")[0])]

    try:
        df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=engine)
        liste_agents = [""] + sorted(list(set(df_agents['nom'].tolist() + df['gestionnaire'].unique().tolist())))
    except: liste_agents = [""]

    st.caption(f"Affichage de {len(df_filtered)} dossiers.")

    edited_df = st.data_editor(
        df_filtered, use_container_width=True, hide_index=True, height=500,
        column_config={
            "id": None, "documents": None, "historique_visites": None, "prochaine_visite": None, "type_dispositif": None,
            "Badge": st.column_config.TextColumn("État", disabled=True),
            "identifiant": st.column_config.TextColumn("Identifiant", disabled=True),
            "nom": "Nom Promoteur",
            "statut_dossier": st.column_config.SelectboxColumn("Étape du dossier", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=not vue_admin),
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
            st.toast("✅ Base mise à jour !")
            st.rerun()
        except Exception as e: session.rollback(); st.error(e)
        finally: session.close()

    # --- LE RETOUR DE LA RUBRIQUE FIXE SOUS LE TABLEAU ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: {theme_color}; border-bottom: 2px solid {theme_color}; padding-bottom: 5px;'>📂 Profil Détaillé du Promoteur</h3>", unsafe_allow_html=True)
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    
    options_noms = ["Sélectionnez un profil..."] + df_filtered.apply(lambda x: f"{x['identifiant']} - {x['nom']} {x['prenom']}", axis=1).tolist()
    profil_choisi = st.selectbox("Choisissez un promoteur affiché dans le tableau ci-dessus :", options_noms)
    
    if profil_choisi != "Sélectionnez un profil...":
        id_choisi = profil_choisi.split(" - ")[0]
        session = get_session()
        dos_db = session.query(Dossier).filter_by(identifiant=id_choisi).first()
        if dos_db:
            afficher_profil_promoteur(dos_db, session)
        session.close()
    st.markdown("</div>", unsafe_allow_html=True)


def page_corbeille():
    env_actif = st.session_state.user.get('env')
    st.title(f"🗑️ Bourse aux dossiers ({env_actif})")
    agent_daira = st.session_state.user.get('daira', '')
    
    if not agent_daira:
        st.warning("⚠️ Vous n'avez pas de Daïra assignée. Demandez à l'administrateur.")
        return

    try: df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{env_actif}'", con=engine).fillna('')
    except: return

    mask_vide = (df['gestionnaire'].astype(str).str.strip() == "")
    mask_cellule = df['daira'].str.contains(agent_daira, case=False, na=False) | df['commune'].str.contains(agent_daira, case=False, na=False)
    df_orphans = df[mask_vide & mask_cellule].copy()
    
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #2c3e50;'>Dossiers en attente dans la Daïra de {agent_daira}</h3>", unsafe_allow_html=True)
    st.markdown(f"<div class='compteur-orphelins'>{len(df_orphans)}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if df_orphans.empty:
        st.success("🎉 Félicitations, tous les dossiers de votre Daïra ont un accompagnateur !")
    else:
        st.info("Cochez les dossiers qui vous appartiennent et validez en bas de la page.")
        df_orphans["C'est mon dossier !"] = False
        edited_orphans = st.data_editor(
            df_orphans, hide_index=True, use_container_width=True, height=400,
            column_config={
                "C'est mon dossier !": st.column_config.CheckboxColumn("S'attribuer", default=False),
                "id": None, "documents": None, "historique_visites": None, "prochaine_visite": None, "type_dispositif": None
            },
            disabled=["identifiant", "nom", "commune", "montant_pnr", "activite"]
        )
        
        ids_recup = edited_orphans[edited_orphans["C'est mon dossier !"] == True]['id'].tolist()
        if st.button(f"📥 Confirmer et récupérer ces {len(ids_recup)} dossier(s)", type="primary", disabled=(len(ids_recup)==0)):
            session = get_session()
            nom_agent = st.session_state.user['nom']
            try:
                for cid in ids_recup:
                    dos = session.query(Dossier).get(cid)
                    if dos: dos.gestionnaire = nom_agent
                session.commit()
                st.success("✅ Dossiers récupérés avec succès !")
                st.rerun()
            except Exception as e: session.rollback()
            finally: session.close()

def page_supervision():
    env_actif = st.session_state.user.get('env')
    st.title("📊 Supervision Direction & Extractions")
    try: df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{env_actif}'", con=engine).fillna('')
    except: df = pd.DataFrame()
    
    if df.empty: st.warning("La base est vide pour cet environnement."); return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📌 Total Dossiers", len(df))
    c2.metric("💰 Crédit PNR", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
    c3.metric("📈 Recouvrement", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA")
    c4.metric("🚨 Reste à Recouvrer", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", delta_color="inverse")
    
    # RADAR ADMIN
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("#### 👁️ Radar des Dossiers Orphelins")
    mask_vide_admin = (df['gestionnaire'].astype(str).str.strip() == "")
    df_orphelins_admin = df[mask_vide_admin]
    
    if df_orphelins_admin.empty:
        st.success("✅ Tous les dossiers de cet environnement ont été affectés à un agent.")
    else:
        st.warning(f"⚠️ Il reste **{len(df_orphelins_admin)} dossiers** sans accompagnateur.")
        orphelins_par_commune = df_orphelins_admin.groupby('commune').size().reset_index(name='Dossiers Orphelins')
        orphelins_par_commune = orphelins_par_commune.sort_values(by='Dossiers Orphelins', ascending=False)
        st.dataframe(orphelins_par_commune, hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("#### 📥 Extractions Officielles (PDF / Excel)")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        pdf_global = generer_rapport_global_pdf(df)
        st.download_button("📊 État Global des Dossiers (PDF)", data=pdf_global, file_name="Etat_Global.pdf", mime="application/pdf", use_container_width=True)
        pdf_creances = generer_creances_pdf(df)
        st.download_button("🔴 Extraction des Contentieux (PDF)", data=pdf_creances, file_name="Contentieux.pdf", mime="application/pdf", use_container_width=True)
    with col_b2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.drop(columns=['id', 'documents', 'historique_visites', 'prochaine_visite'], errors='ignore').to_excel(writer, index=False, sheet_name='Dossiers')
        st.download_button("🟢 Sauvegarde Complète (Excel)", data=buffer.getvalue(), file_name="Base_Dossiers.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def page_integration_admin():
    env_actif = st.session_state.user.get('env')
    st.title("⚙️ Équipes & Intégration Sécurisée")
    tab1, tab2 = st.tabs(["📥 Importateur Intelligent (Anti-Écrasement)", "🔐 Gestion des Équipes"])
    
    with tab1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("💡 **NOUVEAU :** L'importateur est maintenant un *Puzzle*. Si vous importez un deuxième fichier, il complétera les dossiers sans jamais effacer les anciennes cases qui contiennent déjà des informations.")
        st.caption("L'importation se fera dans : **" + env_actif + "** (Filtre > 40 000 DA actif)")
        
        uploaded_file = st.file_uploader(f"📂 Glissez votre fichier (.xlsx ou .csv)", type=['xlsx', 'xls', 'csv'])
        
        if uploaded_file and st.button("🚀 Démarrer l'Importation Intelligente", type="primary"):
            session = get_session()
            try:
                if uploaded_file.name.lower().endswith('.csv'):
                    try: df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', dtype=str)
                    except Exception: df_raw = pd.read_csv(uploaded_file, sep=';', encoding='latin1', dtype=str)
                    xl = {'Fichier CSV': df_raw}
                else:
                    xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
                
                agents_db = session.query(UtilisateurAuth).filter_by(role='agent').all()
                agents_noms = [a.nom for a in agents_db]

                with st.status(f"Importation en cours vers {env_actif}...", expanded=True) as status:
                    count_add, count_upd, count_ignored = 0, 0, 0
                    batch_size = 50 
                    
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    
                    with session.no_autoflush:
                        for s_name, df_raw in xl.items():
                            df_raw = df_raw.fillna('')
                            
                            if uploaded_file.name.lower().endswith('.csv') and 'Identifiant' in df_raw.columns:
                                df = df_raw
                            else:
                                header_idx = -1
                                for i in range(min(30, len(df_raw))):
                                    row_cl = [clean_header(str(x)) for x in df_raw.iloc[i].values]
                                    if sum([1 for k in ["IDENTIFIANT", "CNI", "NOM", "GEST"] if k in row_cl]) >= 2:
                                        header_idx = i; break
                                if header_idx == -1: continue
                                
                                df = df_raw.iloc[header_idx:].copy()
                                df.columns = df.iloc[0].astype(str).tolist()
                                df = df.iloc[1:].reset_index(drop=True)
                                
                            df_cols = [clean_header(c) for c in df.columns]
                            col_map = {db_f: df.columns[df_cols.index(clean_header(v))] for db_f, variants in MAPPING_CONFIG.items() for v in variants if clean_header(v) in df_cols}
                            
                            total_rows = len(df)
                            
                            for idx, row in df.iterrows():
                                # MISE A JOUR BARRE DE PROGRESSION
                                if idx % max(1, (total_rows // 100)) == 0 or idx == total_rows - 1:
                                    prog_val = min(1.0, (idx + 1) / total_rows)
                                    progress_bar.progress(prog_val)
                                    progress_text.markdown(f"**Analyse en cours... {int(prog_val * 100)}%**")

                                data = {}
                                for db_f, xl_c in col_map.items():
                                    val = row[xl_c]
                                    if pd.isna(val) or str(val).strip() in ["", "NAN"]: continue 
                                    if db_f in COLONNES_ARGENT: 
                                        amt = clean_money(val)
                                        if amt is not None: data[db_f] = amt
                                    elif db_f == 'identifiant': data[db_f] = clean_identifiant(val)
                                    elif db_f == 'gestionnaire': data[db_f] = trouver_agent_intelligent(val, agents_noms)
                                    else: data[db_f] = str(val).strip().upper()

                                ident = data.get('identifiant', '')
                                date_fin = data.get('date_financement', '')
                                if not ident: continue

                                exist = session.query(Dossier).filter_by(identifiant=ident, date_financement=date_fin).first()
                                if not exist and date_fin != "": exist = session.query(Dossier).filter_by(identifiant=ident, date_financement='').first()

                                # FILTRE 40 000 DA
                                if 'montant_pnr' in data and 0 < data['montant_pnr'] <= 40000:
                                    count_ignored += 1
                                    continue

                                data['type_dispositif'] = env_actif

                                # LOGIQUE ANTI-ECRASEMENT (LE PUZZLE)
                                if exist:
                                    for k, v in data.items(): 
                                        if isinstance(v, str):
                                            if v.strip() != "":
                                                setattr(exist, k, v)
                                        else:
                                            setattr(exist, k, v)
                                    count_upd += 1
                                else:
                                    session.add(Dossier(**data))
                                    count_add += 1
                                    
                                if (count_add + count_upd) % batch_size == 0:
                                    try: session.commit()
                                    except Exception as e: session.rollback(); st.error(f"Erreur lot : {e}")

                    try: session.commit()
                    except Exception as e: session.rollback(); st.error(f"Erreur finale : {e}")
                    
                    progress_text.empty()
                    status.update(label=f"Succès ! {count_add} créés, {count_upd} mis à jour. ({count_ignored} ignorés car <= 40k).", state="complete")
                st.balloons()
            except Exception as e: session.rollback(); st.error(f"Erreur technique : {e}")
            finally: session.close()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.error("Zone de danger")
        if st.button("🗑️ FORMARTER LA BASE DE DONNÉES", type="primary"):
            session = get_session()
            session.query(Dossier).delete(); session.commit(); session.close()
            st.rerun()

    with tab2:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        try: df_users = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
        except: df_users = pd.DataFrame()
            
        if not df_users.empty:
            st.markdown("### 🔑 Gestion des Accès")
            edited_users = st.data_editor(
                df_users, use_container_width=True, hide_index=True,
                column_config={
                    "id": None, "identifiant": st.column_config.TextColumn("Identifiant", disabled=True), 
                    "nom": st.column_config.TextColumn("Nom", disabled=True), 
                    "daira": st.column_config.SelectboxColumn("Cellule", options=LISTE_DAIRAS),
                    "mot_de_passe": st.column_config.TextColumn("Mot de passe")
                }
            )
            if st.button("💾 Sauvegarder", type="primary"):
                session = get_session()
                try:
                    for _, row in edited_users.iterrows():
                        user_db = session.query(UtilisateurAuth).get(row['id'])
                        if user_db: 
                            user_db.mot_de_passe = row['mot_de_passe']
                            user_db.daira = row['daira']
                    session.commit()
                    st.success("✅ Accès mis à jour !")
                except Exception as e: session.rollback()
                finally: session.close()
                
        st.markdown("---")
        with st.form("ajout_agent"):
            st.markdown("#### ➕ Ajouter un agent")
            c1, c2, c3 = st.columns([1, 1.5, 1])
            new_id = c1.text_input("Identifiant")
            new_nom = c2.text_input("Nom Complet")
            new_daira = c3.selectbox("Cellule", LISTE_DAIRAS)
            if st.form_submit_button("Créer le compte") and new_id and new_nom:
                session = get_session()
                if not session.query(UtilisateurAuth).filter_by(identifiant=new_id.lower()).first():
                    session.add(UtilisateurAuth(identifiant=new_id.lower(), nom=new_nom.upper(), daira=new_daira, mot_de_passe="angem2026", role="agent"))
                    session.commit()
                    st.success("Agent ajouté !")
                    st.rerun()
                session.close()
        st.markdown("</div>", unsafe_allow_html=True)

# --- DEMARRAGE DE L'APPLICATION ---
if st.session_state.user is None: login_page()
else:
    page = sidebar_menu()
    
    if "Espace de Travail" in page or "Base Globale" in page:
        vue_admin = "Base Globale" in page
        page_gestion(vue_admin=vue_admin)
    elif "Corbeille" in page: page_corbeille()
    elif "Supervision" in page and st.session_state.user['role'] == "admin": page_supervision()
    elif "Intégration" in page and st.session_state.user['role'] == "admin": page_integration_admin()
