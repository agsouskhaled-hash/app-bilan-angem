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
st.set_page_config(page_title="ANGEM Intra-Service v18.0", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]

# --- CONNEXION CLOUD SUPABASE (STORAGE) ---
SUPABASE_URL = "https://greyjhgiytajxpvucbrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyZXlqaGdpeXRhanhwdnVjYnJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTU0MjksImV4cCI6MjA4NzU5MTQyOX0.jCNan1Y1hvfGog6Zcu8Rr8d5PkeFRFvipAGGB09ztxo"
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LE STYLE CSS ÉPURÉ ---
st.markdown("""
<style>
    .stApp { background-color: #f4f7f6; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e1e5eb; padding: 20px;
        border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        border-left: 6px solid #1f77b4; transition: transform 0.2s ease-in-out;
    }
    .modern-card {
        background-color: #ffffff; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); margin-top: 15px; margin-bottom: 15px;
        border: 1px solid #e1e5eb;
    }
    .profil-header {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); padding: 20px;
        border-radius: 10px; border-left: 6px solid #28a745; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .action-btn-container { display: flex; gap: 10px; margin-top: 10px; margin-bottom: 20px; }
    .btn-call { background-color: #007bff; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; width: 100%; display: block; transition: 0.3s; }
    .btn-wa { background-color: #25D366; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; text-align: center; width: 100%; display: block; transition: 0.3s; }
    .btn-call:hover, .btn-wa:hover { opacity: 0.8; color: white; }
    .doc-link { display: block; background-color: #f0f2f6; padding: 12px; border-radius: 8px; text-decoration: none; color: #1f77b4; font-weight: bold; margin-bottom: 8px; border: 1px solid #e1e5eb; transition: 0.2s;}
    .doc-link:hover { background-color: #e1e5eb; color: #0d47a1; }
    .badge-projet { background-color: #1f77b4; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; vertical-align: middle; margin-left: 10px; }
    .badge-amp { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; vertical-align: middle; margin-left: 10px; }
    .search-box { font-size: 20px !important; padding: 15px !important; }
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
        st.markdown(f'<div style="text-align: center; color: #1f77b4; font-size: 24px; font-weight: bold; border: 2px solid #1f77b4; padding: 10px; border-radius: 10px; margin-bottom: 20px;">🔵 ANGEM Intra-Service</div>', unsafe_allow_html=True)

def clean_pdf_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')

def get_lat_lon(commune_name):
    c = str(commune_name).upper().strip()
    if "ZÉRALDA" in c or "ZERALDA" in c or "STAOUELI" in c: return 36.7115, 2.8425
    if "CHÉRAGA" in c or "CHERAGA" in c or "AIN BENIAN" in c: return 36.7667, 2.9500
    if "DRARIA" in c or "BABA HASSEN" in c: return 36.7167, 2.9833
    if "BIR MOURAD RAIS" in c or "BIR MOURAD" in c: return 36.7333, 3.0500
    if "BOUZAREAH" in c or "BEN AKNOUN" in c: return 36.7833, 3.0167
    if "BIRTOUTA" in c or "TESSALA" in c: return 36.6500, 2.9833
    return 36.7300, 3.0000

# --- FONCTIONS DOSSIERS ---
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
    pdf.cell(0, 8, f" Adresse : {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)}", border='LRB', ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " 2. PROJET & FINANCEMENT", border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f" Dispositif : {clean_pdf_text(dos.type_dispositif)}", border='L')
    pdf.cell(95, 8, f" Statut : {clean_pdf_text(dos.statut_dossier)}", border='R', ln=True)
    pdf.cell(95, 8, f" Activite : {clean_pdf_text(dos.activite)}", border='L')
    pdf.cell(95, 8, f" Date de versement (OV) : {clean_pdf_text(dos.date_financement)}", border='R', ln=True)
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
    'commune': ['COMMUNE', 'APC', 'ADRESSE'],
    'secteur': ['SECTEURDACTIVITE', 'SECTEUR'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'montant_pnr': ['PNR', 'MONTANTPNR29', 'MTDUPNR', 'MONTANT'],
    'apport_personnel': ['APPORT', 'APPORTPERSONNEL'], 
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'telephone': ['TEL', 'TELEPHONE', 'MOB', 'MOBILE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
    'date_financement': ['DATEOV', 'DATEDEVIREMENT', 'DATEVIREMENT', 'DATEDEFINANCEMENT'], 
    'activite': ['ACTIVITE', 'PROJET'],
}
COLONNES_ARGENT = ['montant_pnr', 'montant_rembourse', 'reste_rembourser', 'apport_personnel']

def calculer_alerte_bool(row):
    ech = str(row.get('nb_echeance_tombee', '')).strip()
    if any(char.isdigit() for char in ech):
        num = int(re.search(r'\d+', ech).group())
        if num > 0: return True
    if row.get('statut_dossier') == "Contentieux / Retard": return True
    return False

def get_badge(row):
    if calculer_alerte_bool(row): return "🔴 Retard"
    elif float(row.get('reste_rembourser', 0)) > 0: return "🟡 En cours"
    else: return "🟢 À jour"

if 'user' not in st.session_state: st.session_state.user = None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        afficher_logo(220)
        st.markdown("<h3 style='color: #2c3e50; margin-bottom: 25px;'>Portail Dossiers ANGEM</h3>", unsafe_allow_html=True)
        
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
    
    options = [
        "🔍 Recherche Promoteur", 
        "🔵 Mes Dossiers (PROJET)", 
        "🟢 Mes Dossiers (AMP)", 
        "🗑️ Corbeille Cellule"
    ]
    if st.session_state.user['role'] == "admin":
        options = [
            "🔍 Recherche Promoteur",
            "🔵 Tous les Dossiers (PROJET)",
            "🟢 Tous les Dossiers (AMP)",
            "📊 Supervision & Extractions", 
            "⚙️ Équipes & Intégration"
        ]
        
    choix = st.sidebar.radio("Navigation Menu", options, label_visibility="collapsed")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    return choix

# --- AFFICHAGE DU PROFIL (RÉUTILISABLE) ---
def afficher_profil_promoteur(dos_db, session):
    taux = (dos_db.montant_rembourse / dos_db.montant_pnr) if dos_db.montant_pnr > 0 else 0
    badge_html = f"<span class='badge-projet'>🔵 PROJET</span>" if dos_db.type_dispositif == "PNR PROJET" else f"<span class='badge-amp'>🟢 AMP</span>"
    st.markdown(f"""
    <div class='profil-header'>
        <h2 style='margin:0; color:#1f77b4;'>👤 {dos_db.nom} {dos_db.prenom} {badge_html}</h2>
        <p style='margin:5px 0 0 0; font-size:16px;'><b>Identifiant:</b> {dos_db.identifiant} &nbsp;|&nbsp; <b>Activité:</b> {dos_db.activite} ({dos_db.commune})</p>
        <p style='margin:10px 0 5px 0;'><b>Remboursement ({dos_db.montant_rembourse:,.0f} / {dos_db.montant_pnr:,.0f} DA) : {taux*100:.1f}%</b></p>
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
        st.caption("⚠️ Pas de numéro de téléphone valide enregistré.")

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
        
        st.markdown("<div style='background-color:#ffffff; border:1px solid #e1e5eb; padding:15px; border-radius:8px; height: 300px; overflow-y: auto;'>", unsafe_allow_html=True)
        if dos_db.historique_visites: st.markdown(dos_db.historique_visites.replace('\n', '  \n'))
        else: st.markdown("<span style='color:#888;'>Aucun rapport enregistré.</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_droite:
        st.markdown("### 📎 Dossier du Promoteur")
        pdf_bytes = generer_fiche_promoteur_pdf(dos_db)
        st.download_button("📄 Exporter le Dossier PDF", data=pdf_bytes, file_name=f"Dossier_{dos_db.identifiant}.pdf", mime="application/pdf", use_container_width=True, key=f"pdf_{dos_db.id}")
        
        st.markdown("---")
        with st.expander("☁️ 📸 Scanner vers le Cloud"):
            photo_camera = st.camera_input("Prise de vue", label_visibility="collapsed", key=f"cam_{dos_db.id}")
            if photo_camera is not None:
                if st.button("☁️ Envoyer sur le Cloud", use_container_width=True, key=f"up_cam_{dos_db.id}"):
                    file_bytes = photo_camera.getvalue()
                    nom_fichier = f"{dos_db.identifiant}_SCAN_{int(datetime.now().timestamp())}.jpg"
                    try:
                        supabase_client.storage.from_("scans_angem").upload(file=file_bytes, path=nom_fichier, file_options={"content-type": "image/jpeg"})
                        dos_db.documents = (dos_db.documents or "") + nom_fichier + "|"
                        session.commit()
                        st.success("✅ Archivé sur le Cloud !")
                        st.rerun()
                    except Exception as e: st.error(f"Erreur Cloud : {e}")

        with st.expander("☁️ 📁 Importer un document (PDF/Image)"):
            nouveau_scan = st.file_uploader("Choisir un fichier", type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed", key=f"file_{dos_db.id}")
            if nouveau_scan is not None:
                if st.button("☁️ Envoyer le fichier", use_container_width=True, key=f"up_file_{dos_db.id}"):
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
                
        st.markdown("**🗄️ Archives Cloud :**")
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

# --- PAGES DE L'APPLICATION ---

def page_recherche():
    st.title("🔍 Moteur de Recherche Promoteur")
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    recherche = st.text_input("Recherchez un promoteur (Nom, Prénom, Identifiant, Téléphone...) :", placeholder="Tapez ici...", key="main_search")
    st.markdown("</div>", unsafe_allow_html=True)

    if recherche:
        try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
        except: df = pd.DataFrame()
        
        if not df.empty:
            mask = df.apply(lambda x: x.astype(str).str.contains(recherche, case=False).any(), axis=1)
            df_recherche = df[mask]
            
            if not df_recherche.empty:
                st.success(f"🎯 {len(df_recherche)} résultat(s) trouvé(s)")
                for _, row in df_recherche.iterrows():
                    with st.expander(f"Ouvrir le dossier de : {row['nom']} {row['prenom']} ({row['identifiant']}) - {row['type_dispositif']}"):
                        session = get_session()
                        dos_db = session.query(Dossier).get(row['id'])
                        if dos_db: afficher_profil_promoteur(dos_db, session)
                        session.close()
            else:
                st.warning("Aucun promoteur ne correspond à cette recherche.")

def page_dossiers_liste(type_dispo, vue_admin=False):
    titre = "🔵 Dossiers PNR PROJET" if type_dispo == "PNR PROJET" else "🟢 Dossiers PNR AMP"
    st.title(titre)
    
    try: df = pd.read_sql_query(f"SELECT * FROM dossiers WHERE type_dispositif='{type_dispo}' ORDER BY id DESC", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info("📌 Aucun dossier de ce type dans la base de données.")
        return

    # Attribution de l'agent connecté
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
        with st.expander(f"🗓️ Agenda : {len(df_visites)} visite(s) programmée(s)", expanded=True):
            st.dataframe(df_visites[['identifiant', 'nom', 'commune', 'prochaine_visite', 'telephone']], hide_index=True, use_container_width=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    filtre_badge = st.radio("Filtrer par état :", ["Tous", "🔴 Retard", "🟡 En cours", "🟢 À jour"], horizontal=True)
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
        df_filtered, use_container_width=True, hide_index=True, height=450,
        column_config={
            "id": None, "documents": None, "historique_visites": None, "prochaine_visite": None, "type_dispositif": None,
            "Badge": st.column_config.TextColumn("État", disabled=True),
            "identifiant": st.column_config.TextColumn("Identifiant", disabled=True),
            "nom": "Nom Promoteur",
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
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

def page_corbeille():
    st.title("🗑️ Corbeille des Dossiers Non Affectés")
    agent_daira = st.session_state.user.get('daira', '')
    
    if not agent_daira:
        st.warning("⚠️ Vous n'avez pas de Daïra assignée. Demandez à l'administrateur de mettre à jour votre compte.")
        return

    st.info(f"Voici les dossiers sans gestionnaire localisés dans la Daïra de **{agent_daira}**.")
    try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except: return

    mask_vide = (df['gestionnaire'].astype(str).str.strip() == "")
    mask_cellule = df['daira'].str.contains(agent_daira, case=False, na=False) | df['commune'].str.contains(agent_daira, case=False, na=False)
    df_orphans = df[mask_vide & mask_cellule].copy()
    
    if df_orphans.empty:
        st.success("🎉 Aucun dossier orphelin dans votre secteur.")
    else:
        df_orphans["C'est mon dossier !"] = False
        edited_orphans = st.data_editor(
            df_orphans, hide_index=True, use_container_width=True,
            column_config={
                "C'est mon dossier !": st.column_config.CheckboxColumn("S'attribuer", default=False),
                "id": None, "documents": None, "historique_visites": None, "prochaine_visite": None
            },
            disabled=["identifiant", "nom", "type_dispositif", "commune", "montant_pnr"]
        )
        
        ids_recup = edited_orphans[edited_orphans["C'est mon dossier !"] == True]['id'].tolist()
        if st.button(f"📥 Récupérer ces {len(ids_recup)} dossier(s)", type="primary", disabled=(len(ids_recup)==0)):
            session = get_session()
            nom_agent = st.session_state.user['nom']
            try:
                for cid in ids_recup:
                    dos = session.query(Dossier).get(cid)
                    if dos: dos.gestionnaire = nom_agent
                session.commit()
                st.success("✅ Dossiers récupérés !")
                st.rerun()
            except Exception as e: session.rollback()
            finally: session.close()

def page_supervision():
    st.title("📊 Supervision des Dossiers & Extractions")
    try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except: df = pd.DataFrame()
    
    if df.empty: st.warning("La base est vide."); return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📌 Total Dossiers", len(df))
    c2.metric("💰 Crédit PNR", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
    c3.metric("📈 Recouvrement", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA")
    c4.metric("🚨 Reste à Recouvrer", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", delta_color="inverse")
    
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("#### 🗺️ Cartographie des Dossiers ANGEM")
    df_map = df.copy()
    df_map['lat'] = df_map['commune'].apply(lambda x: get_lat_lon(x)[0])
    df_map['lon'] = df_map['commune'].apply(lambda x: get_lat_lon(x)[1])
    df_map_grouped = df_map.groupby(['commune', 'lat', 'lon']).size().reset_index(name='Total')
    fig_map = px.scatter_mapbox(df_map_grouped, lat="lat", lon="lon", hover_name="commune", size="Total", mapbox_style="carto-positron", zoom=9)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
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
    st.title("⚙️ Équipes & Intégration")
    tab1, tab2 = st.tabs(["📥 Importation de Fichiers Excel", "🔐 Gestion des Accompagnateurs"])
    
    with tab1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        type_import = st.radio("Quel dispositif souhaitez-vous importer ?", ["🔵 PNR PROJET", "🟢 PNR AMP"], horizontal=True)
        type_dispo_val = "PNR PROJET" if "PROJET" in type_import else "PNR AMP"
        
        uploaded_file = st.file_uploader(f"📂 Glissez votre fichier Excel pour {type_dispo_val}", type=['xlsx', 'xls', 'csv'])
        if uploaded_file and st.button("🚀 Lancer l'Intégration", type="primary"):
            session = get_session()
            try:
                xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
                agents_db = session.query(UtilisateurAuth).filter_by(role='agent').all()
                agents_noms = [a.nom for a in agents_db]

                with st.status(f"Analyse en cours ({type_dispo_val})...", expanded=True) as status:
                    count_add, count_upd = 0, 0
                    for s_name, df_raw in xl.items():
                        df_raw = df_raw.fillna('')
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
                        
                        for _, row in df.iterrows():
                            data = {}
                            for db_f, xl_c in col_map.items():
                                val = row[xl_c]
                                if pd.isna(val) or str(val).strip() in ["", "NAN"]: continue 
                                if db_f in COLONNES_ARGENT: data[db_f] = clean_money(val)
                                elif db_f == 'identifiant': data[db_f] = clean_identifiant(val)
                                elif db_f == 'gestionnaire': data[db_f] = trouver_agent_intelligent(val, agents_noms)
                                else: data[db_f] = str(val).strip().upper()

                            ident = data.get('identifiant', '')
                            date_fin = data.get('date_financement', '')
                            if not ident: continue
                            data['type_dispositif'] = type_dispo_val

                            exist = session.query(Dossier).filter_by(identifiant=ident, date_financement=date_fin).first()
                            if not exist and date_fin != "": exist = session.query(Dossier).filter_by(identifiant=ident, date_financement='').first()

                            if exist:
                                for k, v in data.items(): setattr(exist, k, v)
                                count_upd += 1
                            else:
                                session.add(Dossier(**data))
                                count_add += 1
                    session.commit()
                    status.update(label=f"Terminé : {count_add} créés, {count_upd} mis à jour.", state="complete")
                st.balloons()
            except Exception as e: session.rollback(); st.error(f"Erreur : {e}")
            finally: session.close()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.error("Remise à zéro de tous les dossiers")
        if st.button("🗑️ FORMARTER LA BASE DE DONNÉES", type="primary"):
            session = get_session()
            session.query(Dossier).delete(); session.commit(); session.close()
            st.rerun()

    with tab2:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        try: df_users = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
        except: df_users = pd.DataFrame()
            
        if not df_users.empty:
            st.markdown("### 🔑 Gestion des Accès et Daïras")
            edited_users = st.data_editor(
                df_users, use_container_width=True, hide_index=True,
                column_config={
                    "id": None, "identifiant": st.column_config.TextColumn("Identifiant", disabled=True), 
                    "nom": st.column_config.TextColumn("Nom", disabled=True), 
                    "daira": st.column_config.SelectboxColumn("Cellule", options=LISTE_DAIRAS),
                    "mot_de_passe": st.column_config.TextColumn("Mot de passe")
                }
            )
            if st.button("💾 Sauvegarder les accès", type="primary"):
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
    
    if page == "🔍 Recherche Promoteur": page_recherche()
    elif page == "🔵 Mes Dossiers (PROJET)": page_dossiers_liste("PNR PROJET", vue_admin=False)
    elif page == "🟢 Mes Dossiers (AMP)": page_dossiers_liste("PNR AMP", vue_admin=False)
    elif page == "🔵 Tous les Dossiers (PROJET)": page_dossiers_liste("PNR PROJET", vue_admin=True)
    elif page == "🟢 Tous les Dossiers (AMP)": page_dossiers_liste("PNR AMP", vue_admin=True)
    elif page == "🗑️ Corbeille Cellule": page_corbeille()
    elif page == "📊 Supervision & Extractions" and st.session_state.user['role'] == "admin": page_supervision()
    elif page == "⚙️ Équipes & Intégration" and st.session_state.user['role'] == "admin": page_integration_admin()
