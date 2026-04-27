import streamlit as st
import pandas as pd
import bcrypt
import unicodedata
import re
import io
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import sessionmaker, declarative_base
from fpdf import FPDF
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="ANGEM Workspace Ultra",
    page_icon="🇩🇿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Clés depuis variables d'environnement (jamais en dur) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://greyjhgiytajxpvucbrk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require")

LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]
LISTE_STATUTS = [
    "Phase dépôt du dossier",
    "En attente de la commission",
    "Accordé / En cours",
    "En phase d'exploitation",
    "Contentieux / Retard"
]
COLONNES_ARGENT = ['montant_pnr', 'montant_rembourse', 'reste_rembourser',
                   'total_echue', 'apport_personnel', 'credit_bancaire']
MAPPING_CONFIG_KEYWORDS = {
    'identifiant':         ['IDENTIFIANT', 'CNI', 'NCINPC', 'NAT', 'ID'],
    'nom':                 ['NOMETPRENOM', 'NOM', 'PROMOTEUR'],
    'prenom':              ['PRENOM'],
    'date_naissance':      ['NAISSANCE', 'DATENAISS', 'NELE'],
    'adresse':             ['ADRESSE', 'LIEU'],
    'telephone':           ['TEL', 'MOB', 'TELEPHONE'],
    'commune':             ['COMMUNE', 'APC'],
    'daira':               ['DAIRA'],
    'type_dispositif':     ['TYPE', 'FINANCEMENT', 'DISPOSITIF'],
    'activite':            ['ACTIVITE', 'PROJET', 'INTITULE'],
    'gestionnaire':        ['GEST', 'ACCOMPAGNATEUR', 'AGENT'],
    'banque_nom':          ['BANQUE', 'CCP', 'AGENCE'],
    'num_ordre_versement': ['NUMOV', 'ORDREVERSEMENT', 'OV'],
    'date_financement':    ['DATEOV', 'DATEVIREMENT', 'DATEFINAN'],
    'debut_consommation':  ['DEBUTCONSOM', 'CONSOMMATION'],
    'montant_pnr':         ['PNR', 'MONTANTPNR', 'MONTANT', 'CREDIT'],
    'nb_echeance_tombee':  ['ECHTOMB', 'ECHEANCES', 'NBRECHTOMB'],
    'date_ech_tomb':       ['DATEECHTOMB', 'DATEECHEANCETOMBEE', 'DATEECH'],
    'prochaine_ech':       ['PROCHAINEECH', 'PROCHECH'],
    'total_echue':         ['TOTALECHUE', 'MONTECHEAN'],
    'montant_rembourse':   ['TOTALREMB', 'VERSEMENT', 'REMBOURSE', 'TOTALVERS'],
    'reste_rembourser':    ['RESTAREMB', 'MONTANTRESTA', 'RESTE'],
    'etat_dette':          ['ETATDETTE', 'ETAT'],
    'observations':        ['OBS', 'OBSERVATION', 'OBSERVATIONS'],
    'anticip':             ['ANTICIP', 'ANTICIPATION'],
    'ech_anticip':         ['ECHANTICIP', 'ECHEANCEANTICIP'],
}

# ==========================================
# 2. SESSION STATE
# ==========================================
for k, v in [('user', None), ('portal_selection', None), ('search_query', "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# Thème dynamique
if st.session_state.user:
    theme_color = "#1f77b4" if st.session_state.user.get('env') == "PNR PROJET" else "#28a745"
    theme_bg    = "#f4f9fc" if st.session_state.user.get('env') == "PNR PROJET" else "#f4fcf5"
else:
    theme_color, theme_bg = "#2c3e50", "#f8f9fa"

# ==========================================
# 3. CSS
# ==========================================
st.markdown(f"""
<style>
    .stApp {{ background-color:{theme_bg}; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; }}
    .modern-card {{ background:#fff; padding:25px; border-radius:16px;
        box-shadow:0 8px 24px rgba(0,0,0,.04); margin:15px 0 25px;
        border:1px solid #edf2f7; border-top:4px solid {theme_color};
        transition:transform .2s,box-shadow .2s; }}
    .modern-card:hover {{ transform:translateY(-2px); box-shadow:0 12px 32px rgba(0,0,0,.08); }}
    .metric-card {{ background:#fff; border-radius:16px; padding:20px;
        box-shadow:0 4px 15px rgba(0,0,0,.03); border-left:6px solid {theme_color};
        display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; }}
    .metric-value {{ font-size:26px; font-weight:800; color:#1e293b; margin-top:5px; }}
    .metric-label {{ font-size:13px; color:#64748b; text-transform:uppercase; font-weight:700; letter-spacing:.5px; }}
    .metric-danger {{ border-left-color:#ef4444; }}
    .profil-header {{ background:linear-gradient(135deg,#fff 0%,#f8fafc 100%); padding:25px;
        border-radius:12px; border-left:8px solid {theme_color}; margin-bottom:15px;
        box-shadow:0 4px 15px rgba(0,0,0,.05); }}
    .block-finance {{ background:#eff6ff; border-left:5px solid #3b82f6; padding:15px; border-radius:8px; margin-bottom:15px; }}
    .block-recouvrement {{ background:#f0fdf4; border-left:5px solid #22c55e; padding:15px; border-radius:8px; margin-bottom:15px; }}
    .block-title {{ font-weight:bold; color:#1e293b; margin-bottom:10px; font-size:16px; text-transform:uppercase; }}
    .action-btn-container {{ display:flex; gap:12px; margin:15px 0 25px; flex-wrap:wrap; }}
    .btn-action {{ flex:1; min-width:160px; padding:12px 20px; border-radius:10px; text-decoration:none;
        font-weight:bold; text-align:center; color:white!important; transition:all .3s;
        box-shadow:0 4px 6px rgba(0,0,0,.1); display:flex; align-items:center; justify-content:center; gap:8px; font-size:15px; }}
    .btn-call {{ background:#3b82f6; }} .btn-call:hover {{ background:#2563eb; transform:translateY(-2px); }}
    .btn-wa   {{ background:#22c55e; }} .btn-wa:hover   {{ background:#16a34a; transform:translateY(-2px); }}
    .btn-maps {{ background:#ef4444; }} .btn-maps:hover {{ background:#dc2626; transform:translateY(-2px); }}
    .search-title {{ color:{theme_color}; font-weight:800; font-size:20px; margin-bottom:15px;
        text-transform:uppercase; letter-spacing:1px; }}
    .alerte-nouveau {{ background:#f0fdf4; border-left:6px solid #22c55e; padding:15px 20px;
        border-radius:8px; color:#15803d; font-weight:600; margin-bottom:20px; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. BASE DE DONNÉES (cache engine)
# ==========================================
Base = declarative_base()

@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True,
                         pool_size=5, max_overflow=10)

def get_session():
    return sessionmaker(bind=get_engine())()

class Dossier(Base):
    __tablename__ = 'dossiers'
    id                   = Column(Integer, primary_key=True)
    identifiant          = Column(String, index=True, default="")
    type_dispositif      = Column(String, default="PNR PROJET")
    nom                  = Column(String, default="")
    prenom               = Column(String, default="")
    genre                = Column(String, default="")
    date_naissance       = Column(String, default="")
    adresse              = Column(String, default="")
    telephone            = Column(String, default="")
    niveau_instruction   = Column(String, default="")
    age                  = Column(String, default="")
    activite             = Column(String, default="")
    code_activite        = Column(String, default="")
    secteur              = Column(String, default="")
    daira                = Column(String, default="")
    commune              = Column(String, default="")
    gestionnaire         = Column(String, default="")
    zone                 = Column(String, default="")
    montant_pnr          = Column(Float, default=0.0)
    apport_personnel     = Column(Float, default=0.0)
    credit_bancaire      = Column(Float, default=0.0)
    montant_total_credit = Column(Float, default=0.0)
    banque_nom           = Column(String, default="")
    agence_bancaire      = Column(String, default="")
    numero_compte        = Column(String, default="")
    num_ordre_versement  = Column(String, default="")
    date_financement     = Column(String, default="")
    debut_consommation   = Column(String, default="")
    montant_rembourse    = Column(Float, default=0.0)
    reste_rembourser     = Column(Float, default=0.0)
    nb_echeance_tombee   = Column(String, default="")
    date_ech_tomb        = Column(String, default="")
    prochaine_ech        = Column(String, default="")
    total_echue          = Column(Float, default=0.0)
    etat_dette           = Column(String, default="")
    observations         = Column(String, default="")
    anticip              = Column(String, default="")
    ech_anticip          = Column(String, default="")
    statut_dossier       = Column(String, default="Phase dépôt du dossier")
    documents            = Column(String, default="")
    historique_visites   = Column(String, default="")
    prochaine_visite     = Column(String, default="")
    est_nouveau          = Column(String, default="NON")
    in_finance           = Column(String, default="NON")
    in_recouvrement      = Column(String, default="NON")

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id           = Column(Integer, primary_key=True)
    identifiant  = Column(String, unique=True)
    nom          = Column(String)
    mot_de_passe = Column(String)
    role         = Column(String)
    daira        = Column(String, default="")

def _hash(mdp: str) -> str:
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt()).decode()

def _check(mdp: str, hashed: str) -> bool:
    # Compatible anciens mots de passe en clair
    if not hashed.startswith("$2"):
        return mdp == hashed
    return bcrypt.checkpw(mdp.encode(), hashed.encode())

@st.cache_resource
def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)

    # Migrations sans erreur silencieuse
    with engine.begin() as conn:
        for col in ["type_dispositif","date_naissance","num_ordre_versement",
                    "debut_consommation","etat_dette","est_nouveau","date_ech_tomb",
                    "prochaine_ech","in_finance","in_recouvrement","observations",
                    "anticip","ech_anticip"]:
            conn.execute(text(
                f"ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS {col} VARCHAR DEFAULT ''"
            ))
        for col in ["apport_personnel","total_echue","credit_bancaire"]:
            conn.execute(text(
                f"ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS {col} FLOAT DEFAULT 0.0"
            ))
        conn.execute(text(
            "UPDATE dossiers SET in_finance='OUI' WHERE in_finance='' OR in_finance IS NULL"
        ))
        conn.execute(text(
            "UPDATE dossiers SET in_recouvrement='OUI' WHERE in_recouvrement='' OR in_recouvrement IS NULL"
        ))

    # Comptes par défaut avec mots de passe hashés
    session = get_session()
    try:
        for ident, nom, mdp, role in [
            ("admin",   "Administrateur",  "angem",     "admin"),
            ("finance", "Service Finance", "angem",     "finance"),
        ]:
            u = session.query(UtilisateurAuth).filter_by(identifiant=ident).first()
            if not u:
                session.add(UtilisateurAuth(
                    identifiant=ident, nom=nom,
                    mot_de_passe=_hash(mdp), role=role
                ))
            elif not u.mot_de_passe.startswith("$2"):
                # Migration automatique des anciens mdp en clair
                u.mot_de_passe = _hash(u.mot_de_passe)
        session.commit()
    finally:
        session.close()

init_db()

# ==========================================
# 5. CLIENT SUPABASE (singleton)
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 6. UTILITAIRES
# ==========================================
def clean_header(v: str) -> str:
    return ''.join(filter(str.isalnum, str(v).upper()))

def clean_pdf_text(t) -> str:
    if not t: return ""
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('utf-8')

def clean_money(v):
    if pd.isna(v) or str(v).strip() == '': return None
    try:
        return float(re.sub(r'[^\d\.-]', '',
                            str(v).replace('DA','').replace(' ','').replace(',','.')))
    except Exception:
        return None

def clean_identifiant(v) -> str:
    s = str(v).strip().upper()
    if 'E' in s and s.replace('E','').replace('.','').replace('+','').isdigit():
        try: return f"{float(s):.0f}"
        except Exception: pass
    return s[:-2] if s.endswith('.0') else s

def trouver_agent_intelligent(nom_excel, liste: list) -> str:
    ne = str(nom_excel).strip().upper()
    if not ne or ne in ("NAN","NONE",""): return ""
    for a in liste:
        if a.upper() in ne or ne in a.upper(): return a
    return ne

def calculer_alerte_bool(row) -> bool:
    ech = str(row.get('nb_echeance_tombee', '')).strip()
    if any(c.isdigit() for c in ech):
        m = re.search(r'\d+', ech)
        if m and int(m.group()) > 0: return True
    return (row.get('statut_dossier') == "Contentieux / Retard"
            or row.get('etat_dette') == "CONTENTIEUX")

def safe_read_dataframe(file_obj) -> pd.DataFrame:
    if file_obj.name.lower().endswith('.csv'):
        for enc, sep in [('utf-8',';'),('latin1',';'),('utf-8',',')]:
            try:
                file_obj.seek(0)
                return pd.read_csv(file_obj, sep=sep, encoding=enc,
                                   header=None, dtype=str, on_bad_lines='skip')
            except Exception:
                continue
    file_obj.seek(0)
    return pd.read_excel(file_obj, header=None, dtype=str)

def get_header_row(df_raw: pd.DataFrame) -> int:
    mots = {"IDENTIFIANT","CNI","NOM","GEST","PRENOM","ID","TEL","TELEPHONE","PNR","MONTANT"}
    for i in range(min(30, len(df_raw))):
        row_cl = {clean_header(str(x)) for x in df_raw.iloc[i].values}
        if row_cl & mots: return i
    return 0

def preparer_df_import(file_obj):
    df_raw = safe_read_dataframe(file_obj).fillna('')
    hi = get_header_row(df_raw)
    df = df_raw.iloc[hi:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    return df, ["-- Ignorer --"] + list(df.columns)

def auto_map_index(db_field: str, df_cols: list) -> int:
    kws = MAPPING_CONFIG_KEYWORDS.get(db_field, [])
    for i, col in enumerate(df_cols):
        if any(kw in clean_header(col) for kw in kws):
            return i + 1
    return 0

# ==========================================
# 7. PDF
# ==========================================
def _pdf_bytes(pdf: FPDF) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return open(tmp.name, "rb").read()

def generer_fiche_promoteur_pdf(dos) -> bytes:
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial",'B',16)
    pdf.cell(0,15,"FICHE OFFICIELLE PROMOTEUR - ANGEM",ln=True,align='C')
    for titre, lignes in [
        ("1. IDENTIFICATION", [
            (f"ID : {clean_pdf_text(dos.identifiant)}", f"Agent : {clean_pdf_text(dos.gestionnaire)}"),
            (f"Nom : {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", f"Tel : {clean_pdf_text(dos.telephone)}"),
        ]),
        ("2. FINANCEMENT", [
            (f"Dispositif : {clean_pdf_text(dos.type_dispositif)}", f"Banque : {clean_pdf_text(dos.banque_nom)}"),
            (f"Activite : {clean_pdf_text(dos.activite)}", f"Num OV : {clean_pdf_text(dos.num_ordre_versement)}"),
        ]),
        ("3. RECOUVREMENT", [
            (f"Rembourse : {(dos.montant_rembourse or 0):,.0f} DA", f"Reste : {(dos.reste_rembourser or 0):,.0f} DA"),
            (f"Ech. Tombees : {clean_pdf_text(dos.nb_echeance_tombee)}", f"Echue : {(dos.total_echue or 0):,.0f} DA"),
        ]),
    ]:
        pdf.set_font("Arial",'B',11)
        pdf.cell(0,8,titre,border=1,ln=True,fill=True)
        pdf.set_font("Arial",'',10)
        for g,d in lignes:
            pdf.cell(95,8,g,border='L'); pdf.cell(95,8,d,border='R',ln=True)
        if titre == "2. FINANCEMENT":
            pdf.cell(0,8,f"Credit PNR : {(dos.montant_pnr or 0):,.0f} DA",border='LRB',ln=True)
        elif titre == "3. RECOUVREMENT":
            pdf.cell(0,8,f"Etat : {clean_pdf_text(dos.etat_dette)} | Prochaine : {clean_pdf_text(dos.prochaine_ech)}",border='LRB',ln=True)
        pdf.ln(3)
    return _pdf_bytes(pdf)

def generer_rapport_global_pdf(df) -> bytes:
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial",'B',16)
    pdf.cell(0,20,"ETAT GLOBAL DES DOSSIERS - ANGEM",ln=True,align='C')
    pdf.set_font("Arial",'',12)
    pdf.cell(0,10,f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",ln=True)
    pdf.cell(0,10,f"Total Dossiers : {len(df)}",ln=True)
    for label, col in [("PNR Engage","montant_pnr"),("Total Recouvre","montant_rembourse"),("Reste a Recouvrer","reste_rembourser")]:
        pdf.cell(0,10,f"{label} : {df[col].astype(float).sum():,.0f} DA",ln=True)
    return _pdf_bytes(pdf)

def generer_creances_pdf(df) -> bytes:
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial",'B',16); pdf.set_text_color(200,0,0)
    pdf.cell(0,20,"DOSSIERS EN SOUFFRANCE - ANGEM",ln=True,align='C')
    pdf.set_text_color(0,0,0); pdf.set_font("Arial",'',10)
    for _,row in df[df.apply(calculer_alerte_bool,axis=1)].iterrows():
        pdf.cell(0,8,
            f"ID:{row['identifiant']} | {clean_pdf_text(row['nom'])} | "
            f"Reste:{float(row.get('reste_rembourser') or 0):,.0f} DA | "
            f"Agent:{clean_pdf_text(row['gestionnaire'])}",
            ln=True,border='B')
    return _pdf_bytes(pdf)

# ==========================================
# 8. REQUÊTES DONNÉES (requêtes paramétrées)
# ==========================================
@st.cache_data(ttl=30)
def charger_dossiers(env: str, badge: str) -> pd.DataFrame:
    """Cache 30 secondes — requête paramétrée (anti-injection SQL)."""
    q = text("SELECT * FROM dossiers WHERE type_dispositif=:env AND "
             + badge + "='OUI' ORDER BY id DESC")
    return pd.read_sql_query(q, con=get_engine(), params={"env": env}).fillna('')

@st.cache_data(ttl=60)
def charger_agents_noms() -> list:
    try:
        df = pd.read_sql_query(
            "SELECT nom FROM utilisateurs_auth WHERE role='agent'", con=get_engine()
        )
        return df['nom'].dropna().tolist()
    except Exception:
        return []

def invalider_cache():
    charger_dossiers.clear()
    charger_agents_noms.clear()

# ==========================================
# 9. AUTHENTIFICATION
# ==========================================
def login_page():
    st.markdown("<br><h2 style='text-align:center;color:#1e293b;font-weight:800;'>Portail de Connexion</h2>",
                unsafe_allow_html=True)

    if st.session_state.portal_selection is None:
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("👩‍💻\n\nAccompagnateurs", use_container_width=True):
                st.session_state.portal_selection = "agent"; st.rerun()
        with c2:
            if st.button("💰\n\nService Finance", use_container_width=True):
                st.session_state.portal_selection = "finance"; st.rerun()
        with c3:
            if st.button("👑\n\nDirection & Admin", use_container_width=True):
                st.session_state.portal_selection = "admin"; st.rerun()
    else:
        if st.button("⬅️ Retour"):
            st.session_state.portal_selection = None; st.rerun()

        session = get_session()
        try:
            users = session.query(UtilisateurAuth).filter_by(
                role=st.session_state.portal_selection).all()
        finally:
            session.close()

        if not users:
            st.warning("Aucun compte pour ce portail.")
            return

        st.markdown("<div class='modern-card' style='max-width:500px;margin:0 auto;'>",
                    unsafe_allow_html=True)
        nom = st.selectbox("👤 Profil", [u.nom for u in users])
        pwd = st.text_input("🔑 Mot de passe", type="password")
        env = st.selectbox("🏢 Dispositif", ["PNR PROJET", "PNR AMP"])

        if st.button("🚀 Connexion", type="primary", use_container_width=True):
            user_db = next((u for u in users if u.nom == nom), None)
            if user_db and _check(pwd, user_db.mot_de_passe):
                # Migration mdp en clair → hashé
                if not user_db.mot_de_passe.startswith("$2"):
                    s = get_session()
                    try:
                        u = s.get(UtilisateurAuth, user_db.id)
                        u.mot_de_passe = _hash(pwd); s.commit()
                    finally:
                        s.close()
                st.session_state.user = {
                    "nom": user_db.nom, "role": user_db.role,
                    "daira": user_db.daira, "env": env,
                    "id": user_db.id
                }
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 10. SIDEBAR
# ==========================================
def sidebar_menu() -> str:
    role  = st.session_state.user['role']
    env   = st.session_state.user['env']
    daira = st.session_state.user.get('daira', '')

    st.sidebar.markdown(f"""
    <div style='background:#fff;padding:20px;border-radius:16px;border:1px solid #e2e8f0;
         text-align:center;margin-bottom:25px;'>
      <div style='font-size:30px;'>👤</div>
      <div style='font-weight:800;'>{st.session_state.user['nom']}</div>
      <div style='color:#64748b;font-size:12px;'>{daira}</div>
      <div style='margin-top:5px;background:{theme_color};color:white;padding:4px;
           border-radius:10px;font-size:11px;'>{env}</div>
    </div>""", unsafe_allow_html=True)

    if role == "finance":
        opts = ["📥 Import Financement", "🗂️ Vue Financement"]
    elif role == "admin":
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement",
                "📊 Supervision Direction", "⚙️ Intégration Admin"]
    else:
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement", "🗑️ Corbeille"]

    choice = st.sidebar.radio("Navigation", opts, label_visibility="collapsed")
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.session_state.portal_selection = None
        st.rerun()
    return choice

# ==========================================
# 11. PROFIL COMPLET
# ==========================================
def afficher_profil_complet(dos_id: int):
    session = get_session()
    try:
        dos = session.get(Dossier, dos_id)
        if not dos: return

        # Marquer comme lu
        if dos.est_nouveau == "OUI" and dos.gestionnaire == st.session_state.user['nom']:
            dos.est_nouveau = "NON"; session.commit()

        taux = (dos.montant_rembourse / dos.montant_pnr) if (dos.montant_pnr or 0) > 0 else 0

        st.markdown(f"""
        <div class='profil-header'>
          <div><h2 style='margin:0;'>{dos.nom} {dos.prenom}</h2>
          <p style='margin:0;'>ID: {dos.identifiant} | {dos.activite}</p></div>
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class='block-finance'>
              <div class='block-title'>🏦 Financement</div>
              <b>PNR :</b> {(dos.montant_pnr or 0):,.0f} DA<br>
              <b>OV :</b> {dos.num_ordre_versement}<br>
              <b>Banque :</b> {dos.banque_nom}
            </div>""", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class='block-recouvrement'>
              <div class='block-title'>📈 Recouvrement</div>
              <b>Remboursé :</b> {(dos.montant_rembourse or 0):,.0f} DA<br>
              <b>Reste :</b> <span style='color:#dc2626;'>{(dos.reste_rembourser or 0):,.0f} DA</span><br>
              <b>Échue :</b> {(dos.total_echue or 0):,.0f} DA<br>
              <b>Échéances :</b> {dos.nb_echeance_tombee} ({dos.date_ech_tomb})<br>
              <b>État :</b> {dos.etat_dette}<br>
              <b>Anticipation :</b> {dos.anticip} | <b>Ech. Anticip :</b> {dos.ech_anticip}
            </div>""", unsafe_allow_html=True)
            st.progress(min(taux, 1.0))
            st.caption(f"Progression remboursement : {taux*100:.1f}%")

        # Boutons contact
        tel = re.sub(r'\D', '', str(dos.telephone or ""))
        st.markdown("<div class='action-btn-container'>", unsafe_allow_html=True)
        if len(tel) >= 9:
            num_wa = '213' + tel[1:] if tel.startswith('0') else tel
            st.markdown(f"<a href='tel:{tel}' class='btn-action btn-call'>📞 Appeler</a>", unsafe_allow_html=True)
            st.markdown(f"<a href='https://wa.me/{num_wa}' class='btn-action btn-wa' target='_blank'>💬 WhatsApp</a>", unsafe_allow_html=True)
        adresse_enc = f"{dos.adresse} {dos.commune}".replace(' ', '+')
        st.markdown(f"<a href='https://maps.google.com/?q={adresse_enc}' class='btn-action btn-maps' target='_blank'>🗺️ Maps</a></div>",
                    unsafe_allow_html=True)

        col_g, col_d = st.columns([1.5, 1])

        with col_g:
            st.markdown("### 📝 Historique & Observations")
            if dos.observations:
                st.info(f"**Obs Excel :** {dos.observations}")

            note = st.text_area("Ajouter un compte-rendu :", key=f"n_{dos.id}")
            if st.button("Enregistrer", key=f"bn_{dos.id}"):
                if note.strip():
                    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                    dos.historique_visites = (
                        f"🔹 **[{date_str}]** {note}\n"
                        + (dos.historique_visites or "")
                    )
                    session.commit()
                    invalider_cache()
                    st.rerun()

            hist = (dos.historique_visites or 'Aucun rapport enregistré').replace('\n', '<br>')
            st.markdown(f"<div style='background:#f8fafc;padding:15px;border-radius:8px;"
                        f"height:200px;overflow-y:auto;'>{hist}</div>", unsafe_allow_html=True)

        with col_d:
            st.markdown("### 📎 Documents Cloud")
            pdf_data = generer_fiche_promoteur_pdf(dos)
            st.download_button("📄 Fiche PDF", data=pdf_data,
                               file_name=f"ANGEM_{dos.identifiant}.pdf",
                               mime="application/pdf", use_container_width=True)

            with st.expander("📸 Scanner ou Joindre un document"):
                cam     = st.camera_input("Caméra", key=f"c_{dos.id}")
                file_up = st.file_uploader("Fichier image", key=f"f_{dos.id}")

                if st.button("☁️ Archiver sur Supabase", key=f"u_{dos.id}"):
                    data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                    if data:
                        try:
                            fname = f"{dos.identifiant}_{int(datetime.now().timestamp())}.jpg"
                            get_supabase().storage.from_("scans_angem").upload(
                                file=data, path=fname,
                                file_options={"content-type": "image/jpeg"}
                            )
                            dos.documents = (dos.documents or "") + fname + "|"
                            session.commit()
                            st.success("Document archivé !")
                        except Exception as e:
                            st.error(f"Erreur Cloud: {e}")

            if dos.documents:
                for fname in [x for x in dos.documents.split('|') if x]:
                    url = get_supabase().storage.from_('scans_angem').get_public_url(fname)
                    st.markdown(f"📥 <a href='{url}' target='_blank'>Voir le document</a>",
                                unsafe_allow_html=True)
    finally:
        session.close()

# ==========================================
# 12. PAGE GESTION (financement / recouvrement)
# ==========================================
def page_gestion(mode="financement", vue_admin=False):
    env       = st.session_state.user['env']
    role      = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    badge     = "in_finance" if mode == "financement" else "in_recouvrement"

    df = charger_dossiers(env, badge)
    if df.empty:
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    # Alerte nouveaux dossiers
    if role == 'agent' and mode == 'financement':
        nvx = len(df[(df['gestionnaire'].str.upper() == nom_agent) & (df['est_nouveau'] == "OUI")])
        if nvx > 0:
            st.markdown(f"<div class='alerte-nouveau'>🎉 {nvx} nouveau(x) dossier(s) affecté(s) !</div>",
                        unsafe_allow_html=True)

    # Barre de recherche
    st.markdown(f"<div class='modern-card'><div class='search-title'>🔍 Recherche {mode}</div>",
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 1, 1])
    tmp_s = c1.text_input("Recherche...", value=st.session_state.search_query,
                           label_visibility="collapsed")
    if c2.button("🔍 Chercher", type="primary", use_container_width=True):
        st.session_state.search_query = tmp_s; st.rerun()
    if c3.button("❌ Effacer", use_container_width=True):
        st.session_state.search_query = ""; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Filtrage
    if st.session_state.search_query:
        q = st.session_state.search_query
        df = df[df.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)]
    if not vue_admin and role == "agent":
        df = df[df['gestionnaire'].str.upper() == nom_agent]

    df = df.copy()
    df.insert(0, "Ouvrir 📂", False)

    # Liste agents pour selectbox
    noms_db      = charger_agents_noms()
    noms_dossier = df['gestionnaire'].dropna().tolist()
    liste_agents = [""] + sorted(set(noms_db + noms_dossier))

    if mode == "financement":
        cols = ["Ouvrir 📂","identifiant","nom","prenom","statut_dossier",
                "gestionnaire","montant_pnr","num_ordre_versement","banque_nom","date_financement","id"]
        config = {
            "Ouvrir 📂":    st.column_config.CheckboxColumn(default=False),
            "id":           None,
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent Affecté", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr":  st.column_config.NumberColumn("PNR Débloqué", format="%d DA"),
        }
    else:
        cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone",
                "montant_pnr","montant_rembourse","reste_rembourser","gestionnaire","id"]
        config = {
            "Ouvrir 📂":        st.column_config.CheckboxColumn(default=False),
            "id":               None,
            "identifiant":      st.column_config.TextColumn("Identifiant", disabled=True),
            "nom":              st.column_config.TextColumn("Nom", disabled=True),
            "prenom":           st.column_config.TextColumn("Prénom", disabled=True),
            "telephone":        st.column_config.TextColumn("Téléphone", disabled=True),
            "montant_pnr":      st.column_config.NumberColumn("Crédit", format="%d DA", disabled=True),
            "montant_rembourse":st.column_config.NumberColumn("Remboursé", format="%d DA", disabled=True),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA", disabled=True),
            "gestionnaire":     st.column_config.TextColumn("Agent", disabled=True),
        }

    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(df[cols], use_container_width=True, hide_index=True,
                            column_config=config, height=600)

    if mode == "financement" and st.button("💾 Sauvegarder", type="primary"):
        session = get_session()
        try:
            for _, r in edited.iterrows():
                dos = session.get(Dossier, int(r['id']))
                if dos:
                    dos.statut_dossier = r['statut_dossier']
                    if role != 'agent':
                        dos.gestionnaire = str(r['gestionnaire']).strip().upper()
            session.commit()
            invalider_cache()
            st.toast("✅ Base de données mise à jour !")
            st.rerun()
        finally:
            session.close()

    st.markdown("</div>", unsafe_allow_html=True)

    # Ouvrir un dossier
    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        afficher_profil_complet(dos_id)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 13. INTÉGRATION ADMIN
# ==========================================
def _widget_mapping(fields: list, excel_cols: list, prefix: str, ncols=2) -> dict:
    """Affiche les selectbox de mapping et retourne le dict résultant."""
    mapping = {}
    cols_ui = st.columns(ncols)
    for idx, db_f in enumerate(fields):
        def_idx = auto_map_index(db_f, excel_cols[1:])  # skip "-- Ignorer --"
        with cols_ui[idx % ncols]:
            mapping[db_f] = st.selectbox(
                f"Colonne pour '{db_f}'", excel_cols,
                index=def_idx if def_idx == 0 else def_idx,
                key=f"{prefix}_{db_f}"
            )
    return mapping

def _traiter_import_finance(df: pd.DataFrame, mapping: dict, env: str):
    session   = get_session()
    agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
    c_add = c_upd = 0
    mapped_cols = {v for v in mapping.values() if v != "-- Ignorer --"}
    total = len(df)

    with st.status("Import Finance en cours...", expanded=True) as status:
        bar = st.progress(0)
        try:
            for idx, row in df.iterrows():
                bar.progress(min(1.0, (idx + 1) / total))
                data = {}
                for db_f, xl_col in mapping.items():
                    if xl_col == "-- Ignorer --": continue
                    val = row[xl_col]
                    if pd.isna(val) or str(val).strip() in ("","NAN","None"): continue
                    if db_f in COLONNES_ARGENT:      data[db_f] = clean_money(val)
                    elif db_f == 'identifiant':      data[db_f] = clean_identifiant(val)
                    elif db_f == 'gestionnaire':     data[db_f] = trouver_agent_intelligent(val, agents_db)
                    else:                            data[db_f] = str(val).strip().upper()

                ident = data.get('identifiant')
                if not ident: continue
                valeur_pnr = float(data.get('montant_pnr') or 0)
                notes = "\n".join(f"- {c}: {str(row[c]).strip()}"
                                  for c in df.columns
                                  if c not in mapped_cols
                                  and str(row[c]).strip() not in ("","NAN","None"))
                date_str = datetime.now().strftime('%d/%m/%Y')

                exist = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).first()
                if exist:
                    for k, v in data.items():
                        if v not in (None, ""): setattr(exist, k, v)
                    exist.in_finance = "OUI"
                    if notes:
                        exist.historique_visites = (f"🔹 **[Import Finance {date_str}]**\n{notes}\n"
                                                    + (exist.historique_visites or ""))
                    c_upd += 1
                else:
                    if valeur_pnr <= 40000: continue
                    data.update({'type_dispositif':env,'est_nouveau':'OUI',
                                 'in_finance':'OUI','in_recouvrement':'NON'})
                    if notes:
                        data['historique_visites'] = f"🔹 **[Import Finance {date_str}]**\n{notes}\n"
                    session.add(Dossier(**data))
                    c_add += 1

            session.commit()
            invalider_cache()
            status.update(label=f"✅ {c_add} créés, {c_upd} mis à jour.", state="complete")
        except Exception as e:
            session.rollback()
            st.error(f"Erreur import : {e}")
        finally:
            session.close()

def _traiter_import_recouvrement(df: pd.DataFrame, mapping: dict, env: str):
    session = get_session()
    c_upd = c_new = 0
    mapped_cols = {v for v in mapping.values() if v != "-- Ignorer --"}
    total = len(df)

    with st.status("Import Recouvrement en cours...", expanded=True) as status:
        bar = st.progress(0)
        try:
            for idx, row in df.iterrows():
                bar.progress(min(1.0, (idx + 1) / total))
                xl_id = mapping.get('identifiant',"-- Ignorer --")
                ident = clean_identifiant(row[xl_id]) if xl_id != "-- Ignorer --" else ""
                if not ident: continue

                notes = "\n".join(f"- {c}: {str(row[c]).strip()}"
                                  for c in df.columns
                                  if c not in mapped_cols
                                  and str(row[c]).strip() not in ("","NAN","None"))
                date_str = datetime.now().strftime('%d/%m/%Y')

                exist = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).first()
                if exist:
                    for db_f, xl_col in mapping.items():
                        if xl_col == "-- Ignorer --" or db_f == 'identifiant': continue
                        val = row[xl_col]
                        if pd.isna(val) or str(val).strip() in ("","NAN","None"): continue
                        setattr(exist, db_f, clean_money(val) if db_f in COLONNES_ARGENT
                                else str(val).strip().upper())
                    exist.in_recouvrement = "OUI"
                    if notes:
                        exist.historique_visites = (f"🔹 **[Import Recouv {date_str}]**\n{notes}\n"
                                                    + (exist.historique_visites or ""))
                    c_upd += 1
                else:
                    data_new = {}
                    for db_f, xl_col in mapping.items():
                        if xl_col == "-- Ignorer --": continue
                        val = row[xl_col]
                        if pd.isna(val) or str(val).strip() in ("","NAN","None"): continue
                        if db_f in COLONNES_ARGENT:  data_new[db_f] = clean_money(val)
                        elif db_f == 'identifiant':  data_new[db_f] = clean_identifiant(val)
                        else:                        data_new[db_f] = str(val).strip().upper()
                    data_new.update({'type_dispositif':env,'in_recouvrement':'OUI','in_finance':'NON'})
                    if notes:
                        data_new['historique_visites'] = f"🔹 **[Import Recouv {date_str}]**\n{notes}\n"
                    session.add(Dossier(**data_new))
                    c_new += 1

            session.commit()
            invalider_cache()
            status.update(label=f"✅ {c_upd} mis à jour, {c_new} nouveaux.", state="complete")
        except Exception as e:
            session.rollback()
            st.error(f"Erreur import : {e}")
        finally:
            session.close()

def page_integration_admin():
    env  = st.session_state.user['env']
    role = st.session_state.user['role']
    st.title("⚙️ Intégration : Mapping & Données")

    tabs_labels = (["💰 IMPORT FINANCE"] if role == "finance"
                   else ["💰 IMPORT FINANCE","📈 IMPORT RECOUVREMENT",
                         "👥 MAJ GESTIONNAIRES","🧹 DOUBLONS","🔐 EQUIPES"])
    tabs = st.tabs(tabs_labels)

    # ── ONGLET 1 : FINANCE ──────────────────────────────────────
    with tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("💡 **FINANCE :** Crée la fiche et attribue le gestionnaire.")
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx','xls','csv'], key="ff")
        if f_fin:
            try:
                df, excel_cols = preparer_df_import(f_fin)
            except Exception as e:
                st.error(f"🚨 Impossible de lire le fichier : {e}")
                df = None
            if df is not None:
                st.write("### 🎛️ Mapping des Colonnes (Finance)")
                targets_fin = ['identifiant','nom','prenom','date_naissance','adresse',
                               'telephone','commune','activite','gestionnaire','banque_nom',
                               'num_ordre_versement','date_financement','montant_pnr',
                               'apport_personnel','credit_bancaire']
                with st.form("form_fin"):
                    mapping = _widget_mapping(targets_fin, excel_cols, "fin", ncols=2)
                    if st.form_submit_button("🚀 Créer les dossiers", type="primary"):
                        _traiter_import_finance(df, mapping, env)
        st.markdown("</div>", unsafe_allow_html=True)

    if role == "finance":
        return  # Finance n'a accès qu'à l'onglet 1

    # ── ONGLET 2 : RECOUVREMENT ─────────────────────────────────
    with tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.warning("🛡️ **RECOUVREMENT :** Ne modifie jamais le gestionnaire.")
        f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx','xls','csv'], key="fr")
        if f_rec:
            try:
                df, excel_cols = preparer_df_import(f_rec)
            except Exception as e:
                st.error(f"🚨 Impossible de lire le fichier : {e}"); df = None
            if df is not None:
                targets_rec = ['identifiant','nom','prenom','date_naissance','adresse',
                               'telephone','commune','daira','type_dispositif',
                               'debut_consommation','montant_pnr','nb_echeance_tombee',
                               'date_ech_tomb','prochaine_ech','total_echue',
                               'montant_rembourse','reste_rembourser',
                               'observations','anticip','ech_anticip']
                with st.form("form_rec"):
                    mapping_rec = _widget_mapping(targets_rec, excel_cols, "rec", ncols=3)
                    if st.form_submit_button("🚀 Mettre à jour Recouvrement", type="primary"):
                        _traiter_import_recouvrement(df, mapping_rec, env)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ONGLET 3 : GESTIONNAIRES ────────────────────────────────
    with tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.warning("👥 **AFFECTATION MASSIVE** via fichier (Identifiant + Gestionnaire).")
        f_gest = st.file_uploader("Fichier Gestionnaires", type=['xlsx','xls','csv'], key="fgest")
        if f_gest:
            try:
                df_g, ecols_g = preparer_df_import(f_gest)
            except Exception as e:
                st.error(f"🚨 {e}"); df_g = None
            if df_g is not None:
                with st.form("form_gest"):
                    mapping_g = _widget_mapping(
                        ['identifiant','nom','prenom','gestionnaire'], ecols_g, "gest", ncols=2)
                    if st.form_submit_button("🚀 Assigner les gestionnaires", type="primary"):
                        session = get_session()
                        agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
                        session.close()
                        c = 0
                        session2 = get_session()
                        try:
                            for _, row in df_g.iterrows():
                                xi = mapping_g.get('identifiant',"-- Ignorer --")
                                xn = mapping_g.get('nom',"-- Ignorer --")
                                xp = mapping_g.get('prenom',"-- Ignorer --")
                                xg = mapping_g.get('gestionnaire',"-- Ignorer --")
                                ident  = clean_identifiant(row[xi]) if xi != "-- Ignorer --" else ""
                                nom    = str(row[xn]).strip().upper() if xn != "-- Ignorer --" else ""
                                prenom = str(row[xp]).strip().upper() if xp != "-- Ignorer --" else ""
                                gb = row[xg] if xg != "-- Ignorer --" else ""
                                if pd.isna(gb) or str(gb).strip() in ("","NAN","None"): continue
                                gest = trouver_agent_intelligent(gb, agents_db)
                                dos = (session2.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).first()
                                       if ident else None)
                                if not dos and nom and prenom:
                                    dos = session2.query(Dossier).filter_by(nom=nom, prenom=prenom, type_dispositif=env).first()
                                if dos:
                                    dos.gestionnaire = gest; c += 1
                            session2.commit()
                            invalider_cache()
                            st.success(f"✅ {c} dossiers affectés.")
                        except Exception as e:
                            session2.rollback(); st.error(str(e))
                        finally:
                            session2.close()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ONGLET 4 : DOUBLONS ─────────────────────────────────────
    with tabs[3]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        if st.button("🚨 Nettoyer les doublons (même ID + même OV)", type="primary"):
            session = get_session()
            try:
                df_dup = pd.read_sql_query(
                    "SELECT id, identifiant, num_ordre_versement, type_dispositif FROM dossiers",
                    con=get_engine()
                ).fillna("")
                df_dup = df_dup[df_dup['identifiant'] != ""]
                if not df_dup.empty:
                    keep = df_dup.groupby(['identifiant','num_ordre_versement','type_dispositif'])['id'].max().tolist()
                    ids_del = df_dup[~df_dup['id'].isin(keep)]['id'].tolist()
                    if ids_del:
                        session.query(Dossier).filter(Dossier.id.in_(ids_del)).delete(synchronize_session=False)
                        session.commit()
                        invalider_cache()
                        st.success(f"✅ {len(ids_del)} doublon(s) supprimé(s).")
                    else:
                        st.info("Aucun doublon détecté.")
            except Exception as e:
                session.rollback(); st.error(str(e))
            finally:
                session.close()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ONGLET 5 : EQUIPES ──────────────────────────────────────
    with tabs[4]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.subheader("🔑 Équipes")
        try:
            df_u = pd.read_sql_query(
                "SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'",
                con=get_engine()
            )
        except Exception:
            df_u = pd.DataFrame()

        if not df_u.empty:
            ed_u = st.data_editor(df_u, use_container_width=True, hide_index=True,
                                  column_config={
                                      "id":          None,
                                      "identifiant": st.column_config.TextColumn(disabled=True),
                                      "nom":         st.column_config.TextColumn(disabled=True),
                                      "daira":       st.column_config.SelectboxColumn(options=LISTE_DAIRAS),
                                      "mot_de_passe":st.column_config.TextColumn("Nouveau mot de passe"),
                                  })
            if st.button("💾 Sauvegarder équipes", type="primary"):
                session = get_session()
                try:
                    for _, r in ed_u.iterrows():
                        u = session.get(UtilisateurAuth, int(r['id']))
                        if u:
                            new_mdp = str(r['mot_de_passe'])
                            if new_mdp and not new_mdp.startswith("$2"):
                                u.mot_de_passe = _hash(new_mdp)
                            u.daira = r['daira']
                    session.commit()
                    st.success("✅ Équipes mises à jour.")
                except Exception as e:
                    session.rollback(); st.error(str(e))
                finally:
                    session.close()

        st.divider()
        with st.form("ajout_agent"):
            c1, c2, c3 = st.columns([1, 1.5, 1])
            n_id   = c1.text_input("Identifiant de connexion")
            n_nom  = c2.text_input("Nom Complet")
            n_daira= c3.selectbox("Daïra", LISTE_DAIRAS)
            if st.form_submit_button("Créer le compte Agent") and n_id and n_nom:
                session = get_session()
                try:
                    if not session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first():
                        session.add(UtilisateurAuth(
                            identifiant=n_id.lower(), nom=n_nom.strip().upper(),
                            daira=n_daira, mot_de_passe=_hash("angem2026"), role="agent"
                        ))
                        session.commit()
                        invalider_cache()
                        st.success(f"✅ Compte créé — mot de passe par défaut : angem2026")
                        st.rerun()
                    else:
                        st.error("Cet identifiant existe déjà.")
                except Exception as e:
                    session.rollback(); st.error(str(e))
                finally:
                    session.close()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 14. SUPERVISION
# ==========================================
def page_supervision():
    st.title("📊 Supervision Globale")
    env = st.session_state.user['env']

    df = pd.read_sql_query(
        text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
        con=get_engine(), params={"env": env}
    ).fillna('')

    if df.empty:
        st.warning("La base est vide pour cet environnement."); return

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div><div class='metric-label'>Total Dossiers</div><div class='metric-value'>{len(df)}</div></div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div><div class='metric-label'>PNR Engagé</div><div class='metric-value'>{df['montant_pnr'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div><div class='metric-label'>Total Recouvré</div><div class='metric-value'>{df['montant_rembourse'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card metric-danger'><div><div class='metric-label'>Reste à Recouvrer</div><div class='metric-value' style='color:#dc2626;'>{df['reste_rembourser'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.subheader("📥 Extractions Officielles")
    cb1,cb2,cb3 = st.columns(3)
    with cb1:
        st.download_button("📊 Bilan Global PDF",
                           data=generer_rapport_global_pdf(df),
                           file_name="Bilan_Angem.pdf", mime="application/pdf",
                           use_container_width=True)
    with cb2:
        st.download_button("🔴 Contentieux PDF",
                           data=generer_creances_pdf(df),
                           file_name="Contentieux_Angem.pdf", mime="application/pdf",
                           use_container_width=True)
    with cb3:
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        st.download_button("🟢 Sauvegarde Excel", data=buf.getvalue(),
                           file_name="Backup_Angem.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 15. CORBEILLE
# ==========================================
def page_corbeille():
    env   = st.session_state.user['env']
    agent = st.session_state.user['nom']
    daira = st.session_state.user.get('daira','')

    if not daira:
        st.warning("Vous n'avez pas de Daïra assignée."); return

    df = pd.read_sql_query(
        text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
        con=get_engine(), params={"env": env}
    ).fillna('')

    mask_vide  = df['gestionnaire'].str.strip() == ""
    mask_daira = (df['daira'].str.contains(daira, case=False, na=False)
                  | df['commune'].str.contains(daira, case=False, na=False))
    orphans = df[mask_vide & mask_daira].copy()

    st.markdown(f"<div class='modern-card'><h3 style='text-align:center;'>Dossiers non assignés à {daira} : {len(orphans)}</h3></div>",
                unsafe_allow_html=True)

    if orphans.empty:
        st.success("Aucun dossier orphelin dans votre secteur."); return

    orphans["C'est à moi !"] = False
    ed = st.data_editor(orphans, hide_index=True,
                        column_config={"C'est à moi !": st.column_config.CheckboxColumn(default=False), "id": None})
    ids = ed[ed["C'est à moi !"] == True]['id'].tolist()

    if st.button(f"📥 S'attribuer {len(ids)} dossier(s)", type="primary") and ids:
        session = get_session()
        try:
            session.query(Dossier).filter(Dossier.id.in_(ids)).update(
                {"gestionnaire": agent.upper()}, synchronize_session=False)
            session.commit()
            invalider_cache()
            st.success("✅ Dossiers récupérés.")
            st.rerun()
        except Exception as e:
            session.rollback(); st.error(str(e))
        finally:
            session.close()

# ==========================================
# 16. ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if "Intégration" in page or "Import" in page:
        page_integration_admin()
    elif "Supervision" in page:
        page_supervision()
    elif "Corbeille" in page:
        page_corbeille()
    elif "Financement" in page:
        page_gestion(mode="financement", vue_admin=("Vue Globale" in page))
    else:
        page_gestion(mode="recouvrement", vue_admin=("Vue Globale" in page))
