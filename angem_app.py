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

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Intra-Service ANGEM v6.0", page_icon="🇩🇿", layout="wide", initial_sidebar_state="expanded")

# --- STYLE CSS (Design Moderne) ---
st.markdown("""
<style>
    .stMetric {background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #1f77b4; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .stTabs [aria-selected="true"] {background-color: #f0f2f6; border-bottom: 4px solid #1f77b4; font-weight: bold;}
    .login-box {max-width: 400px; margin: auto; padding: 30px; background-color: #ffffff; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);}
    .doc-box {background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; margin-top: 10px;}
    .alerte-box {background-color: #ffcccc; padding: 15px; border-radius: 8px; border-left: 6px solid #ff0000; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

if not os.path.exists("scans_angem"):
    os.makedirs("scans_angem")

# --- CONNEXION BASE DE DONNÉES SUPABASE ---
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

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id = Column(Integer, primary_key=True)
    identifiant = Column(String, unique=True)
    nom = Column(String)
    mot_de_passe = Column(String)
    role = Column(String)

Base.metadata.create_all(engine)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS statut_dossier VARCHAR DEFAULT 'Phase dépôt du dossier'"))
        conn.execute(text("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS documents VARCHAR DEFAULT ''"))
        conn.commit()
except: pass

def get_session(): return Session()

def init_db_users():
    session = get_session()
    if session.query(UtilisateurAuth).count() == 0:
        utilisateurs_base = [
            UtilisateurAuth(identifiant="admin", nom="Administrateur", mot_de_passe="angem", role="admin"),
            UtilisateurAuth(identifiant="mahrez", nom="M. MAHREZ MOHAMED", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="aitouarab", nom="Mme AIT OUARAB AMINA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="felfoul", nom="FELFOUL Samira", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="medjhoum", nom="MEDJHOUM Raouia", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="chemmamdji", nom="CHEMMAMDJI REDA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="djaoudi", nom="DJAOUDI SARA", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="berrabah", nom="BERRABAH Douadi", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="boulahlib", nom="BOULAHLIB Redouane", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="nasri", nom="NASRI Riym", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="kadri", nom="KADRI Mohamed amine", mot_de_passe="angem2026", role="agent"),
            UtilisateurAuth(identifiant="sekat", nom="SEKAT Manel", mot_de_passe="angem2026", role="agent")
        ]
        session.add_all(utilisateurs_base)
        session.commit()
    session.close()

init_db_users()

LISTE_STATUTS = ["Phase dépôt du dossier", "En attente de la commission d'éligibilité", "Accordé / En cours de financement", "En phase d'exploitation", "Contentieux / Retard de remboursement"]

# --- FONCTIONS PDF ---
def clean_pdf_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')

def generer_fiche_promoteur_pdf(dos):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo_angem.png", x=10, y=8, w=30)
    except: pass
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, "FICHE DE SUIVI PROMOTEUR - ANGEM", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. IDENTIFICATION", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Identifiant : {clean_pdf_text(dos.identifiant)}")
    pdf.cell(90, 8, f"Accompagnateur : {clean_pdf_text(dos.gestionnaire)}", ln=True)
    pdf.cell(100, 8, f"Nom & Prenom : {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}")
    pdf.cell(90, 8, f"Telephone : {clean_pdf_text(dos.telephone)}", ln=True)
    pdf.cell(0, 8, f"Adresse : {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. PROJET & FINANCEMENT", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Activite : {clean_pdf_text(dos.activite)}")
    pdf.cell(90, 8, f"Secteur : {clean_pdf_text(dos.secteur)}", ln=True)
    pdf.cell(100, 8, f"Statut du dossier : {clean_pdf_text(dos.statut_dossier)}", ln=True)
    pdf.cell(65, 8, f"Credit PNR : {dos.montant_pnr:,.0f} DA")
    pdf.cell(65, 8, f"Apport : {dos.apport_personnel:,.0f} DA")
    pdf.cell(60, 8, f"Banque : {dos.credit_bancaire:,.0f} DA", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. RECOUVREMENT", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Montant Recouvre : {dos.montant_rembourse:,.0f} DA")
    pdf.cell(90, 8, f"Reste a Rembourser : {dos.reste_rembourser:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Echeances tombees : {clean_pdf_text(dos.nb_echeance_tombee)}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "4. NOTES DE VISITE SUR SITE (A remplir manuellement)", ln=True, border='B')
    pdf.ln(5)
    for _ in range(5): pdf.cell(0, 10, "......................................................................................................................................................", ln=True)
    
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
    
    # Section Finance
    total_pnr = df['montant_pnr'].astype(float).sum()
    total_remb = df['montant_rembourse'].astype(float).sum()
    total_reste = df['reste_rembourser'].astype(float).sum()
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. RESUME FINANCIER GLOBAL", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Total Credit PNR Engage : {total_pnr:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Montant Recouvre : {total_remb:,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Dette Globale (Reste a payer) : {total_reste:,.0f} DA", ln=True)
    pdf.ln(5)

    # Section Pipeline
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. RAPPORT DU PIPELINE DES DOSSIERS", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    statuts = df['statut_dossier'].value_counts()
    for stat, count in statuts.items():
        pdf.cell(0, 8, f"- {clean_pdf_text(stat)} : {count} dossiers", ln=True)
    pdf.ln(5)
    
    # Section Banques
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. DOSSIERS PAR BANQUE", ln=True, border='B')
    pdf.set_font("Arial", '', 11)
    if 'banque_nom' in df.columns:
        banques = df[df['banque_nom'] != '']['banque_nom'].value_counts()
        for bq, count in banques.items():
            pdf.cell(0, 8, f"- {clean_pdf_text(bq)} : {count} dossiers", ln=True)
            
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: bytes_pdf = f.read()
    return bytes_pdf

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
    return nom_excel.title()

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
    'commune': ['COMMUNE', 'APC'],
    'banque_nom': ['BANQUEDUPROMOTEUR', 'BANQUECCP', 'BANQUE'],
    'montant_pnr': ['PNR', 'MONTANTPNR29', 'MTDUPNR', 'MONTANT'],
    'montant_rembourse': ['TOTALREMB', 'TOTALVERS', 'VERSEMENT'],
    'reste_rembourser': ['MONTANTRESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'nb_echeance_tombee': ['NBRECHTOMB', 'ECHEANCESTOMBEES'],
}
COLONNES_ARGENT = ['montant_pnr', 'montant_rembourse', 'reste_rembourser']

if 'user' not in st.session_state: st.session_state.user = None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_angem.png", width=250)
        except: pass
        
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.subheader("🔐 Accès Intra-Service")
        username = st.text_input("Identifiant", placeholder="Ex: admin ou nasri")
        password = st.text_input("Mot de passe", type="password")
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            user_input = username.lower().strip()
            session = get_session()
            user_db = session.query(UtilisateurAuth).filter_by(identifiant=user_input).first()
            session.close()
            
            if user_db and user_db.mot_de_passe == password:
                st.session_state.user = {"identifiant": user_db.identifiant, "nom": user_db.nom, "role": user_db.role}
                st.rerun()
            else: st.error("Identifiant ou mot de passe incorrect.")
        st.markdown("</div>", unsafe_allow_html=True)

def sidebar_menu():
    try: st.sidebar.image("logo_angem.png", use_container_width=True)
    except: pass
    
    st.sidebar.markdown(f"**👤 Connecté :** {st.session_state.user['nom']}")
    st.sidebar.markdown("---")
    
    options = ["🗂️ Mes Dossiers Promoteurs"]
    if st.session_state.user['role'] == "admin":
        options = ["📊 Espace Administrateur", "🗂️ Tous les Dossiers", "📥 Importation des Fichiers"]
        
    choix = st.sidebar.radio("📌 Navigation :", options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state.user = None
        st.rerun()
    return choix

def page_gestion(vue_admin=False):
    st.title("🗂️ Suivi des Dossiers Promoteurs")
    
    try: df = pd.read_sql_query("SELECT * FROM dossiers ORDER BY id DESC", con=engine).fillna('')
    except: df = pd.DataFrame()

    if df.empty:
        st.info("📌 Aucun dossier trouvé.")
        return

    if not vue_admin: 
        df = df[df['gestionnaire'] == st.session_state.user['nom']]
        
        # --- NOUVEAUTÉ : ÉTAT D'ALERTE CONTENTIEUX ---
        dossiers_alerte = df[df['statut_dossier'] == "Contentieux / Retard de remboursement"]
        if not dossiers_alerte.empty:
            st.markdown(f"<div class='alerte-box'><h4>🚨 ALERTES CONTENTIEUX</h4>Vous avez <b>{len(dossiers_alerte)} dossier(s)</b> nécessitant un appel ou une intervention prioritaire aujourd'hui.</div>", unsafe_allow_html=True)

    search = st.text_input("🔍 Chercher un dossier :", placeholder="Nom, Identifiant...")
    df_filtered = df.copy()
    if search:
        mask = df_filtered.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        df_filtered = df_filtered[mask]

    try:
        df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=engine)
        liste_agents = [""] + df_agents['nom'].tolist()
    except: liste_agents = [""]

    st.success(f"{len(df_filtered)} dossiers affichés.")

    edited_df = st.data_editor(
        df_filtered, use_container_width=True, hide_index=True, height=350,
        column_config={
            "id": None, "documents": None,
            "identifiant": st.column_config.TextColumn("Identifiant", disabled=True),
            "nom": "Nom Promoteur",
            "statut_dossier": st.column_config.SelectboxColumn("🚦 Statut", options=LISTE_STATUTS, width="large"),
            "gestionnaire": st.column_config.SelectboxColumn("👨‍💼 Accompagnateur", options=liste_agents, disabled=not vue_admin),
            "montant_pnr": st.column_config.NumberColumn("PNR", format="%d DA", disabled=True),
            "montant_rembourse": st.column_config.NumberColumn("Recouvré", format="%d DA", disabled=True),
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
            st.toast("✅ Modifications sauvegardées avec succès !")
            st.rerun()
        except Exception as e: session.rollback(); st.error(f"Erreur : {e}")
        finally: session.close()

    st.markdown("---")
    
    st.subheader("📂 Gestion individuelle : Scans et Fiche PDF")
    options_dossiers = ["Sélectionnez un dossier..."] + df_filtered.apply(lambda x: f"{x['identifiant']} - {x['nom']} {x['prenom']}", axis=1).tolist()
    dossier_choisi = st.selectbox("Choisissez le promoteur pour voir ses détails :", options_dossiers)

    if dossier_choisi != "Sélectionnez un dossier...":
        identifiant_choisi = dossier_choisi.split(" - ")[0]
        session = get_session()
        dos_db = session.query(Dossier).filter_by(identifiant=identifiant_choisi).first()
        
        if dos_db:
            st.markdown("<div class='doc-box'>", unsafe_allow_html=True)
            col_pdf, col_scan = st.columns(2)
            
            with col_pdf:
                st.markdown("#### 📄 Fiche de Suivi")
                pdf_bytes = generer_fiche_promoteur_pdf(dos_db)
                st.download_button(
                    label="📥 Imprimer la Fiche PDF pour visite sur site",
                    data=pdf_bytes, file_name=f"Fiche_Suivi_{dos_db.identifiant}.pdf", mime="application/pdf"
                )
            
            with col_scan:
                st.markdown("#### 📎 Ajouter un scan")
                nouveau_scan = st.file_uploader("Scan CNI, Facture, PV...", type=['pdf', 'jpg', 'png'])
                if nouveau_scan is not None:
                    if st.button("Sauvegarder la pièce jointe"):
                        nom_fichier_propre = f"{dos_db.identifiant}_{nouveau_scan.name}"
                        chemin_sauvegarde = os.path.join("scans_angem", nom_fichier_propre)
                        with open(chemin_sauvegarde, "wb") as f: f.write(nouveau_scan.getbuffer())
                        docs_actuels = dos_db.documents if dos_db.documents else ""
                        dos_db.documents = docs_actuels + nom_fichier_propre + "|"
                        session.commit()
                        st.success("Pièce jointe ajoutée !")
                        st.rerun()

            st.markdown("**📂 Pièces jointes actuelles :**")
            if dos_db.documents:
                for doc in dos_db.documents.split("|"):
                    if doc: st.markdown(f"- 🗎 `{doc}`")
            else: st.info("Aucune pièce jointe.")
            st.markdown("</div>", unsafe_allow_html=True)
        session.close()

def page_import():
    st.title("📥 Moteur d'Intégration Excel")
    uploaded_file = st.file_uploader("📂 Glissez le fichier Excel", type=['xlsx', 'xls', 'csv'])
    if uploaded_file and st.button("🚀 Lancer l'Intégration", type="primary"):
        session = get_session()
        try:
            xl = pd.read_excel(uploaded_file, sheet_name=None, header=None, dtype=str)
            agents_db = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_noms = [a.nom for a in agents_db]

            with st.status("Analyse et fusion des données...", expanded=True) as status:
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
                        if not ident: continue
                        exist = session.query(Dossier).filter_by(identifiant=ident).first()
                        if exist:
                            for k, v in data.items(): setattr(exist, k, v)
                            count_upd += 1
                        else:
                            session.add(Dossier(**data))
                            count_add += 1
                session.commit()
                status.update(label=f"Opération terminée : {count_add} créés, {count_upd} mis à jour.", state="complete")
            st.balloons()
        except Exception as e: session.rollback(); st.error(f"Erreur d'importation : {e}")
        finally: session.close()

def page_admin():
    st.title("📊 Espace Administrateur & Direction")
    tab1, tab2, tab3 = st.tabs(["📈 Rapports et Bilans", "🔐 Gestion des Accès", "⚙️ Système"])

    with tab1:
        try: df = pd.read_sql_query("SELECT * FROM dossiers", con=engine).fillna('')
        except: df = pd.DataFrame()
        
        if df.empty: st.warning("La base de dossiers est vide.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Dossiers", len(df))
            c2.metric("Crédit PNR Engagé", f"{df['montant_pnr'].astype(float).sum():,.0f} DA")
            c3.metric("Recouvrement", f"{df['montant_rembourse'].astype(float).sum():,.0f} DA")
            c4.metric("Dette Globale", f"{df['reste_rembourser'].astype(float).sum():,.0f} DA", delta_color="inverse")
            
            # --- NOUVEAUTÉ : LE BILAN PDF COMPLET ---
            st.markdown("### Exportation pour la hiérarchie")
            pdf_bilan = generer_bilan_global_pdf(df)
            st.download_button(
                label="📥 Télécharger le Rapport Complet (Finances, Pipeline, Banques) en PDF",
                data=pdf_bilan, file_name="Rapport_Direction_ANGEM.pdf", mime="application/pdf", type="primary"
            )
            st.markdown("---")
            
            # --- NOUVEAUTÉ : GRAPHIQUES GÉOGRAPHIQUES ET BANCAIRES ---
            st.markdown("### Cartographie & Suivi")
            col_l, col_r = st.columns(2)
            with col_l:
                if 'statut_dossier' in df.columns: st.plotly_chart(px.pie(df, names='statut_dossier', title="Le Pipeline (Statuts)", hole=0.3), use_container_width=True)
                if 'banque_nom' in df.columns: st.plotly_chart(px.bar(df[df['banque_nom'] != '']['banque_nom'].value_counts().reset_index(), x='banque_nom', y='count', title="Répartition par Banque"), use_container_width=True)
            with col_r:
                if 'commune' in df.columns: st.plotly_chart(px.bar(df[df['commune'] != '']['commune'].value_counts().reset_index(), x='count', y='commune', orientation='h', title="Répartition Géographique (Communes)"), use_container_width=True)
                st.plotly_chart(px.bar(df[df['gestionnaire'] != '']['gestionnaire'].value_counts().reset_index(), x='gestionnaire', y='count', title="Charge par Accompagnateur"), use_container_width=True)

    with tab2:
        st.markdown("### 🔑 Liste des Accompagnateurs et Mots de passe")
        try: df_users = pd.read_sql_query("SELECT id, identifiant, nom, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", con=engine)
        except: df_users = pd.DataFrame()
            
        if not df_users.empty:
            edited_users = st.data_editor(
                df_users, use_container_width=True, hide_index=True,
                column_config={"id": None, "identifiant": st.column_config.TextColumn("Identifiant (Login)", disabled=True), "nom": st.column_config.TextColumn("Nom de l'Accompagnateur", disabled=True), "mot_de_passe": st.column_config.TextColumn("Mot de passe (Modifiable)")}
            )
            if st.button("💾 Sauvegarder les mots de passe"):
                session = get_session()
                try:
                    for _, row in edited_users.iterrows():
                        user_db = session.query(UtilisateurAuth).get(row['id'])
                        if user_db: user_db.mot_de_passe = row['mot_de_passe']
                    session.commit()
                    st.success("✅ Mots de passe mis à jour !")
                except Exception as e: session.rollback(); st.error(f"Erreur : {e}")
                finally: session.close()

    with tab3:
        st.error("Zone de danger")
        if st.button("🗑️ Vider la base de données (Dossiers uniquement)", type="primary"):
            session = get_session()
            session.query(Dossier).delete(); session.commit(); session.close()
            st.rerun()

# --- DEMARRAGE DE L'APPLICATION ---
if st.session_state.user is None: login_page()
else:
    page = sidebar_menu()
    if page == "🗂️ Tous les Dossiers": page_gestion(vue_admin=True)
    elif page == "🗂️ Mes Dossiers Promoteurs": page_gestion(vue_admin=False)
    elif page == "📥 Importation des Fichiers": page_import()
    elif page == "📊 Espace Administrateur": page_admin()
