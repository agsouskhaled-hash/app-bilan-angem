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
DB_PATH = os.path.join(BASE_DIR, "angem_pro_v5.db") # v5 pour forcer la nouvelle architecture blindée

Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

# --- 1. STRUCTURE DE LA BASE DE DONNÉES ---
class Dossier(Base):
    __tablename__ = 'dossiers'
    id = Column(Integer, primary_key=True)
    nom = Column(String)
    prenom = Column(String)
    identifiant = Column(String, index=True)
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

# --- 2. OUTILS DE NETTOYAGE BLINDÉS ---
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
    """Garde les 18 chiffres intacts de l'identifiant et rejette les déchets"""
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    s = re.sub(r'\D', '', s)
    if len(s) < 10: return "" # Un vrai CNI ANGEM fait plus de 10 chiffres
    return s

# --- MAPPING INTELLIGENT EXHAUSTIF ---
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
    'gestionnaire': ['ACCOMPAGNATEUR', 'GEST', 'SUIVIPAR'],
    'zone': ['ZONEDACTIVIEURBAINERURALE', 'ZONE'],
    'montant_pnr': ['MONTANTPNR29', 'MTDUPNR', 'PNR', 'MONTANT'],
    'apport_personnel': ['APPERS1', 'APPERS', 'AP', 'APPORTPERSONNEL'],
    'credit_bancaire': ['CBANCAIRE70', 'CBANCAIRE', 'CMT', 'CREDITBANCAIRE'],
    'montant_total_credit': ['TOTALCREDIT', 'COUTDUPROJET'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'agence_bancaire': ['LAGENCEBANCAIREDUPROMOTEUR', 'CODEAGENCE', 'AGENCE'],
    'numero_compte': ['NDUCOMPTE'],
    'num_ordre_versement': ['NDORDREDEVIREMENT', 'NUMOV', 'OV'], 
    'date_financement': ['DATEDEVIREMENT', 'DATEVIREMENT', 'DATEOV'],
    'debut_consommation': ['DEBUTCONSOM', 'DEBUTCONSOMMATION'],
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTA', 'MONTANTRESTAREMB', 'RESTE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
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
        st.warning("La base de données est vide. Allez dans l'onglet 'Import Excel'.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Dossiers", len(df))
    col2.metric("Montant PNR (DA)", f"{df['montant_pnr'].astype(float).sum():,.0f}")
    col3.metric("Total Recouvré (DA)", f"{df['montant_rembourse'].astype(float).sum():,.0f}", delta="Versé")
    col4.metric("Reste à Payer (DA)", f"{df['reste_rembourser'].astype(float).sum():,.0f}", delta_color="inverse")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Répartition par Banque")
        if 'banque_nom' in df.columns and not df['banque_nom'].eq('').all():
            b_counts = df[df['banque_nom'] != '']['banque_nom'].value_counts().reset_index()
            b_counts.columns = ['Banque', 'Nombre']
            st.plotly_chart(px.pie(b_counts, values='Nombre', names='Banque', hole=0.4), use_container_width=True)
            
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

    search = st.text_input("🔍 Rechercher (Nom, Identifiant ou Activité) :", "")
    
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    st.info("💡 Double-cliquez sur une cellule pour modifier, puis appuyez sur le bouton Enregistrer.")
    
    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "identifiant": st.column_config.TextColumn("Identifiant (CNI)"),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste (DA)", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Versé (DA)", format="%d DA"),
        }
    )

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
    st.title("📥 Importation Avancée (Fuzzy Match)")
    st.markdown("Importez vos fichiers. Le système lira intelligemment les en-têtes et les numéros d'identification.")
    
    uploaded_file = st.file_uploader("Fichier Excel (.xls ou .xlsx)", type=['xlsx', 'xls'])
    
    if uploaded_file and st.button("Analyser et Importer", type="primary"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
            total_add, total_upd = 0, 0
            
            with st.expander("🔍 Journal d'importation (Détails)", expanded=True):
                for s_name, df_raw in xl.items():
                    df_raw = df_raw.fillna('')
                    header_idx = -1
                    
                    # NOUVELLE DETECTION INFAILLIBLE DE L'EN-TETE
                    for i in range(min(30, len(df_raw))):
                        row_cleaned = [clean_header(str(x)) for x in df_raw.iloc[i].values]
                        score = 0
                        if "NOM" in row_cleaned or "NOMETPRENOM" in row_cleaned or "PROMOTEUR" in row_cleaned: score += 1
                        if "PRENOM" in row_cleaned or "PRENOMS" in row_cleaned: score += 1
                        if "IDENTIFIANT" in row_cleaned or "CNI" in row_cleaned or "CARTENAT" in row_cleaned: score += 1
                        if "PNR" in row_cleaned or "MONTANTPNR29" in row_cleaned or "MONTANT" in row_cleaned: score += 1
                        if "BANQUE" in row_cleaned or "AGENCEBANCAIRE" in row_cleaned: score += 1
                        
                        if score >= 2: # Il faut au moins 2 vraies colonnes reconnues pour valider l'en-tête
                            header_idx = i
                            break
                    
                    if header_idx == -1:
                        st.warning(f"Ignoré : L'onglet '{s_name}' ne ressemble pas à un tableau ANGEM.")
                        continue
                        
                    # Découpage du tableau
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    
                    df_cols = [clean_header(c) for c in df.columns]
                    col_map = {}
                    
                    # MAPPING STRICT ET PRECIS
                    for db_f, variants in MAPPING_CONFIG.items():
                        # Recherche Exacte
                        for v in variants:
                            clean_v = clean_header(v)
                            if clean_v in df_cols:
                                col_map[db_f] = df.columns[df_cols.index(clean_v)]
                                break
                        # Recherche partielle si non trouvé
                        if db_f not in col_map:
                            for v in variants:
                                clean_v = clean_header(v)
                                for idx, col in enumerate(df_cols):
                                    if len(clean_v) >= 3 and clean_v in col:
                                        if clean_v == 'NOM' and 'PRENOM' in col: continue
                                        col_map[db_f] = df.columns[idx]
                                        break
                                if db_f in col_map: break
                    
                    if 'nom' not in col_map:
                        st.warning(f"Ignoré : Colonne 'Nom' introuvable dans '{s_name}'.")
                        continue

                    count_add, count_upd = 0, 0
                    for _, row in df.iterrows():
                        data = {}
                        for db_f, xl_c in col_map.items():
                            val = row[xl_c]
                            if db_f in ['montant_pnr', 'montant_rembourse', 'reste_rembourser', 'apport_personnel', 'credit_bancaire', 'montant_total_credit']:
                                data[db_f] = clean_money(val)
                            elif db_f == 'identifiant':
                                data[db_f] = clean_identifiant(val)
                            else:
                                data[db_f] = str(val).strip().upper() if val else ""
                        
                        if not data.get('nom'): continue

                        # FUSION INFAILLIBLE PAR IDENTIFIANT OU NOM+PRENOM
                        ident = data.get('identifiant', '')
                        exist = None
                        
                        if ident:
                            exist = session.query(Dossier).filter_by(identifiant=ident).first()
                        
                        if not exist and data.get('nom'):
                            nom_val = data['nom']
                            prenom_val = data.get('prenom', '')
                            exist = session.query(Dossier).filter_by(nom=nom_val, prenom=prenom_val).first()
                            #
