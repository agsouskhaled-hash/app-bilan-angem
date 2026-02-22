import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import unicodedata
import re
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION DE LA PAGE (DESIGN MODERNE) ---
st.set_page_config(page_title="ANGEM PRO", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .stMetric {background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);}
    h1 {color: #1f2937; font-weight: 800;}
    h2, h3 {color: #374151;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;}
    .stTabs [aria-selected="true"] {background-color: #f3f4f6; border-bottom: 3px solid #007bff;}
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# ON GARDE LA V9 ! Comme ça tu ne perds pas tes données déjà importées.
DB_PATH = os.path.join(BASE_DIR, "angem_pro_v9.db") 

Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

# --- 1. STRUCTURE DE LA BASE ---
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

Base.metadata.create_all(engine)
def get_session(): return Session()

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
    if pd.isna(val): return ""
    s = str(val).strip().upper()
    if 'E' in s: 
        try: s = f"{float(s):.0f}"
        except: pass
    if s.endswith('.0'): s = s[:-2]
    s = re.sub(r'\D', '', s)
    if len(s) < 5: return ""
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

# --- 3. INTERFACE UTILISATEUR ---
def sidebar_menu():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Emblem_of_Algeria.svg/200px-Emblem_of_Algeria.svg.png", width=100)
    st.sidebar.title("ANGEM MANAGER")
    st.sidebar.markdown("---")
    return st.sidebar.radio("📌 Navigation :", ["🗂️ Consultation Dossiers", "📥 Importation Excel", "🔒 Espace Administrateur"])

def page_gestion():
    st.title("🗂️ Consultation des Dossiers")
    st.markdown("Recherchez et modifiez rapidement les informations d'un promoteur.")
    
    try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info("📌 La base est vide. Veuillez importer vos fichiers Excel.")
        return

    search = st.text_input("🔍 Recherche rapide (Identifiant, Nom, Activité, Commune...) :", placeholder="Ex: 1605011401... ou BOUDIS")
    
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df[mask]
    else:
        df_display = df

    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "id": None,
            "identifiant": st.column_config.TextColumn("Identifiant Unique", width="large"),
            "montant_pnr": st.column_config.NumberColumn("Crédit PNR", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste à Payer", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Versé", format="%d DA"),
        }
    )

    if st.button("💾 Enregistrer les modifications", type="primary"):
        session = get_session()
        try:
            for _, row in edited_df.iterrows():
                dos = session.query(Dossier).get(row['id'])
                if dos:
                    for col in edited_df.columns:
                        if col != 'id': setattr(dos, col, row[col])
            session.commit()
            st.success("✅ Modifications sauvegardées avec succès !")
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"Erreur : {e}")
        finally:
            session.close()

def page_import():
    st.title("📥 Importation des Fichiers")
    st.markdown("L'algorithme fusionnera automatiquement les données **en se basant sur l'Identifiant (18 chiffres)**.")
    
    uploaded_file = st.file_uploader("📂 Glissez votre fichier Excel (Finance ou Recouvrement)", type=['xlsx', 'xls'])
    
    if uploaded_file and st.button("🚀 Lancer l'Analyse", type="primary"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
            total_add, total_upd = 0, 0
            
            with st.status("Analyse en cours...", expanded=True) as status:
                for s_name, df_raw in xl.items():
                    df_raw = df_raw.fillna('')
                    header_idx = -1
                    
                    for i in range(min(30, len(df_raw))):
                        row_cleaned = [clean_header(str(x)) for x in df_raw.iloc[i].values]
                        score = 0
                        if any(k in row_cleaned for k in ["IDENTIFIANT", "CNI", "CARTENAT"]): score += 2
                        if any(k in row_cleaned for k in ["NOM", "NOMETPRENOM"]): score += 1
                        if any(k in row_cleaned for k in ["PNR", "MONTANT"]): score += 1
                        if any(k in row_cleaned for k in ["TOTALREMB", "MONTANTRESTAREMB"]): score += 2
                        
                        if score >= 2: 
                            header_idx = i
                            break
                    
                    if header_idx == -1:
                        st.write(f"⏭️ Feuille '{s_name}' ignorée (Pas de tableau reconnu).")
                        continue
                        
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    df_cols = [clean_header(c) for c in df.columns]
                    col_map = {}
                    
                    for db_f, variants in MAPPING_CONFIG.items():
                        for v in variants:
                            clean_v = clean_header(v)
                            if clean_v in df_cols:
                                col_map[db_f] = df.columns[df_cols.index(clean_v)]
                                break
                        if db_f not in col_map:
                            for v in variants:
                                clean_v = clean_header(v)
                                for idx, col in enumerate(df_cols):
                                    if len(clean_v) >= 3 and clean_v in col:
                                        if clean_v == 'NOM' and 'PRENOM' in col: continue
                                        col_map[db_f] = df.columns[idx]
                                        break
                                if db_f in col_map: break

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
                        
                        ident = data.get('identifiant', '')
                        if not ident and not data.get('nom'): continue

                        exist = None
                        if ident:
                            exist = session.query(Dossier).filter_by(identifiant=ident).first()
                            if not exist and len(ident) >= 12 and data.get('nom'):
                                prefix = ident[:12]
                                exist = session.query(Dossier).filter(Dossier.identifiant.like(f"{prefix}%")).first()
                                if exist and data['nom'][:3] not in exist.nom: exist = None
                        
                        if exist:
                            for k, v in data.items():
                                if v != "" and v is not None: setattr(exist, k, v)
                            count_upd += 1
                        else:
                            session.add(Dossier(**data))
                            count_add += 1

                    total_add += count_add
                    total_upd += count_upd
                    st.write(f"✔️ **{s_name}** : {count_add} nouveaux, {count_upd} mis à jour.")

                session.commit()
                status.update(label=f"Terminé ! ({total_add} Nouveaux | {total_upd} Mis à jour)", state="complete")
            st.balloons()
            
        except Exception as e:
            session.rollback()
            st.error(f"Erreur critique lors de l'import : {e}")
        finally:
            session.close()

def page_admin():
    st.title("🔒 Espace Administrateur")
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        pwd = st.text_input("Veuillez entrer le mot de passe administrateur :", type="password")
        if pwd == "angem":
            st.session_state.logged_in = True
            st.rerun()
        elif pwd:
            st.error("Mot de passe incorrect.")
        return

    st.success("✅ Connecté en tant qu'Administrateur")
    if st.button("🚪 Se déconnecter"):
        st.session_state.logged_in = False
        st.rerun()

    try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.warning("Aucune donnée disponible. Veuillez importer des fichiers.")
        return

    # L'AJOUT EST ICI : 4 ONGLETS AU LIEU DE 3 (Garde tout l'existant !)
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Tableau de Bord", "📈 Stats Sur-Mesure", "🔎 Analyses Avancées", "⚙️ Système"])

    # ONGLET 1 : TABLEAU DE BORD CLASSIQUE
    with tab1:
        st.markdown("### 🏆 Indicateurs Clés")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Dossiers Actifs", len(df))
        col2.metric("Crédits PNR Alloués", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
        col3.metric("Fonds Recouvrés", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA", "Remboursements")
        col4.metric("Dettes en Cours", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", "- À recouvrer", delta_color="inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if 'banque_nom' in df.columns and not df['banque_nom'].eq('').all():
                fig1 = px.pie(df[df['banque_nom'] != ''], names='banque_nom', title="Répartition des dossiers par Banque", hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
        with c2:
            if 'secteur' in df.columns and not df['secteur'].eq('').all():
                fig2 = px.bar(df[df['secteur'] != '']['secteur'].value_counts().reset_index(), x='secteur', y='count', title="Dossiers par Secteur", color='secteur')
                st.plotly_chart(fig2, use_container_width=True)

    # ONGLET 2 : STATISTIQUES LIBRES
    with tab2:
        st.markdown("### 🛠️ Créateur de Statistiques Personnalisées")
        st.info("Choisissez les critères ci-dessous pour générer le graphique de votre choix.")
        
        colonnes_groupement = {
            "Par Activité": "activite", "Par Secteur": "secteur", "Par Commune": "commune",
            "Par Daira": "daira", "Par Banque": "banque_nom", "Par Genre": "genre", "Par État de Dette": "etat_dette"
        }
        colonnes_calcul = {
            "Nombre de dossiers": "count", "Somme des PNR (DA)": "montant_pnr", 
            "Somme Recouvrée (DA)": "montant_rembourse", "Somme Reste à Payer (DA)": "reste_rembourser"
        }

        col_a, col_b = st.columns(2)
        axe_x_label = col_a.selectbox("1. Grouper les données :", list(colonnes_groupement.keys()))
        axe_y_label = col_b.selectbox("2. Valeur à calculer :", list(colonnes_calcul.keys()))
        
        axe_x = colonnes_groupement[axe_x_label]
        axe_y = colonnes_calcul[axe_y_label]

        if axe_x in df.columns and not df[axe_x].eq('').all():
            df_clean = df[df[axe_x] != '']
            if axe_y == "count":
                stat_df = df_clean[axe_x].value_counts().reset_index()
                stat_df.columns = [axe_x_label, axe_y_label]
            else:
                df_clean[axe_y] = pd.to_numeric(df_clean[axe_y], errors='coerce').fillna(0)
                stat_df = df_clean.groupby(axe_x)[axe_y].sum().reset_index()
                stat_df.columns = [axe_x_label, axe_y_label]
                stat_df = stat_df.sort_values(by=axe_y_label, ascending=False)

            fig_custom = px.bar(stat_df.head(15), x=axe_x_label, y=axe_y_label, title=f"{axe_y_label} {axe_x_label}", text_auto='.2s', color=axe_x_label)
            st.plotly_chart(fig_custom, use_container_width=True)
            with st.expander("Voir les données en tableau"):
                st.dataframe(stat_df, use_container_width=True)
        else:
            st.warning(f"La colonne {axe_x_label} ne contient pas de données.")

    # ONGLET 3 : NOUVEAU - ANALYSES AVANCÉES
    with tab3:
        st.markdown("### 🧭 Analyses Approfondies de l'Agence")
        
        total_pnr = df['montant_pnr'].astype(float).sum()
        total_remb = df['montant_rembourse'].astype(float).sum()
        taux_recouvrement = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
        
        # Jauge de recouvrement
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = taux_recouvrement,
            title = {'text': "Taux de Recouvrement Global (%)", 'font': {'size': 24}},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#1f2937"},
                'steps': [
                    {'range': [0, 30], 'color': "#ff4b4b"},
                    {'range': [30, 70], 'color': "#ffa421"},
                    {'range': [70, 100], 'color': "#09ab3b"}]
            }
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.markdown("---")
        
        # Ligne : Accompagnateurs et Zones
        c_x, c_y = st.columns(2)
        with c_x:
            st.markdown("#### 👥 Top 10 Accompagnateurs (Volume de dossiers)")
            if 'gestionnaire' in df.columns and not df['gestionnaire'].eq('').all():
                df_gest = df[df['gestionnaire'] != '']
                gest_counts = df_gest['gestionnaire'].value_counts().head(10).reset_index()
                gest_counts.columns = ['Accompagnateur', 'Dossiers gérés']
                fig_gest = px.bar(gest_counts, x='Dossiers gérés', y='Accompagnateur', orientation='h')
                st.plotly_chart(fig_gest, use_container_width=True)
            else:
                st.info("Données des accompagnateurs non disponibles.")
                
        with c_y:
            st.markdown("#### 🗺️ Répartition d'Activité par Zone")
            if 'zone' in df.columns and not df['zone'].eq('').all():
                df_zone = df[df['zone'] != '']
                zone_counts = df_zone['zone'].value_counts().reset_index()
                zone_counts.columns = ['Zone', 'Nombre de Dossiers']
                fig_zone = px.pie(zone_counts, values='Nombre de Dossiers', names='Zone', hole=0.5)
                st.plotly_chart(fig_zone, use_container_width=True)
            else:
                st.info("Données de zonage non disponibles.")

        st.markdown("---")
        st.markdown("#### 🚨 Alertes : Top 10 des plus grandes dettes actives")
        df_dettes = df.copy()
        df_dettes['reste_rembourser'] = pd.to_numeric(df_dettes['reste_rembourser'], errors='coerce').fillna(0)
        df_dettes = df_dettes[df_dettes['reste_rembourser'] > 0]
        if not df_dettes.empty:
            top_dettes = df_dettes.nlargest(10, 'reste_rembourser')[['identifiant', 'nom', 'prenom', 'commune', 'reste_rembourser']]
            top_dettes.columns = ['Identifiant', 'Nom', 'Prénom', 'Commune', 'Reste à Payer (DA)']
            st.dataframe(top_dettes, use_container_width=True, hide_index=True)
        else:
            st.success("Aucune dette détectée dans la base de données !")

    # ONGLET 4 : PARAMÈTRES ET SÉCURITÉ
    with tab4:
        st.markdown("### ⚠️ Zone de Danger")
        st.write("Ces actions sont irréversibles.")
        if st.button("🗑️ Vider entièrement la base de données", type="primary"):
            session = get_session()
            session.query(Dossier).delete()
            session.commit()
            st.warning("Base de données réinitialisée.")
            st.rerun()

# --- DÉMARRAGE ---
page = sidebar_menu()
if page == "🗂️ Consultation Dossiers": page_gestion()
elif page == "📥 Importation Excel": page_import()
elif page == "🔒 Espace Administrateur": page_admin()

# --- FIN DU FICHIER ---
