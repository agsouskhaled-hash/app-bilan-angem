import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import plotly.express as px

# --- CONFIGURATION & CHEMIN ABSOLU (CORRECTION BUG) ---
st.set_page_config(page_title="ANGEM MANAGER", page_icon="🇩🇿", layout="wide")

# Force la base de données à se créer EXACTEMENT dans le même dossier que app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "angem_pro.db")

Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

# --- 1. STRUCTURE DE LA BASE ---
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
    activite = Column(String)
    secteur = Column(String)
    commune = Column(String)
    gestionnaire = Column(String)
    zone = Column(String)
    montant_pnr = Column(Float, default=0.0)
    apport_personnel = Column(Float, default=0.0)
    credit_bancaire = Column(Float, default=0.0)
    banque_nom = Column(String)
    numero_compte = Column(String)
    date_financement = Column(String)
    montant_rembourse = Column(Float, default=0.0)
    reste_rembourser = Column(Float, default=0.0)
    nb_echeance_tombee = Column(Integer, default=0)
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

MAPPING_CONFIG = {
    'nom': ['NOM', 'NAME', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'num_cni': ['CNI', 'IDENTIFIANT', 'N° CIN/PC', 'CARTENAT'],
    'activite': ['ACTIVITE', 'PROJET', 'INTITULE'],
    'commune': ['COMMUNE', 'APC', 'DAIRA'],
    'montant_pnr': ['PNR', 'MONTANT PNR', 'MT PNR'],
    'banque_nom': ['BANQUE', 'AGENCE BANCAIRE'],
    'montant_rembourse': ['VERSEMENT', 'REMBOURSE', 'TOTAL VERS'],
    'reste_rembourser': ['RESTE', 'SOLDE', 'A PAYER']
}

# --- 3. PAGES DE L'APPLICATION ---
def sidebar_menu():
    st.sidebar.title("MENU GÉNÉRAL")
    return st.sidebar.radio("Navigation", ["Tableau de Bord", "Gestion Dossiers", "Import Excel", "Admin"])

def page_dashboard():
    st.title("📊 Tableau de Bord")
    
    # Lecture sécurisée de la BDD
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
    col3.metric("Recouvré (DA)", f"{df['montant_rembourse'].astype(float).sum():,.0f}", delta="Versé")
    col4.metric("Reste à Payer (DA)", f"{df['reste_rembourser'].astype(float).sum():,.0f}", delta_color="inverse")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Bilan par Banque")
        if 'banque_nom' in df.columns and not df['banque_nom'].eq('').all():
            b_counts = df[df['banque_nom'] != '']['banque_nom'].value_counts().reset_index()
            b_counts.columns = ['Banque', 'Nombre']
            st.plotly_chart(px.pie(b_counts, values='Nombre', names='Banque', hole=0.4), use_container_width=True)
        else:
            st.info("Importez un fichier 'Finance' pour voir les banques.")

def page_gestion():
    st.title("🗂️ Gestion des Dossiers")
    
    try:
        df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except:
        df = pd.DataFrame()

    if df.empty:
        st.warning("Aucun dossier enregistré.")
        return

    search = st.text_input("🔍 Rechercher par Nom, CNI ou Activité :", "")
    
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    st.info("💡 Vous pouvez modifier les cases directement ci-dessous, puis cliquer sur Enregistrer !")
    
    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste (DA)", format="%d DA"),
        }
    )

    # SAUVEGARDE SÉCURISÉE SANS CASSER LA STRUCTURE
    if st.button("💾 Enregistrer les modifications"):
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
    st.title("📥 Importation Excel")
    uploaded_file = st.file_uploader("Fichier Excel (.xls ou .xlsx)", type=['xlsx', 'xls'])
    
    if uploaded_file and st.button("Lancer l'Analyse"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
            count_add = 0
            count_upd = 0
            progress = st.progress(0)
            
            for idx, (s_name, df_raw) in enumerate(xl.items()):
                df_raw = df_raw.fillna('')
                header_idx = -1
                for i in range(min(30, len(df_raw))):
                    row = [clean_header(x) for x in df_raw.iloc[i].values]
                    if any(k in row for k in ['NOM', 'PNR', 'BANQUE', 'VERSEMENT']):
                        header_idx = i; break
                
                if header_idx == -1: continue
                
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, sheet_name=s_name, header=header_idx, dtype=str).fillna('')
                
                col_map = {}
                df_cols = [clean_header(c) for c in df.columns]
                
                for db_f, variants in MAPPING_CONFIG.items():
                    for v in variants:
                        clean_v = clean_header(v)
                        match = next((col for col in df_cols if clean_v in col), None)
                        if match: col_map[db_f] = df.columns[df_cols.index(match)]; break
                
                if 'nom' not in col_map: continue

                for _, row in df.iterrows():
                    data = {}
                    for db_f, xl_c in col_map.items():
                        val = row[xl_c]
                        if db_f in ['montant_pnr', 'montant_rembourse', 'reste_rembourser']: data[db_f] = clean_money(val)
                        elif db_f == 'num_cni': data[db_f] = clean_cni(val)
                        else: data[db_f] = str(val).strip().upper() if val else ""
                    
                    if not data.get('nom'): continue

                    exist = session.query(Dossier).filter_by(num_cni=data['num_cni']).first() if data.get('num_cni') else None
                    if not exist: exist = session.query(Dossier).filter_by(nom=data['nom'], prenom=data.get('prenom', '')).first()
                    
                    if exist:
                        for k, v in data.items():
                            if v: setattr(exist, k, v)
                        count_upd += 1
                    else:
                        session.add(Dossier(**data))
                        count_add += 1
                
                progress.progress((idx + 1) / len(xl))

            session.commit()
            st.success(f"Terminé ! {count_add} ajoutés, {count_upd} mis à jour.")
        except Exception as e:
            session.rollback()
            st.error(f"Erreur technique : {e}")
        finally:
            session.close()

def page_admin():
    st.title("🔒 Administration")
    if st.text_input("Mot de passe", type="password") == "angem":
        st.success("Accès Autorisé")
        if st.button("🗑️ VIDER LA BASE DE DONNÉES", type="primary"):
            session = get_session()
            session.query(Dossier).delete()
            session.commit()
            st.warning("Base vidée.")
            st.rerun()

# --- DEMARRAGE ---
page = sidebar_menu()
if page == "Tableau de Bord": page_dashboard()
elif page == "Gestion Dossiers": page_gestion()
elif page == "Import Excel": page_import()
elif page == "Admin": page_admin()
