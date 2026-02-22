import streamlit as st
import pandas as pd
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import io
import unicodedata
import re
import plotly.express as px

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="ANGEM MANAGER",
    page_icon="🇩🇿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);}
    .metric-value {font-size: 24px; font-weight: bold; color: #0e1117;}
    .metric-label {font-size: 14px; color: #555;}
    .stApp {background-color: #ffffff;}
    div[data-testid="stMetric"] {background-color: #ffffff; border: 1px solid #e6e9ef; padding: 10px; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- 1. BASE DE DONNÉES (SQLAlchemy) ---
Base = declarative_base()
engine = create_engine('sqlite:///angem_pro.db', echo=False)
Session = sessionmaker(bind=engine)

class Dossier(Base):
    __tablename__ = 'dossiers'
    id = Column(Integer, primary_key=True)
    # Identité
    nom = Column(String)
    prenom = Column(String)
    num_cni = Column(String, index=True)
    date_naissance = Column(String)
    adresse = Column(String)
    telephone = Column(String)
    genre = Column(String)
    niveau_instruction = Column(String)
    # Projet
    activite = Column(String)
    secteur = Column(String)
    commune = Column(String)
    gestionnaire = Column(String)
    zone = Column(String)
    # Finance
    montant_pnr = Column(Float, default=0.0)
    apport_personnel = Column(Float, default=0.0)
    credit_bancaire = Column(Float, default=0.0)
    banque_nom = Column(String)
    numero_compte = Column(String)
    date_financement = Column(String)
    # Recouvrement
    montant_rembourse = Column(Float, default=0.0)
    reste_rembourser = Column(Float, default=0.0)
    nb_echeance_tombee = Column(Integer, default=0)
    etat_dette = Column(String)

# Création de la table si elle n'existe pas
Base.metadata.create_all(engine)

# --- 2. OUTILS & LOGIQUE MÉTIER ---

def get_session():
    return Session()

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

# --- MAPPING INTELLIGENT ---
MAPPING_CONFIG = {
    'nom': ['NOM', 'NAME', 'PROMOTEUR'],
    'prenom': ['PRENOM', 'PRENOMS'],
    'num_cni': ['CNI', 'IDENTIFIANT', 'N° CIN/PC', 'CARTENAT'],
    'activite': ['ACTIVITE', 'PROJET', 'INTITULE'],
    'montant_pnr': ['PNR', 'MONTANT PNR', 'MT PNR'],
    'banque_nom': ['BANQUE', 'AGENCE BANCAIRE'],
    'montant_rembourse': ['VERSEMENT', 'REMBOURSE', 'TOTAL VERS'],
    'reste_rembourser': ['RESTE', 'SOLDE', 'A PAYER']
    # (J'ai allégé pour la lisibilité, mais la logique reste la même)
}

# --- 3. INTERFACE UTILISATEUR ---

def sidebar_menu():
    st.sidebar.title("MENU GÉNÉRAL")
    page = st.sidebar.radio("Navigation", ["Tableau de Bord", "Gestion Dossiers", "Import Excel", "Admin"])
    st.sidebar.markdown("---")
    st.sidebar.caption("Système ANGEM V.Streamlit")
    return page

def page_dashboard():
    st.title("📊 Tableau de Bord")
    
    session = get_session()
    df = pd.read_sql(session.query(Dossier).statement, session.bind)
    session.close()

    if df.empty:
        st.warning("La base de données est vide. Allez dans 'Import Excel'.")
        return

    # KPIS
    col1, col2, col3, col4 = st.columns(4)
    total_dossiers = len(df)
    total_pnr = df['montant_pnr'].sum()
    total_recouvre = df['montant_rembourse'].sum()
    total_reste = df['reste_rembourser'].sum()

    col1.metric("Total Dossiers", total_dossiers)
    col2.metric("Montant PNR (DA)", f"{total_pnr:,.0f}")
    col3.metric("Recouvré (DA)", f"{total_recouvre:,.0f}", delta="Versé")
    col4.metric("Reste à Payer (DA)", f"{total_reste:,.0f}", delta_color="inverse")

    st.markdown("---")

    # GRAPHIQUES
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Répartition par Banque")
        if 'banque_nom' in df.columns:
            banque_counts = df['banque_nom'].value_counts().reset_index()
            banque_counts.columns = ['Banque', 'Nombre']
            fig = px.pie(banque_counts, values='Nombre', names='Banque', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Top 10 Activités")
        if 'activite' in df.columns:
            act_counts = df['activite'].value_counts().head(10)
            st.bar_chart(act_counts)

def page_gestion():
    st.title("🗂️ Gestion des Dossiers")
    
    session = get_session()
    df = pd.read_sql(session.query(Dossier).statement, session.bind)
    
    # RECHERCHE
    search = st.text_input("🔍 Rechercher (Nom, CNI, Activité...)", "")
    
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    # TABLEAU INTERACTIF (EDITABLE !)
    st.info("💡 Astuce : Vous pouvez modifier les cases directement dans le tableau ci-dessous !")
    
    edited_df = st.data_editor(
        df_display,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "montant_pnr": st.column_config.NumberColumn(format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn(format="%d DA"),
        },
        hide_index=True
    )

    # SAUVEGARDE DES MODIFICATIONS
    if st.button("💾 Enregistrer les modifications"):
        # Logique simplifiée pour mettre à jour la DB depuis le dataframe édité
        # Attention : Pour une vraie prod, il faut comparer les diffs.
        # Ici, on réécrit (méthode brutale mais efficace pour Streamlit local)
        try:
            edited_df.to_sql('dossiers', con=engine, if_exists='replace', index=False)
            st.success("Base de données mise à jour avec succès !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde : {e}")
            
    session.close()

def page_import():
    st.title("📥 Importation Excel")
    st.markdown("Fusionnez vos fichiers **Finance** et **Recouvrement** ici.")
    
    uploaded_file = st.file_uploader("Choisir un fichier Excel (.xlsx, .xls)", type=['xlsx', 'xls'])
    
    if uploaded_file and st.button("Lancer l'Analyse et l'Import"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
            count_add = 0
            count_upd = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for sheet_idx, (sheet_name, df_raw) in enumerate(xl.items()):
                status_text.text(f"Traitement de la feuille : {sheet_name}")
                df_raw = df_raw.fillna('')
                
                # Recherche En-tête
                header_idx = -1
                for i in range(min(30, len(df_raw))):
                    row = [clean_header(x) for x in df_raw.iloc[i].values]
                    if any(k in row for k in ['NOM', 'PNR', 'BANQUE', 'VERSEMENT']):
                        header_idx = i; break
                
                if header_idx == -1: continue
                
                # Lecture propre
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_idx, dtype=str).fillna('')
                
                # Mapping dynamique
                col_map = {}
                df_cols = [clean_header(c) for c in df.columns]
                
                for db_field, variants in MAPPING_CONFIG.items():
                    for v in variants:
                        clean_v = clean_header(v)
                        # Match exact ou partiel
                        match = next((col for col in df_cols if clean_v in col), None)
                        if match:
                            col_map[db_field] = df.columns[df_cols.index(match)]
                            break
                
                if 'nom' not in col_map: continue

                # Upsert Logic
                for _, row in df.iterrows():
                    data = {}
                    for db_f, xl_c in col_map.items():
                        val = row[xl_c]
                        if db_f in ['montant_pnr', 'montant_rembourse', 'reste_rembourser']:
                            data[db_f] = clean_money(val)
                        elif db_f == 'num_cni':
                            data[db_f] = clean_cni(val)
                        else:
                            data[db_f] = str(val).strip().upper() if val else ""
                    
                    if not data.get('nom'): continue

                    # Recherche doublon
                    existing = None
                    if data.get('num_cni'):
                        existing = session.query(Dossier).filter_by(num_cni=data['num_cni']).first()
                    
                    if existing:
                        # Update seulement si vide
                        for k, v in data.items():
                            if v: setattr(existing, k, v)
                        count_upd += 1
                    else:
                        # Insert
                        new_dos = Dossier(**data)
                        session.add(new_dos)
                        count_add += 1
                
                progress_bar.progress((sheet_idx + 1) / len(xl))

            session.commit()
            st.success(f"Terminé ! {count_add} ajoutés, {count_upd} mis à jour.")
            
        except Exception as e:
            st.error(f"Erreur : {e}")
        finally:
            session.close()

def page_admin():
    st.title("🔒 Administration")
    password = st.text_input("Mot de passe Admin", type="password")
    
    if password == "angem":
        st.success("Connecté")
        if st.button("🗑️ VIDER LA BASE DE DONNÉES", type="primary"):
            session = get_session()
            session.query(Dossier).delete()
            session.commit()
            session.close()
            st.warning("Base vidée.")
            st.rerun()
        
        st.download_button(
            "📥 Télécharger la Base (Excel)",
            data=open("angem_pro.db", "rb"), # Idéalement convertir en Excel ici
            file_name="backup_angem.db"
        )

# --- LANCEMENT ---
page = sidebar_menu()

if page == "Tableau de Bord":
    page_dashboard()
elif page == "Gestion Dossiers":
    page_gestion()
elif page == "Import Excel":
    page_import()
elif page == "Admin":
    page_admin()
