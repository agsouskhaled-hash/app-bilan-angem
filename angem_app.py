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

# LA CORRECTION EST ICI : On utilise un nouveau nom (v2) pour forcer une base neuve !
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

def clean_cni(val):
    if pd.isna(val): return ""
    try:
        if isinstance(val, float): return '{:.0f}'.format(val)
        s = str(val).strip()
        if 'E' in s or '.' in s: return '{:.0f}'.format(float(s))
        return s
    except: return str(val).strip()

# --- MAPPING INTELLIGENT (Spécial ANGEM 2006-2023) ---
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
        st.warning("La base de données est vide. Allez dans l'onglet 'Import Excel' pour charger vos fichiers.")
        return

    # KPIS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Dossiers", len(df))
    col2.metric("Montant PNR (DA)", f"{df['montant_pnr'].astype(float).sum():,.0f}")
    col3.metric("Total Recouvré (DA)", f"{df['montant_rembourse'].astype(float).sum():,.0f}", delta="Versé")
    col4.metric("Reste à Payer (DA)", f"{df['reste_rembourser'].astype(float).sum():,.0f}", delta_color="inverse")
    
    st.markdown("---")
    
    # Graphiques
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Répartition par Banque")
        if 'banque_nom' in df.columns and not df['banque_nom'].eq('').all():
            b_counts = df[df['banque_nom'] != '']['banque_nom'].value_counts().reset_index()
            b_counts.columns = ['Banque', 'Nombre']
            st.plotly_chart(px.pie(b_counts, values='Nombre', names='Banque', hole=0.4), use_container_width=True)
        else:
            st.info("Les données bancaires ne sont pas encore importées.")
            
    with c2:
        st.subheader("Top Secteurs / Activités")
        if 'activite' in df.columns and not df['activite'].eq('').all():
            act_counts = df[df['activite'] != '']['activite'].value_counts().head(10)
            st.bar_chart(act_counts)

def page_gestion():
    st.title("🗂️ Gestion des Dossiers")
    
    try:
        df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except:
        df = pd.DataFrame()

    if df.empty:
        st.warning("Aucun dossier enregistré.")
        return

    # Barre de recherche
    search = st.text_input("🔍 Rechercher (Tapez un Nom, une CNI ou une Activité) :", "")
    
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    st.info("💡 Cliquez deux fois sur n'importe quelle case du tableau pour la modifier. N'oubliez pas de cliquer sur 'Enregistrer' en bas !")
    
    # Tableau éditable
    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste (DA)", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Versé (DA)", format="%d DA"),
        }
    )

    # Sauvegarde
    if st.button("💾 Enregistrer les modifications", type="primary"):
        session = get_session()
        try:
            for _, row in edited_df.iterrows():
                dos = session.query(Dossier).get(row['id'])
                if dos:
                    for col in edited_df.columns:
                        if col != 'id':
                            setattr(dos, col, row[col])
            session.commit()
            st.success("Données mises à jour avec succès !")
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")
        finally:
            session.close()

def page_import():
    st.title("📥 Importation Automatique")
    st.markdown("Glissez vos fichiers **Finance** et **Recouvrement** ci-dessous.")
    
    uploaded_file = st.file_uploader("Fichier Excel (.xls ou .xlsx)", type=['xlsx', 'xls'])
    
    if uploaded_file and st.button("Lancer l'Analyse et l'Import"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
            count_add = 0
            count_upd = 0
            
            progress = st.progress(0)
            status = st.empty()
            
            for idx, (s_name, df_raw) in enumerate(xl.items()):
                status.text(f"Analyse de la feuille : {s_name}...")
                df_raw = df_raw.fillna('')
                
                # Chercher la ligne d'en-tête (Fuzzy header)
                header_idx = -1
                for i in range(min(30, len(df_raw))):
                    row = [clean_header(x) for x in df_raw.iloc[i].values]
                    if any(k in row for k in ['NOM', 'PNR', 'BANQUE', 'VERSEMENT', 'IDENTIFIANT', 'NOMETPRENOM']):
                        header_idx = i; break
