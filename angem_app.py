import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import plotly.express as px

# --- CONFIGURATION DE LA PAGE & CHEMIN ABSOLU ---
st.set_page_config(page_title="ANGEM MANAGER PRO", page_icon="🇩🇿", layout="wide")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "angem_pro_v2.db")

Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

# --- 1. STRUCTURE DE LA BASE DE DONNÉES ---
class Dossier(Base):
    __tablename__ = 'dossiers'
    id = Column(Integer, primary_key=True)
    nom = Column(String)
    prenom = Column(String)
    num_cni = Column(String, index=True)
    date_naissance = Column(String)
    adresse = Column(String)
    telephone = Column(String)
    genre = Column(String)
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

Base.metadata.create_all(engine)

def get_session():
    return Session()

# --- 2. OUTILS DE NETTOYAGE ---
def clean_header(val):
    if pd.isna(val): 
        return ""
    val = str(val).upper()
    val = ''.join(c for c in unicodedata.normalize('NFD', val) if unicodedata.category(c) != 'Mn')
    return ''.join(filter(str.isalnum, val))

def clean_money(val):
    if pd.isna(val) or val == '': 
        return 0.0
    s = str(val).upper().replace('DA', '').replace(' ', '').replace(',', '.')
    s = re.sub(r'[^\d\.]', '', s)
    try: 
        return float(s)
    except: 
        return 0.0

def clean_cni(val):
    if pd.isna(val): 
        return ""
    try:
        if isinstance(val, float): 
            return '{:.0f}'.format(val)
        s = str(val).strip()
        if 'E' in s or '.' in s: 
            return '{:.0f}'.format(float(s))
        return s
    except: 
        return str(val).strip()

# --- MAPPING INTELLIGENT ---
MAPPING_CONFIG = {
    'num_cni': ['IDENTIFIANT', 'CNI', 'N° CIN/PC', 'CARTENAT'],
    'nom': ['NOM', 'NOM ET PRENOM', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'genre': ['GENRE', 'G', '(H/F)'],
    'date_naissance': ['DATE DE NAISSANCE', 'NE LE', 'D.N'],
    'adresse': ['ADRESSE', 'RESIDENCE'],
    'telephone': ['TEL', 'PHONE', 'MOBILE'],
    'niveau_instruction': ['NIVEAU D\'INSTRUCTION', 'INSTRUCTION'],
    'age': ['TRANCHE D\'AGE', 'AGE'],
    'activite': ['ACTIVITE', 'PROJET', 'AVTIVITE'],
    'code_activite': ['CODE D\'ACTIVITE', 'CODE ACTIVITE'],
    'secteur': ['SECTEUR D\'ACTIVITE', 'SECTEUR'],
    'daira': ['DAIRA'],
    'commune': ['COMMUNE', 'APC'],
    'gestionnaire': ['ACCOMPAGNATEUR', 'GEST', 'SUIVI PAR'],
    'zone': ['ZONE D\'ACTIVIE URBAINE /RURALE', 'ZONE'],
    'montant_pnr': ['MONTANT PNR 29 %', 'MT DU P.N.R', 'PNR', 'MONTANT'],
    'apport_personnel': ['APPERS 1%', 'AP,PERS 1%', 'AP', 'APPERS', 'APPORT PERSONNEL'],
    'credit_bancaire': ['C,BANCAIRE 70%', 'C.BANCAIRE 70%', 'C,BANCAIRE', 'CMT', 'CREDIT BANCAIRE'],
    'montant_total_credit': ['TOTAL CREDIT', 'COUT DU PROJET'],
    'banque_nom': ['BANQUE DU PROMOTEUR', 'BANQUE/CCP', 'BANQUE'],
    'agence_bancaire': ['L\'AGENCE BANCAIRE DU PROMOTEUR', 'CODE AGENCE', 'AGENCE'],
    'numero_compte': ['N° DU COMPTE', 'N° DU COMPTE '],
    'num_ordre_versement': ['N° D\'ORDRE DE VIREMENT', 'NUM OV', 'OV'], 
    'date_financement': ['DATE DE VIREMENT', 'DATE VIREMENT', 'DATE OV'],
    'debut_consommation': ['DÉBUT CONSOM.', 'DEBUT CONSOMMATION'],
    'montant_rembourse': ['TOTAL REMB.', 'TOTAL VERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANT REST À REMB', 'MONTANT REST A REMB', 'RESTE'],
    'nb_echeance_tombee': ['NBR ECH TOMB.', 'ECHEANCES TOMBEES'],
    'etat_dette': ['ETAT', 'SITUATION']
}

# --- 3. PAGES DE L'APPLICATION ---
def sidebar_menu():
    st.sidebar.title("MENU ANGEM")
    return st.sidebar.radio("Navigation", ["Tableau de Bord", "Gestion Dossiers", "Import Excel", "Admin"])

def page_dashboard():
    st.title("📊 Tableau de Bord")
    
    try:
        df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base de données est vide. Allez dans l'onglet 'Import Excel' pour charger vos
