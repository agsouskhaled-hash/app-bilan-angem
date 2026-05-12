import streamlit as st
import pandas as pd
import difflib
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base
import unicodedata
import re
import io
import json
import contextlib
from datetime import datetime, date
from fpdf import FPDF
import tempfile
import os
from supabase import create_client, Client

st.set_page_config(
    page_title="ANGEM Workspace",
    page_icon="🇩🇿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CREDENTIALS
# ==========================================
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    DB_URL       = st.secrets["database"]["url"]
except Exception:
    SUPABASE_URL = "https://greyjhgiytajxpvucbrk.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyZXlqaGdpeXRhanhwdnVjYnJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTU0MjksImV4cCI6MjA4NzU5MTQyOX0.jCNan1Y1hvfGog6Zcu8Rr8d5PkeFRFvipAGGB09ztxo"
    DB_URL       = "postgresql+psycopg2://postgres.greyjhgiytajxpvucbrk:algerouest2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# CONSTANTES
# ==========================================
LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]

# ✅ Mapping Daïra → Communes (Wilaya d'Alger)
DAIRA_COMMUNES = {
    "Zéralda":         ["Zéralda", "Mahelma", "Rahmania", "Souidania", "Staoueli"],
    "Chéraga":         ["Chéraga", "Aïn Benian", "Hammamet", "Ouled Fayet", "Dely Brahim"],
    "Draria":          ["Draria", "Baba Hassen", "Douera", "El Achour", "Khraïcia"],
    "Bir Mourad Rais": ["Bir Mourad Rais", "Birkhadem", "Djasr Kasentina", "Hydra", "Saoula"],
    "Bouzareah":       ["Bouzareah", "Beni Messous", "Ben Aknoun", "El Biar"],
    "Birtouta":        ["Birtouta", "Ouled Chebel", "Tessala El Merdja"],
}

def deduire_daira_de_commune(commune: str) -> str:
    """Retourne la daïra correspondante à une commune, sinon ''."""
    if not commune:
        return ""
    c_norm = unicodedata.normalize('NFKD', str(commune).strip().upper()).encode('ascii','ignore').decode('ascii')
    for daira, communes in DAIRA_COMMUNES.items():
        for com in communes:
            com_norm = unicodedata.normalize('NFKD', com.upper()).encode('ascii','ignore').decode('ascii')
            if com_norm == c_norm or com_norm in c_norm or c_norm in com_norm:
                return daira
    return ""

def communes_de_daira(daira: str) -> list:
    """Retourne la liste des communes d'une daïra."""
    return DAIRA_COMMUNES.get(daira, [])
LISTE_STATUTS = [
    "Phase dépôt du dossier",
    "En attente de la commission",
    "Accordé / En cours",
    "En phase d'exploitation",
    "Contentieux / Retard"
]
COLONNES_ARGENT = [
    'montant_pnr', 'montant_rembourse', 'reste_rembourser',
    'total_echue', 'apport_personnel', 'credit_bancaire', 'montant_total_credit'
]
MAPPING_CONFIG_KEYWORDS = {
    'identifiant':         ['IDENTIFIANT','CNI','NCINPC','NAT','NATIONALITE','ID','NIN'],
    'nom':                 ['NOMETPRENOM','NOM','PROMOTEUR','BENEFICIAIRE'],
    'prenom':              ['PRENOM'],
    'date_naissance':      ['NAISSANCE','DATENAISS','NELE','DATEDENAISSANCE'],
    'adresse':             ['ADRESSE','LIEU','DOMICILE'],
    'telephone':           ['TEL','MOB','TELEPHONE','MOBILE','GSM','CONTACT'],
    'commune':             ['COMMUNE','APC','MUNICIPALITE'],
    'daira':               ['DAIRA'],
    'wilaya':              ['WILAYA'],
    'secteur':             ['SECTEUR'],
    'zone':                ['ZONE'],
    'genre':               ['GENRE','SEXE','CIVILITE'],
    'age':                 ['AGE'],
    'niveau_instruction':  ['NIVEAU','INSTRUCTION','SCOLARITE'],
    'type_dispositif':     ['TYPE','FINANCEMENT','DISPOSITIF','PROGRAMME'],
    'activite':            ['ACTIVITE','PROJET','INTITULE','NATUREPROJET','LIBELLEACTIVITE'],
    'code_activite':       ['CODEACTIVITE','CODE'],
    'gestionnaire':        ['GEST','ACCOMPAGNATEUR','AGENT','CHARGE','RESPONSABLE'],
    'banque_nom':          ['BANQUE','CCP','ETABLISSEMENT'],
    'agence_bancaire':     ['AGENCE','AGENCEBANC'],
    'numero_compte':       ['NUMCOMPTE','COMPTE','RIB'],
    'num_ordre_versement': ['NUMOV','ORDREVERSEMENT','OV','NUMERORDREVIREMENT'],
    'date_financement':    ['DATEOV','DATEVIREMENT','DATEFINAN','DATEVERSEMENT','DATEOCTROI'],
    'debut_consommation':  ['DEBUTCONSOM','CONSOMMATION','DEBUT'],
    'montant_pnr':         ['PNR','MONTANTPNR','MONTANTACCORDE','MONTANTCREDIT','CREDIT','MONTANT'],
    'apport_personnel':    ['APPORT','APPORTPERSO','APPORTPERSONNEL'],
    'credit_bancaire':     ['CREDITBANC','CREDITBANCAIRE','MONTANTBANQUE'],
    'montant_total_credit':['MONTANTTOTAL','TOTAL','COUTPROJET'],
    'nb_echeance_tombee':  ['ECHTOMB','ECHEANCES','NBRECHTOMB','NBRECHEANCESTOMBEES'],
    'date_ech_tomb':       ['DATEECHTOMB','DATEECHEANCETOMBEE','DATEECH'],
    'prochaine_ech':       ['PROCHAINEECH','PROCHECH','PROCHAINEECHEANCE'],
    'total_echue':         ['TOTALECHUE','MONTECHEAN','MONTANTECHU'],
    'montant_rembourse':   ['TOTALREMB','VERSEMENT','REMBOURSE','TOTALVERS','MONTANTREMBOURSE'],
    'reste_rembourser':    ['RESTAREMB','MONTANTRESTA','RESTE','SOLDE','ENCOURS'],
    'etat_dette':          ['ETATDETTE','ETAT','SITUATION'],
    'observations':        ['OBS','OBSERVATION','OBSERVATIONS','REMARQUE','NOTE'],
    'anticip':             ['ANTICIP','ANTICIPATION'],
    'ech_anticip':         ['ECHANTICIP','ECHEANCEANTICIP'],
}

# ==========================================
# BASE DE DONNÉES
# ==========================================
Base = declarative_base()
engine = create_engine(DB_URL, echo=False, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

@contextlib.contextmanager
def get_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class Dossier(Base):
    __tablename__ = 'dossiers'
    id                   = Column(Integer, primary_key=True)
    identifiant          = Column(String, index=True)
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
    wilaya               = Column(String, default="")
    zone                 = Column(String, default="")
    gestionnaire         = Column(String, default="")
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
    anticip              = Column(String, default="")
    ech_anticip          = Column(String, default="")
    observations         = Column(String, default="")
    statut_dossier       = Column(String, default="Phase dépôt du dossier")
    documents            = Column(String, default="")
    historique_visites   = Column(String, default="")
    prochaine_visite     = Column(String, default="")
    est_nouveau          = Column(String, default="NON")
    in_finance           = Column(String, default="NON")
    in_recouvrement      = Column(String, default="NON")
    champs_dynamiques    = Column(Text, default="{}")

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id           = Column(Integer, primary_key=True)
    identifiant  = Column(String, unique=True)
    nom          = Column(String)
    mot_de_passe = Column(String)
    role         = Column(String)
    daira        = Column(String, default="")

Base.metadata.create_all(engine)

_MIGRATIONS = {
    'champs_dynamiques':    "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS champs_dynamiques TEXT DEFAULT '{}'",
    'wilaya':               "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS wilaya VARCHAR DEFAULT ''",
    'agence_bancaire':      "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS agence_bancaire VARCHAR DEFAULT ''",
    'numero_compte':        "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS numero_compte VARCHAR DEFAULT ''",
    'montant_total_credit': "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS montant_total_credit FLOAT DEFAULT 0.0",
    'zone':                 "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS zone VARCHAR DEFAULT ''",
    'secteur':              "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS secteur VARCHAR DEFAULT ''",
}
try:
    with engine.connect() as conn:
        for col, sql in _MIGRATIONS.items():
            conn.execute(text(sql))
        conn.commit()
except Exception:
    pass

def init_db_users():
    with get_session() as session:
        for ident, nom, role in [
            ("admin","Administrateur","admin"),
            ("finance","Service Finance","finance"),
            ("communication","Service Communication","communication")
        ]:
            u = session.query(UtilisateurAuth).filter_by(identifiant=ident).first()
            if not u:
                session.add(UtilisateurAuth(identifiant=ident, nom=nom, mot_de_passe="angem", role=role))

init_db_users()

# ==========================================
# SESSION STATE
# ==========================================
for key, val in {
    'user': None,
    'portal_selection': None,
    'search_query': "",
    'import_quick_open': False,
    'agent_choisi': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# THÈME
# ==========================================
if st.session_state.user and st.session_state.user.get('env') == "PNR PROJET":
    theme_color, theme_bg = "#1f77b4", "#f4f9fc"
elif st.session_state.user:
    theme_color, theme_bg = "#28a745", "#f4fcf5"
else:
    theme_color, theme_bg = "#2c3e50", "#f8f9fa"

st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    :root {{
        --primary: {theme_color};
        --bg: {theme_bg};
        --surface: #ffffff;
        --surface-2: #f8fafc;
        --text: #0f172a;
        --text-muted: #64748b;
        --border: #e2e8f0;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --accent: #0ea5e9;
    }}

    * {{ font-family: 'Manrope', -apple-system, sans-serif; }}
    h1, h2, h3, h4 {{ font-family: 'Outfit', sans-serif; letter-spacing: -0.02em; }}

    .stApp {{
        background:
            radial-gradient(circle at 0% 0%, rgba(31,119,180,0.04) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(40,167,69,0.04) 0%, transparent 50%),
            var(--bg);
    }}

    .modern-card {{
        background: var(--surface);
        padding: 28px;
        border-radius: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02), 0 8px 24px rgba(0,0,0,0.04);
        margin: 16px 0 24px;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(.4,0,.2,1);
    }}
    .modern-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--accent));
    }}
    .modern-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.04), 0 16px 40px rgba(0,0,0,0.08); }}

    .metric-card {{
        background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
        border-radius: 16px;
        padding: 22px;
        border: 1px solid var(--border);
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
        transition: all 0.25s ease;
    }}
    .metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
    .metric-card::after {{
        content: '';
        position: absolute;
        right: -20px; top: -20px;
        width: 80px; height: 80px;
        background: var(--primary);
        opacity: 0.06;
        border-radius: 50%;
    }}

    .metric-value {{
        font-family: 'Outfit', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.03em;
        margin-top: 4px;
    }}
    .metric-label {{
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}
    .metric-danger {{ background: linear-gradient(135deg, #fef2f2 0%, #fff 100%); border-color: #fecaca; }}
    .metric-danger::after {{ background: var(--danger); }}

    .profil-header {{
        background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
        padding: 28px;
        border-radius: 20px;
        border-left: 6px solid var(--primary);
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .profil-header h2 {{ margin: 0; font-size: 26px; font-weight: 700; color: var(--text); }}

    .block-finance, .block-recouvrement, .block-dynamique {{
        padding: 18px 20px;
        border-radius: 14px;
        margin-bottom: 14px;
        border: 1px solid var(--border);
    }}
    .block-finance {{ background: linear-gradient(135deg, #eff6ff 0%, #fff 100%); border-left: 4px solid #3b82f6; }}
    .block-recouvrement {{ background: linear-gradient(135deg, #f0fdf4 0%, #fff 100%); border-left: 4px solid #10b981; }}
    .block-dynamique {{ background: linear-gradient(135deg, #fefce8 0%, #fff 100%); border-left: 4px solid #eab308; }}
    .block-title {{
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 12px;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .btn-action {{
        flex: 1;
        min-width: 150px;
        padding: 13px 22px;
        border-radius: 12px;
        font-weight: 600;
        text-align: center;
        color: white !important;
        transition: all 0.25s cubic-bezier(.4,0,.2,1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 14px;
        text-decoration: none;
        margin: 4px;
    }}
    .btn-action:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.15); }}
    .btn-call {{ background: linear-gradient(135deg, #3b82f6, #2563eb); }}
    .btn-wa {{ background: linear-gradient(135deg, #22c55e, #16a34a); }}
    .btn-maps {{ background: linear-gradient(135deg, #ef4444, #dc2626); }}

    .badge-nouveau {{
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
        animation: pulse 1.8s infinite;
        box-shadow: 0 2px 8px rgba(239,68,68,0.3);
    }}
    @keyframes pulse {{
        0%,100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.85; transform: scale(0.96); }}
    }}

    .alerte-nouveau {{
        background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
        border-left: 5px solid #10b981;
        padding: 16px 22px;
        border-radius: 12px;
        color: #065f46;
        font-weight: 600;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(16,185,129,0.08);
    }}

    .import-rapide-box {{
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);
        padding: 24px;
        border-radius: 18px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 40px rgba(37,99,235,0.25);
        position: relative;
        overflow: hidden;
    }}
    .import-rapide-box::before {{
        content: '';
        position: absolute;
        top: -50%; right: -10%;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        border-radius: 50%;
    }}

    .agent-card {{
        background: var(--surface);
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        border: 2px solid var(--border);
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        transition: all 0.3s cubic-bezier(.4,0,.2,1);
    }}
    .agent-card:hover {{ transform: translateY(-4px); border-color: var(--primary); box-shadow: 0 12px 32px rgba(0,0,0,0.08); }}

    .stat-agent-card {{
        background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        border: 1px solid var(--border);
        transition: all 0.2s ease;
    }}
    .stat-agent-card:hover {{ transform: translateY(-2px); }}
    .stat-icon {{ font-size: 22px; margin-bottom: 6px; }}
    .stat-val {{ font-family: 'Outfit', sans-serif; font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }}
    .stat-lbl {{ font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; letter-spacing: 0.08em; margin-top: 2px; }}

    /* Streamlit overrides */
    .stButton > button {{
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
        border: 1px solid var(--border);
    }}
    .stButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
    .stTextInput > div > div > input, .stSelectbox > div > div {{ border-radius: 12px !important; }}
    [data-testid="stMetric"] {{
        background: var(--surface);
        padding: 18px;
        border-radius: 14px;
        border: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }}
    [data-testid="stMetricValue"] {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILITAIRES
# ==========================================

PREFIXES_RE = r'(MME|MR|M\.|MLLE|MELLE|DR|PR)\.?\s*'

def normaliser_nom(s: str) -> str:
    """Supprime préfixes, accents, met en majuscules — pour comparaison."""
    s = re.sub(PREFIXES_RE, '', str(s).strip().upper())
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').strip()

def similarite(a: str, b: str) -> float:
    """Score de ressemblance entre deux noms (0 à 1)."""
    return difflib.SequenceMatcher(None, normaliser_nom(a), normaliser_nom(b)).ratio()

def clean_header(v):
    return ''.join(filter(str.isalnum, unicodedata.normalize('NFKD', str(v)).encode('ascii','ignore').decode('ascii').upper()))

def clean_identifiant(v):
    if pd.isna(v) or str(v).strip() in ['', 'NAN', 'None', 'nan']:
        return ""
    s = str(v).strip()
    if re.match(r'^[\d\.\+\-eE]+$', s) and ('e' in s.lower() or 'E' in s):
        try:
            return f"{float(s):.0f}"
        except Exception:
            pass
    if s.endswith('.0'):
        s = s[:-2]
    return s.strip().upper()

def clean_money(v):
    if pd.isna(v) or str(v).strip() in ['', 'NAN', 'None', 'nan', '-', 'N/A']:
        return 0.0
    s = str(v).strip()
    s = re.sub(r'[Dd][Aa]|DZD|DA', '', s)
    s = s.replace('\xa0', '').replace(' ', '').replace('\u202f', '')
    if s.count(',') == 1 and s.count('.') >= 1:
        s = s.replace('.', '').replace(',', '.')
    elif s.count(',') == 1 and s.count('.') == 0:
        s = s.replace(',', '.')
    elif s.count('.') >= 2:
        s = s.replace('.', '')
    s = re.sub(r'[^\d\.\-]', '', s)
    try:
        val = float(s)
        return val if val >= 0 else 0.0
    except Exception:
        return 0.0

def clean_pdf_text(t):
    if not t:
        return ""
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii')

def is_ligne_parasite(row, colonnes_mappees):
    vals = [str(v).strip() for v in row.values]
    vals_non_vides = [v for v in vals if v not in ('', 'NAN', 'None', 'nan', '-')]
    if not vals_non_vides:
        return True
    mots_parasites = ['TOTAL', 'SOUS-TOTAL', 'CUMUL', 'GRAND TOTAL',
                      'IDENTIFIANT', 'CNI', 'NOM ET PRENOM', 'PROMOTEUR', 'SUITE']
    if any(mot in vals_non_vides[0].upper() for mot in mots_parasites):
        return True
    return False

def get_header_row(df_raw):
    tous_mots_cles = set()
    for kws in MAPPING_CONFIG_KEYWORDS.values():
        tous_mots_cles.update(kws)
    best_idx, best_score = 0, 0
    for i in range(min(50, len(df_raw))):
        row_cl = [clean_header(str(x)) for x in df_raw.iloc[i].values]
        score = sum(1 for cell in row_cl for kw in tous_mots_cles if kw in cell)
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx

def safe_read_dataframe(file_obj):
    # ✅ Patch openpyxl pour fichiers Excel avec attribut biltinId invalide
    try:
        import openpyxl.styles.named_styles as _ns
        _orig_init = _ns._NamedCellStyle.__init__
        def _patched_init(self, **kwargs):
            kwargs.pop('biltinId', None)
            _orig_init(self, **kwargs)
        _ns._NamedCellStyle.__init__ = _patched_init
    except Exception:
        pass
    name = file_obj.name.lower()
    if name.endswith('.csv'):
        for sep, enc in [(';','utf-8'),(';','latin1'),(',','utf-8'),('\t','utf-8')]:
            try:
                file_obj.seek(0)
                return pd.read_csv(file_obj, sep=sep, encoding=enc,
                                   header=None, dtype=str, on_bad_lines='skip')
            except Exception:
                pass
    else:
        for eng in ['openpyxl', 'xlrd']:
            try:
                file_obj.seek(0)
                return pd.read_excel(file_obj, header=None, dtype=str, engine=eng)
            except Exception:
                pass
    raise ValueError("Impossible de lire le fichier.")

def fix_colonnes_doublons(df):
    """✅ Renomme les colonnes en double pour éviter les erreurs Streamlit/PyArrow."""
    cols_vus = {}
    nouvelles_cols = []
    for col in df.columns:
        if col in cols_vus:
            cols_vus[col] += 1
            nouvelles_cols.append(f"{col}_{cols_vus[col]}")
        else:
            cols_vus[col] = 0
            nouvelles_cols.append(col)
    df.columns = nouvelles_cols
    return df

def auto_mapper(df_cols):
    mapping = {}
    cols_clean = {clean_header(c): c for c in df_cols}
    for db_field, keywords in MAPPING_CONFIG_KEYWORDS.items():
        for kw in keywords:
            for col_clean, col_orig in cols_clean.items():
                if kw in col_clean or col_clean in kw:
                    if db_field not in mapping:
                        mapping[db_field] = col_orig
                    break
    return mapping

def extraire_champs_dynamiques(row, colonnes_mappees, all_cols):
    champs = {}
    for col in all_cols:
        if col not in colonnes_mappees:
            val = row.get(col, '')
            val_str = str(val).strip()
            if val_str not in ('', 'NAN', 'None', 'nan', '-'):
                champs[col] = val_str
    return champs

def trouver_agent_par_zone(daira, commune, session):
    if not daira and not commune:
        return ""
    agents = session.query(UtilisateurAuth).filter_by(role='agent').all()
    zone = (daira + " " + commune).upper()
    for agent in agents:
        if agent.daira and agent.daira.upper() in zone:
            return agent.nom
    return ""

def trouver_agent_intelligent(nom_excel: str, agents_db: list) -> str:
    """✅ Matching par similarité 80% — tolère fautes de frappe et préfixes."""
    if not nom_excel or str(nom_excel).strip().upper() in ['', 'NAN', 'NONE']:
        return ""
    meilleur_score = 0.0
    meilleur_agent = ""
    for agent in agents_db:
        score = similarite(nom_excel, agent)
        if score > meilleur_score:
            meilleur_score = score
            meilleur_agent = agent
    if meilleur_score >= 0.80:
        return meilleur_agent
    return normaliser_nom(nom_excel)

def verifier_doublon(session, identifiant, env, badge):
    if not identifiant:
        return None
    return session.query(Dossier).filter(
        Dossier.identifiant == identifiant,
        Dossier.type_dispositif == env,
        getattr(Dossier, badge) == 'OUI'
    ).first()

# ==========================================
# MOTEUR D'IMPORT
# ==========================================

def moteur_import(df, mapping, env, badge, session, agents_db, affectation_auto=False):
    stats = {'crees': 0, 'mis_a_jour': 0, 'ignores': 0, 'non_assignes': 0, 'erreurs': []}
    colonnes_mappees = [v for v in mapping.values() if v != "-- Ignorer --"]
    total = len(df)
    progress_bar = st.progress(0)

    # ✅ CACHE TRIPLE : identifiant + nom + date_naissance
    _cache_by_ident = {}     # {identifiant: dossier_id}
    _cache_by_nom   = []     # [(id, nom_norm, prefixe, date_naiss)]
    _cache_by_date  = {}     # {date_naiss: [(id, nom_norm)]}
    if badge == 'in_recouvrement':
        rows = session.query(
            Dossier.id, Dossier.identifiant, Dossier.nom, Dossier.prenom, Dossier.date_naissance
        ).filter(
            Dossier.type_dispositif == env,
            Dossier.in_finance == 'OUI'
        ).all()
        for r in rows:
            d_id     = r[0]
            ident_db = (r[1] or '').strip().upper()
            nom_db   = r[2] or ''
            prenom_db= r[3] or ''
            date_db  = (r[4] or '').strip()
            if ident_db:
                _cache_by_ident[ident_db] = d_id
            nom_norm = normaliser_nom(f"{nom_db} {prenom_db}")
            prefixe = nom_norm[:2] if len(nom_norm) >= 2 else nom_norm
            if nom_norm:
                _cache_by_nom.append((d_id, nom_norm, prefixe, date_db))
            if date_db:
                _cache_by_date.setdefault(date_db, []).append((d_id, nom_norm))

    for idx, row in df.iterrows():
        try:
            progress_bar.progress(min(1.0, (idx + 1) / max(total, 1)))
            if is_ligne_parasite(row, colonnes_mappees):
                stats['ignores'] += 1
                continue
            data = {}
            for db_field, xl_col in mapping.items():
                if xl_col == "-- Ignorer --":
                    continue
                val = row.get(xl_col, '')
                if pd.isna(val) or str(val).strip() in ('', 'NAN', 'None', 'nan'):
                    continue
                if db_field in COLONNES_ARGENT:
                    data[db_field] = clean_money(val)
                elif db_field == 'identifiant':
                    data[db_field] = clean_identifiant(val)
                elif db_field == 'gestionnaire':
                    data[db_field] = trouver_agent_intelligent(val, agents_db)
                else:
                    data[db_field] = str(val).strip().upper()

            ident = data.get('identifiant', '')
            if not ident:
                stats['ignores'] += 1
                continue

            # ✅ Auto-déduction daïra depuis commune si daïra vide
            if not data.get('daira') and data.get('commune'):
                d_deduite = deduire_daira_de_commune(data['commune'])
                if d_deduite:
                    data['daira'] = d_deduite

            champs_dyn = extraire_champs_dynamiques(row, colonnes_mappees, list(df.columns))

            if affectation_auto and not data.get('gestionnaire'):
                agent_zone = trouver_agent_par_zone(data.get('daira',''), data.get('commune',''), session)
                if agent_zone:
                    data['gestionnaire'] = agent_zone
                else:
                    stats['non_assignes'] += 1

            # ✅ MATCHING 3 NIVEAUX (recouvrement uniquement) : identifiant → nom → date_naissance+nom
            exist = verifier_doublon(session, ident, env, badge)
            if not exist and badge == 'in_recouvrement':
                ident_norm = ident.strip().upper() if ident else ''
                # Niveau 1 : par identifiant (instantané)
                if ident_norm and ident_norm in _cache_by_ident:
                    exist = session.get(Dossier, _cache_by_ident[ident_norm])
                # Niveau 2 : par nom + prénom (similarité 80%)
                if not exist:
                    nom_imp = data.get('nom','')
                    prenom_imp = data.get('prenom','')
                    if nom_imp:
                        nom_full_imp = normaliser_nom(f"{nom_imp} {prenom_imp}")
                        prefixe_imp = nom_full_imp[:2] if len(nom_full_imp) >= 2 else nom_full_imp
                        for cand_id, cand_nom_norm, cand_prefixe, cand_date in _cache_by_nom:
                            if prefixe_imp and cand_prefixe and prefixe_imp != cand_prefixe:
                                continue
                            score = difflib.SequenceMatcher(None, nom_full_imp, cand_nom_norm).ratio()
                            if score >= 0.80:
                                exist = session.get(Dossier, cand_id)
                                break
                # Niveau 3 : par date de naissance + nom partiel
                if not exist:
                    date_imp = data.get('date_naissance','').strip()
                    nom_imp_norm = normaliser_nom(data.get('nom',''))
                    if date_imp and date_imp in _cache_by_date and nom_imp_norm:
                        for cand_id, cand_nom_norm in _cache_by_date[date_imp]:
                            if nom_imp_norm in cand_nom_norm or cand_nom_norm in nom_imp_norm:
                                exist = session.get(Dossier, cand_id)
                                break

                # ✅ Si trouvé : MISE À JOUR CIBLÉE (3 champs + remplir vides)
                if exist:
                    exist.in_recouvrement = 'OUI'
                    # Champs recouvrement à mettre à jour
                    for champ in ['nb_echeance_tombee', 'montant_rembourse', 'reste_rembourser', 'total_echue', 'date_ech_tomb', 'prochaine_ech', 'etat_dette', 'anticip', 'ech_anticip', 'observations']:
                        if champ in data and data[champ] not in (None, '', 0, 0.0):
                            setattr(exist, champ, data[champ])
                    # Remplir commune/daira UNIQUEMENT si vides
                    if (not exist.commune or exist.commune.strip() == '') and data.get('commune'):
                        exist.commune = data['commune']
                    if (not exist.daira or exist.daira.strip() == '') and data.get('daira'):
                        exist.daira = data['daira']
                    # Remplir adresse si vide
                    if (not exist.adresse or exist.adresse.strip() == '') and data.get('adresse'):
                        exist.adresse = data['adresse']
                    # Champs dynamiques
                    try:
                        cd_e = json.loads(exist.champs_dynamiques or '{}')
                    except Exception:
                        cd_e = {}
                    cd_e.update(champs_dyn)
                    exist.champs_dynamiques = json.dumps(cd_e, ensure_ascii=False)
                    stats['mis_a_jour'] += 1
                    continue  # ⏭️ on saute le bloc de création standard

            if exist:
                for k, v in data.items():
                    if v is not None and v != '':
                        setattr(exist, k, v)
                try:
                    cd_exist = json.loads(exist.champs_dynamiques or '{}')
                except Exception:
                    cd_exist = {}
                cd_exist.update(champs_dyn)
                exist.champs_dynamiques = json.dumps(cd_exist, ensure_ascii=False)
                stats['mis_a_jour'] += 1
            else:
                if badge == 'in_finance':
                    pnr = float(data.get('montant_pnr', 0.0) or 0.0)
                    if pnr <= 40000:
                        stats['ignores'] += 1
                        continue
                data['type_dispositif']   = env
                data['est_nouveau']       = 'OUI'
                data[badge]               = 'OUI'
                autre = 'in_recouvrement' if badge == 'in_finance' else 'in_finance'
                data[autre]               = 'NON'
                data['champs_dynamiques'] = json.dumps(champs_dyn, ensure_ascii=False)
                session.add(Dossier(**data))
                stats['crees'] += 1

        except Exception as e:
            stats['erreurs'].append(f"Ligne {idx}: {str(e)}")

        # ✅ Commit périodique toutes les 100 lignes pour libérer la mémoire
        if (idx + 1) % 100 == 0:
            try:
                session.commit()
            except Exception:
                session.rollback()

    return stats

# ==========================================
# PDF
# ==========================================

def generer_fiche_promoteur_pdf(dos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 12, "FICHE OFFICIELLE PROMOTEUR - ANGEM", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 6, f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}", ln=True, align='C')
    pdf.ln(3)
    _pdf_section(pdf, "1. IDENTIFICATION")
    _pdf_ligne2(pdf, f"ID: {clean_pdf_text(dos.identifiant)}", f"Agent: {clean_pdf_text(dos.gestionnaire)}")
    _pdf_ligne2(pdf, f"Nom: {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", f"Tel: {clean_pdf_text(dos.telephone)}")
    _pdf_ligne1(pdf, f"Adresse: {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)} - {clean_pdf_text(dos.daira)}")
    pdf.ln(2)
    _pdf_section(pdf, "2. FINANCEMENT")
    _pdf_ligne2(pdf, f"Dispositif: {clean_pdf_text(dos.type_dispositif)}", f"Banque: {clean_pdf_text(dos.banque_nom)}")
    _pdf_ligne2(pdf, f"Activite: {clean_pdf_text(dos.activite)}", f"Num OV: {clean_pdf_text(dos.num_ordre_versement)}")
    _pdf_ligne2(pdf, f"Credit PNR: {dos.montant_pnr:,.0f} DA", f"Date: {clean_pdf_text(dos.date_financement)}")
    pdf.ln(2)
    _pdf_section(pdf, "3. RECOUVREMENT")
    _pdf_ligne2(pdf, f"Rembourse: {dos.montant_rembourse:,.0f} DA", f"Reste: {dos.reste_rembourser:,.0f} DA")
    _pdf_ligne2(pdf, f"Echue: {dos.total_echue:,.0f} DA", f"Etat: {clean_pdf_text(dos.etat_dette)}")
    _pdf_ligne1(pdf, f"Ech. Tombees: {clean_pdf_text(dos.nb_echeance_tombee)} | Prochaine: {clean_pdf_text(dos.prochaine_ech)}")
    try:
        cd = json.loads(dos.champs_dynamiques or '{}')
    except Exception:
        cd = {}
    if cd:
        pdf.ln(2)
        _pdf_section(pdf, "4. INFORMATIONS COMPLEMENTAIRES")
        for k, v in cd.items():
            _pdf_ligne1(pdf, f"{clean_pdf_text(k)}: {clean_pdf_text(v)}")
    if dos.observations:
        pdf.ln(2)
        _pdf_section(pdf, "5. OBSERVATIONS")
        pdf.set_font("Arial", '', 9)
        pdf.multi_cell(0, 6, clean_pdf_text(dos.observations))
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data

def _pdf_section(pdf, titre):
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(0, 7, titre, border=1, ln=True, fill=True)
    pdf.set_font("Arial", '', 9)

def _pdf_ligne2(pdf, g, d):
    pdf.cell(95, 6, g, border='LRB')
    pdf.cell(95, 6, d, border='RB', ln=True)

def _pdf_ligne1(pdf, texte):
    pdf.cell(0, 6, texte, border='LRB', ln=True)

def generer_rapport_global_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "ETAT GLOBAL DES DOSSIERS - ANGEM", ln=True, align='C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 8, f"Total Dossiers: {len(df)}", ln=True)
    pdf.cell(0, 8, f"PNR Engage: {df['montant_pnr'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Total Recouvre: {df['montant_rembourse'].astype(float).sum():,.0f} DA", ln=True)
    pdf.cell(0, 8, f"Reste a Recouvrer: {df['reste_rembourser'].astype(float).sum():,.0f} DA", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data

# ==========================================
# CONNEXION — GRILLE AGENTS
# ==========================================

def login_page():
    st.markdown("<br><h2 style='text-align:center; color:#1e293b; font-weight:800;'>Portail de Connexion ANGEM</h2>", unsafe_allow_html=True)
    COULEURS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#14b8a6','#f97316']

    if st.session_state.portal_selection is None:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👩‍💻\n\nAccompagnateurs", use_container_width=True):
                st.session_state.portal_selection = "agent"
        with c2:
            if st.button("💰\n\nService Finance", use_container_width=True):
                st.session_state.portal_selection = "finance"
        with c3:
            if st.button("👑\n\nDirection & Admin", use_container_width=True):
                st.session_state.portal_selection = "admin"
        # ✅ Bouton Communication
        _, c_com, _ = st.columns([1, 1, 1])
        with c_com:
            if st.button("📢\n\nService Communication", use_container_width=True):
                st.session_state.portal_selection = "communication"

    elif st.session_state.portal_selection == "agent":
        if st.button("⬅️ Retour"):
            st.session_state.portal_selection = None
            st.session_state.agent_choisi = None
            st.rerun()

        with get_session() as session:
            agents = session.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()
            agents_data = [(a.nom, a.mot_de_passe, a.daira) for a in agents]

        if st.session_state.agent_choisi is None:
            st.markdown("<h3 style='text-align:center; color:#64748b; margin-bottom:20px;'>Choisissez votre profil</h3>", unsafe_allow_html=True)
            cols = st.columns(3)
            for i, (nom, pwd, daira) in enumerate(agents_data):
                initiales = ''.join([p[0] for p in nom.strip().split()[:2]]).upper()
                couleur = COULEURS[i % len(COULEURS)]
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class='agent-card'>
                        <div style='width:64px; height:64px; border-radius:50%; background:{couleur};
                             color:white; font-size:22px; font-weight:800;
                             display:flex; align-items:center; justify-content:center; margin:0 auto 12px;'>{initiales}</div>
                        <div style='font-weight:700; font-size:15px; color:#1e293b;'>{nom}</div>
                        <div style='font-size:12px; color:#64748b; margin-top:4px;'>{daira or "—"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Sélectionner", key=f"sel_{i}", use_container_width=True):
                        st.session_state.agent_choisi = (nom, pwd, daira)
                        st.rerun()
        else:
            nom, pwd_db, daira = st.session_state.agent_choisi
            initiales = ''.join([p[0] for p in nom.strip().split()[:2]]).upper()
            st.markdown(f"""
            <div style='max-width:400px; margin:0 auto; background:#fff; border-radius:16px;
                 padding:30px; text-align:center; box-shadow:0 8px 24px rgba(0,0,0,0.08);'>
                <div style='width:80px; height:80px; border-radius:50%; background:{theme_color};
                     color:white; font-size:28px; font-weight:800;
                     display:flex; align-items:center; justify-content:center; margin:0 auto 15px;'>{initiales}</div>
                <h3 style='margin:0 0 5px;'>{nom}</h3>
                <p style='color:#64748b; margin:0 0 20px;'>{daira or ""}</p>
            </div>
            <div style='max-width:400px; margin:15px auto 0;'>
            """, unsafe_allow_html=True)
            env = st.selectbox("🏢 Dispositif", ["PNR PROJET", "PNR AMP"])
            pwd = st.text_input("🔑 Mot de passe", type="password")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⬅️ Changer", use_container_width=True):
                    st.session_state.agent_choisi = None
                    st.rerun()
            with c2:
                if st.button("🚀 Connexion", type="primary", use_container_width=True):
                    if pwd == pwd_db:
                        st.session_state.user = {"nom": nom, "role": "agent", "daira": daira, "env": env}
                        st.session_state.agent_choisi = None
                        st.rerun()
                    else:
                        st.error("Mot de passe incorrect.")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        if st.button("⬅️ Retour"):
            st.session_state.portal_selection = None
            st.rerun()
        with get_session() as session:
            users = session.query(UtilisateurAuth).filter_by(role=st.session_state.portal_selection).all()
            users_data = [(u.nom, u.mot_de_passe, u.role, u.daira) for u in users]
        if users_data:
            st.markdown("<div class='modern-card' style='max-width:500px; margin:0 auto;'>", unsafe_allow_html=True)
            noms = [u[0] for u in users_data]
            nom_sel = st.selectbox("👤 Profil", noms)
            pwd     = st.text_input("🔑 Mot de passe", type="password")
            env     = st.selectbox("🏢 Dispositif", ["PNR PROJET", "PNR AMP"])
            if st.button("🚀 Connexion", type="primary", use_container_width=True):
                user_data = next(u for u in users_data if u[0] == nom_sel)
                if user_data[1] == pwd:
                    st.session_state.user = {"nom": user_data[0], "role": user_data[2], "daira": user_data[3], "env": env}
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================

def sidebar_menu():
    role  = st.session_state.user['role']
    env   = st.session_state.user['env']
    daira = st.session_state.user.get('daira', '')

    st.sidebar.markdown(f"""
    <div style='background:#fff; padding:20px; border-radius:16px; border:1px solid #e2e8f0; text-align:center; margin-bottom:25px;'>
        <div style='font-size:30px;'>👤</div>
        <div style='font-weight:800;'>{st.session_state.user['nom']}</div>
        <div style='color:#64748b; font-size:12px;'>{daira}</div>
        <div style='margin-top:5px; background:{theme_color}; color:white; padding:4px; border-radius:10px; font-size:11px;'>{env}</div>
    </div>
    """, unsafe_allow_html=True)

    if role == 'agent':
        try:
            with get_session() as s:
                nvx = s.query(Dossier).filter(
                    Dossier.type_dispositif == env,
                    Dossier.gestionnaire == st.session_state.user['nom'].upper(),
                    Dossier.est_nouveau == 'OUI',
                    Dossier.in_finance == 'OUI'
                ).count()
            if nvx > 0:
                st.sidebar.markdown(f"<div style='text-align:center; margin-bottom:10px;'><span class='badge-nouveau'>🔴 {nvx} nouveau(x)</span></div>", unsafe_allow_html=True)
        except Exception:
            pass

    if role == "finance":
        opts = ["📂 Mes Dossiers", "📥 Import Financement"]
    elif role == "admin":
        opts = ["📂 Mes Dossiers", "📊 Bilans & Reporting", "⚙️ Administration"]
    elif role == "communication":
        opts = ["🔍 Recherche Promoteurs"]
    else:
        opts = ["📂 Mes Dossiers", "🗑️ Corbeille"]

    choice = st.sidebar.radio("Navigation", opts, label_visibility="collapsed")
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.session_state.portal_selection = None
        st.rerun()
    return choice

# ==========================================
# PROFIL PROMOTEUR
# ==========================================

def afficher_profil_complet(dos_id):
    with get_session() as session:
        dos = session.get(Dossier, dos_id)
        if not dos:
            st.error("Dossier introuvable.")
            return
        if dos.est_nouveau == 'OUI' and similarite(dos.gestionnaire, st.session_state.user['nom']) >= 0.80:
            dos.est_nouveau = 'NON'
        taux = (dos.montant_rembourse / dos.montant_pnr) if dos.montant_pnr and dos.montant_pnr > 0 else 0
        # ✅ Initiales pour avatar
        initiales = ''.join([p[0] for p in (dos.nom or 'XX').split()[:2] if p])[:2].upper() or "??"
        # Couleur par genre
        couleur_avatar = "#3b82f6" if str(dos.genre).upper().startswith(('M','H')) else "#ec4899"
        st.markdown(f"""
        <div class='profil-header'>
            <div style='display:flex; align-items:center; gap:18px;'>
                <div style='width:72px; height:72px; border-radius:50%; background:{couleur_avatar};
                     color:white; font-size:24px; font-weight:800; font-family:Outfit,sans-serif;
                     display:flex; align-items:center; justify-content:center;
                     box-shadow:0 4px 12px rgba(0,0,0,0.15);'>{initiales}</div>
                <div>
                    <h2 style='margin:0; font-size:24px;'>{dos.nom} {dos.prenom}</h2>
                    <p style='margin:4px 0; color:#64748b; font-size:14px;'>🆔 {dos.identifiant} • 🏭 {dos.activite or "Activité non précisée"}</p>
                    <p style='margin:0; color:#475569; font-size:13px;'>📍 {dos.adresse or ""} — <b>{dos.commune}</b> ({dos.daira})</p>
                </div>
            </div>
            <div style='text-align:right;'>
        <div style='font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; font-weight:700;'>Statut du dossier</div>
                <div style='font-family:Outfit,sans-serif; font-weight:700; color:{theme_color}; font-size:18px; margin-top:4px;'>{dos.statut_dossier}</div>
                <div style='margin-top:6px; font-size:12px; color:#64748b;'>👤 Agent : <b>{dos.gestionnaire or "Non assigné"}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ✅ NOUVELLE SECTION : IDENTITÉ COMPLÈTE
        with st.expander("👤 Identité complète du promoteur", expanded=True):
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.8;'>
                    <b>📛 Nom :</b> {dos.nom or '—'}<br>
                    <b>📛 Prénom :</b> {dos.prenom or '—'}<br>
                    <b>🆔 Identifiant :</b> {dos.identifiant or '—'}<br>
                    <b>👫 Genre :</b> {dos.genre or '—'}
                </div>
                """, unsafe_allow_html=True)
            with ic2:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.8;'>
                    <b>🎂 Date naissance :</b> {dos.date_naissance or '—'}<br>
                    <b>🎯 Âge :</b> {dos.age or '—'}<br>
                    <b>📚 Instruction :</b> {dos.niveau_instruction or '—'}<br>
                    <b>📞 Téléphone :</b> {dos.telephone or '—'}
                </div>
                """, unsafe_allow_html=True)
            with ic3:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.8;'>
                    <b>🏠 Adresse :</b> {dos.adresse or '—'}<br>
                    <b>🏘️ Commune :</b> {dos.commune or '—'}<br>
                    <b>🏛️ Daïra :</b> {dos.daira or '—'}<br>
                    <b>🌍 Wilaya :</b> {dos.wilaya or '—'}
                </div>
                """, unsafe_allow_html=True)

        # ✅ SECTION PROJET
        with st.expander("🏭 Détails du projet", expanded=False):
            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.8;'>
                    <b>🔧 Activité :</b> {dos.activite or '—'}<br>
                    <b>🔢 Code activité :</b> {dos.code_activite or '—'}<br>
                    <b>📊 Secteur :</b> {dos.secteur or '—'}
                </div>
                """, unsafe_allow_html=True)
            with pc2:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.8;'>
                    <b>📍 Zone :</b> {dos.zone or '—'}<br>
                    <b>🏢 Dispositif :</b> {dos.type_dispositif or '—'}<br>
                    <b>📅 Début exploitation :</b> {dos.debut_consommation or '—'}
                </div>
                """, unsafe_allow_html=True)
        tel = re.sub(r'\D', '', str(dos.telephone or ''))
        if len(tel) >= 9:
            num_wa = '213' + tel[1:] if tel.startswith('0') else tel
            st.markdown(f"""
            <div style='display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;'>
                <a href='tel:{tel}' class='btn-action btn-call'>📞 Appeler</a>
                <a href='https://wa.me/{num_wa}' class='btn-action btn-wa' target='_blank'>💬 WhatsApp</a>
                <a href='http://maps.google.com/?q={dos.adresse}+{dos.commune}' class='btn-action btn-maps' target='_blank'>🗺️ Maps</a>
            </div>
            """, unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class='block-finance'>
                <div class='block-title'>🏦 Financement</div>
                <b>PNR :</b> {dos.montant_pnr:,.0f} DA<br>
                <b>OV :</b> {dos.num_ordre_versement}<br>
                <b>Banque :</b> {dos.banque_nom} — {dos.agence_bancaire}<br>
                <b>Date :</b> {dos.date_financement}
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class='block-recouvrement'>
                <div class='block-title'>📈 Recouvrement</div>
                <b>Remboursé :</b> {dos.montant_rembourse:,.0f} DA<br>
                <b>Reste :</b> <span style='color:#dc2626;'><b>{dos.reste_rembourser:,.0f} DA</b></span><br>
                <b>Échue :</b> {dos.total_echue:,.0f} DA<br>
                <b>Échéances tombées :</b> {dos.nb_echeance_tombee} ({dos.date_ech_tomb})<br>
                <b>Prochaine :</b> {dos.prochaine_ech}<br>
                <b>État :</b> {dos.etat_dette}
            </div>
            """, unsafe_allow_html=True)
        st.progress(min(taux, 1.0))
        st.caption(f"Progression remboursement : {taux*100:.1f}%")
        # ✅ NOUVEAU : Bouton spécial "Tous les détails recouvrement"
        with st.expander("📊 Voir tous les détails du recouvrement", expanded=False):
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.9;'>
                    <b>💰 Montant PNR :</b> {dos.montant_pnr:,.0f} DA<br>
                    <b>✅ Total remboursé :</b> {dos.montant_rembourse:,.0f} DA<br>
                    <b>⏳ Reste à rembourser :</b> {dos.reste_rembourser:,.0f} DA<br>
                    <b>💸 Total échue :</b> {dos.total_echue:,.0f} DA<br>
                    <b>📅 Échéances tombées :</b> {dos.nb_echeance_tombee or '—'}<br>
                    <b>📆 Date dernière échéance :</b> {dos.date_ech_tomb or '—'}
                </div>
                """, unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.9;'>
                    <b>🗓️ Prochaine échéance :</b> {dos.prochaine_ech or '—'}<br>
                    <b>🚦 État de la dette :</b> {dos.etat_dette or '—'}<br>
                    <b>⚡ Anticipation :</b> {dos.anticip or '—'}<br>
                    <b>📊 Échéance anticipation :</b> {dos.ech_anticip or '—'}<br>
                    <b>🏦 Banque :</b> {dos.banque_nom or '—'}<br>
                    <b>🔢 N° Compte :</b> {dos.numero_compte or '—'}
                </div>
                """, unsafe_allow_html=True)
            if dos.observations:
                st.markdown(f"<div style='margin-top:12px; padding:12px; background:#fef3c7; border-radius:8px;'><b>📝 Observations :</b> {dos.observations}</div>", unsafe_allow_html=True)
            taux_local = (dos.montant_rembourse / dos.montant_pnr * 100) if dos.montant_pnr > 0 else 0
            st.progress(min(taux_local/100, 1.0))
            st.caption(f"Progression : **{taux_local:.1f}%** remboursé")

        try:
            champs_dyn = json.loads(dos.champs_dynamiques or '{}')
        except Exception:
            champs_dyn = {}
        if champs_dyn:
            with st.expander(f"📋 Informations complémentaires ({len(champs_dyn)} champs)", expanded=False):
                items = list(champs_dyn.items())
                for i in range(0, len(items), 2):
                    cols = st.columns(2)
                    for j, (k, v) in enumerate(items[i:i+2]):
                        with cols[j]:
                            new_val = st.text_input(k, value=v, key=f"dyn_{dos_id}_{k}")
                            if new_val != v:
                                champs_dyn[k] = new_val
                if st.button("💾 Sauvegarder", key=f"save_dyn_{dos_id}"):
                    dos.champs_dynamiques = json.dumps(champs_dyn, ensure_ascii=False)
                    st.success("Champs mis à jour !")
                    st.rerun()
        col_g, col_d = st.columns([1.5, 1])
        with col_g:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📝 Historique & Observations**")
            if dos.observations:
                st.info(f"**Obs Excel :** {dos.observations}")
            note = st.text_area("Ajouter un compte-rendu :", key=f"n_{dos_id}")
            if st.button("Enregistrer", key=f"bn_{dos_id}"):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                dos.historique_visites = f"🔹 **[{date_str}]** {note}\n" + (dos.historique_visites or "")
                st.rerun()
            hist = (dos.historique_visites or 'Aucun rapport enregistré').replace('\n', '<br>')
            st.markdown(f"<div style='background:#f8fafc; padding:15px; border-radius:8px; height:200px; overflow-y:auto;'>{hist}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_d:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📎 Documents**")
            pdf_data = generer_fiche_promoteur_pdf(dos)
            st.download_button("📄 Fiche PDF", data=pdf_data,
                               file_name=f"ANGEM_{dos.identifiant}.pdf", mime="application/pdf",
                               use_container_width=True)
            with st.expander("📸 Joindre un document"):
                cam     = st.camera_input("Caméra", key=f"c_{dos_id}")
                file_up = st.file_uploader("Fichier", key=f"f_{dos_id}")
                if st.button("☁️ Archiver", key=f"u_{dos_id}"):
                    data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                    if data:
                        try:
                            fname = f"{dos.identifiant}_{int(datetime.now().timestamp())}.jpg"
                            supabase_client.storage.from_("scans_angem").upload(
                                file=data, path=fname, file_options={"content-type": "image/jpeg"})
                            dos.documents = (dos.documents or "") + fname + "|"
                            st.success("Archivé !")
                        except Exception as e:
                            st.error(f"Erreur: {e}")
            if dos.documents:
                for d in [x for x in dos.documents.split('|') if x]:
                    url = supabase_client.storage.from_('scans_angem').get_public_url(d)
                    st.markdown(f"📥 <a href='{url}' target='_blank'>Voir document</a>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# VUE GESTION
# ==========================================

def page_gestion(mode="financement", vue_admin=False):
    env       = st.session_state.user['env']
    role      = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    # ✅ Mode unifié : un dossier apparait s'il est dans Finance OU Recouvrement
    is_unifie = (mode == "unifie")
    if is_unifie:
        badge_filter = "(in_finance='OUI' OR in_recouvrement='OUI')"
    else:
        badge = "in_finance" if mode == "financement" else "in_recouvrement"
        badge_filter = f"{badge}='OUI'"

    if (is_unifie or mode == "financement") and role in ("finance", "admin"):
        st.markdown("<div class='import-rapide-box'>", unsafe_allow_html=True)
        col_imp1, col_imp2 = st.columns([3, 1])
        with col_imp1:
            st.markdown("**📥 Import rapide — Nouveaux dossiers financés**")
            st.caption("Importe et affecte automatiquement les dossiers aux accompagnateurs.")
        with col_imp2:
            if st.button("📂 Importer", key="btn_import_rapide", use_container_width=True):
                st.session_state.import_quick_open = not st.session_state.import_quick_open
        st.markdown("</div>", unsafe_allow_html=True)
        if st.session_state.import_quick_open:
            with st.expander("🚀 Import rapide", expanded=True):
                _widget_import_rapide(env)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(f"SELECT * FROM dossiers WHERE type_dispositif=:env AND {badge_filter} ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    # ✅ MÉTRIQUES ADMIN — total dossiers + non assignés
    if role == 'admin':
        try:
            with engine.connect() as conn:
                df_stats = pd.read_sql_query(
                    text("SELECT gestionnaire FROM dossiers WHERE type_dispositif=:env"),
                    conn, params={"env": env}
                ).fillna('')
            total_dos = len(df_stats)
            non_assignes = len(df_stats[df_stats['gestionnaire'].apply(
                lambda x: str(x).strip().upper() in ('','NAN','NONE','NON','-','N/A'))])
            assignes = total_dos - non_assignes
            taux = (assignes / total_dos * 100) if total_dos > 0 else 0
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📂 Total Dossiers", total_dos)
            c2.metric("✅ Assignés", assignes)
            c3.metric("⚠️ Non Assignés", non_assignes,
                      delta=f"-{non_assignes}" if non_assignes > 0 else None,
                      delta_color="inverse")
            c4.metric("📈 Taux affectation", f"{taux:.1f}%")
        except Exception:
            pass

    if role == 'agent':
        nvx = len(df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80) & (df['est_nouveau'] == 'OUI')])
        if nvx > 0:
            st.markdown(f"<div class='alerte-nouveau'>🎉 {nvx} nouveau(x) dossier(s) vous ont été affectés !</div>", unsafe_allow_html=True)

        # ✅ STATISTIQUES PERSONNELLES DE L'AGENT
        df_agent_stats = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        try:
            df_agent_stats['montant_pnr']        = pd.to_numeric(df_agent_stats['montant_pnr'], errors='coerce').fillna(0.0)
            df_agent_stats['montant_rembourse']  = pd.to_numeric(df_agent_stats['montant_rembourse'], errors='coerce').fillna(0.0)
            df_agent_stats['reste_rembourser']   = pd.to_numeric(df_agent_stats['reste_rembourser'], errors='coerce').fillna(0.0)
        except Exception:
            pass
        nb_dos     = len(df_agent_stats)
        tot_pnr    = float(df_agent_stats['montant_pnr'].sum()) if 'montant_pnr' in df_agent_stats else 0
        tot_remb   = float(df_agent_stats['montant_rembourse'].sum()) if 'montant_rembourse' in df_agent_stats else 0
        tot_reste  = float(df_agent_stats['reste_rembourser'].sum()) if 'reste_rembourser' in df_agent_stats else 0
        taux_perso = (tot_remb / tot_pnr * 100) if tot_pnr > 0 else 0
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Outfit; font-size:18px; font-weight:700; margin-bottom:14px;'>📊 Mon tableau de bord</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📂</div><div class='stat-val'>{nb_dos}</div><div class='stat-lbl'>Mes Dossiers</div></div>", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>💰</div><div class='stat-val'>{tot_pnr/1_000_000:.1f}M</div><div class='stat-lbl'>PNR Total (DA)</div></div>", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>✅</div><div class='stat-val'>{tot_remb/1_000_000:.1f}M</div><div class='stat-lbl'>Recouvré (DA)</div></div>", unsafe_allow_html=True)
        with sc4:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>⏳</div><div class='stat-val'>{tot_reste/1_000_000:.1f}M</div><div class='stat-lbl'>Reste (DA)</div></div>", unsafe_allow_html=True)
        with sc5:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📈</div><div class='stat-val'>{taux_perso:.1f}%</div><div class='stat-lbl'>Taux Recouvr.</div></div>", unsafe_allow_html=True)
        st.progress(min(taux_perso/100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)



    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 1, 1])
    tmp_s = c1.text_input("🔍 Recherche rapide...", value=st.session_state.search_query, label_visibility="collapsed")
    if c2.button("Chercher", type="primary", use_container_width=True):
        st.session_state.search_query = tmp_s
        st.rerun()
    if c3.button("❌ Effacer", use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.search_query:
        q = st.session_state.search_query
        df = df[df.apply(lambda x: x.astype(str).str.contains(q, case=False).any(), axis=1)]

    # ✅ FILTRE AGENT — matching renforcé (similarité + tokens)
    if not vue_admin and role == "agent":
        def match_agent_robuste(nom_db):
            """Matching combiné : similarité 75% OU 2 tokens communs OU inclusion complète."""
            if not str(nom_db).strip() or str(nom_db).strip().upper() in ('NAN','NONE',''):
                return False
            nom_db_norm    = normaliser_nom(str(nom_db))
            nom_agent_norm = normaliser_nom(nom_agent)
            if not nom_db_norm or not nom_agent_norm:
                return False
            # Critère 1 : similarité globale >= 75%
            if similarite(nom_db_norm, nom_agent_norm) >= 0.75:
                return True
            # Critère 2 : tous les tokens de l'agent présents dans le gestionnaire
            tokens_agent = set(re.split(r'[\s\-_\.]+', nom_agent_norm)) - {'', 'MME', 'MR', 'MLLE'}
            tokens_db    = set(re.split(r'[\s\-_\.]+', nom_db_norm))    - {'', 'MME', 'MR', 'MLLE'}
            tokens_agent = {t for t in tokens_agent if len(t) > 1}
            if tokens_agent and tokens_agent.issubset(tokens_db):
                return True
            # Critère 3 : au moins 2 tokens communs (nom + prénom)
            communs = tokens_agent & tokens_db
            if len(communs) >= min(2, len(tokens_agent)):
                return True
            return False

        df_filtre = df[df['gestionnaire'].apply(match_agent_robuste)]
        if df_filtre.empty and not df.empty:
            with st.expander("⚠️ Aucun dossier trouvé — Diagnostic", expanded=True):
                st.warning(f"Votre nom : **{nom_agent}**")
                noms = [n for n in df['gestionnaire'].dropna().unique().tolist() if str(n).strip() not in ('','NAN')]
                st.info("Noms dans la base :")
                st.write(noms[:30] if noms else "Aucun gestionnaire assigné.")
        df = df_filtre

    df.insert(0, "Ouvrir 📂", False)

    try:
        with engine.connect() as conn:
            df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", conn)
        noms_db = df_agents['nom'].dropna().tolist()
        noms_dossiers = df['gestionnaire'].dropna().tolist()
        liste_agents = [""] + sorted(set(noms_db + noms_dossiers))
    except Exception:
        liste_agents = [""]

    # ✅ ADMIN : édition libre de TOUTES les colonnes
    is_admin = (role == 'admin')

    # ✅ Indicateur visuel : 🟢 complet | 🟡 finance seule | 🔴 recouvrement seul
    def calc_statut_dos(row):
        f = str(row.get('in_finance','NON')).upper() == 'OUI'
        r = str(row.get('in_recouvrement','NON')).upper() == 'OUI'
        if f and r: return "🟢 Complet"
        if f: return "🟡 Finance"
        if r: return "🔴 Recouvr."
        return "⚪"
    df['statut_data'] = df.apply(calc_statut_dos, axis=1)

    if is_unifie:
        if is_admin:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","telephone","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "statut_data": st.column_config.TextColumn("Données", disabled=True, width="small"),
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    elif mode == "financement":
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","agence_bancaire","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    else:
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","montant_pnr","montant_rembourse","reste_rembourser","total_echue","etat_dette","nb_echeance_tombee","prochaine_ech","gestionnaire","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","montant_pnr","montant_rembourse","reste_rembourser","etat_dette","gestionnaire","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "montant_pnr": st.column_config.NumberColumn("Crédit", format="%d DA", disabled=not is_admin),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA", disabled=not is_admin),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA", disabled=not is_admin),
            "total_echue": st.column_config.NumberColumn("Échue", format="%d DA", disabled=not is_admin),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=not is_admin) if is_admin else st.column_config.TextColumn("Agent", disabled=True),
        }

    cols = [c for c in cols if c in df.columns or c == "Ouvrir 📂"]
    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(df[cols], use_container_width=True, hide_index=True, column_config=config, height=500)

    if st.button("💾 Sauvegarder", type="primary"):
        with get_session() as session:
            for _, r in edited.iterrows():
                dos = session.get(Dossier, int(r['id']))
                if dos:
                    if is_admin:
                        # Admin : sauve TOUTES les colonnes affichées
                        for col_name in edited.columns:
                            if col_name in ('Ouvrir 📂', 'id'):
                                continue
                            val = r[col_name]
                            if hasattr(dos, col_name):
                                if col_name in COLONNES_ARGENT:
                                    try:
                                        setattr(dos, col_name, float(val) if val not in (None, '') else 0.0)
                                    except Exception:
                                        pass
                                else:
                                    setattr(dos, col_name, str(val).strip().upper() if val else "")
                    else:
                        if mode == "financement":
                            dos.statut_dossier = r.get('statut_dossier', dos.statut_dossier)
                            if role != 'agent':
                                dos.gestionnaire = str(r.get('gestionnaire','')).strip().upper()
        st.toast("✅ Modifications enregistrées !")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        afficher_profil_complet(dos_id)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# IMPORT RAPIDE
# ==========================================

def _widget_import_rapide(env):
    f = st.file_uploader("📁 Fichier Excel / CSV", type=['xlsx','xls','csv'], key="f_rapide")
    if not f:
        return
    try:
        df_raw = safe_read_dataframe(f)
    except Exception as e:
        st.error(f"Erreur lecture : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df = fix_colonnes_doublons(df)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(5), use_container_width=True)
    mapping_final = {k: (v if v in excel_cols else "-- Ignorer --") for k, v in mapping_auto.items()}
    with st.expander("🎛️ Ajuster le mapping (optionnel)"):
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        for idx, db_f in enumerate(targets):
            auto_val = mapping_final.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"mr_{db_f}")
    if st.button("🚀 Lancer l'import", type="primary", key="btn_go_rapide"):
        with get_session() as session:
            agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
            with st.status("Import en cours...", expanded=True) as status:
                stats = moteur_import(df, mapping_final, env, 'in_finance', session, agents_db, affectation_auto=True)
            status.update(label="✅ Terminé !", state="complete")
        st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
        if stats['non_assignes'] > 0:
            st.warning(f"⚠️ **{stats['non_assignes']}** sans agent → corbeille.")
        if stats['erreurs']:
            with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                for err in stats['erreurs'][:20]:
                    st.code(err)
        st.session_state.import_quick_open = False
        st.rerun()

# ==========================================
# BILANS & REPORTING
# ==========================================

def page_bilans():
    st.title("📊 Bilans & Reporting")
    env = st.session_state.user['env']

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base est vide.")
        return

    for col in COLONNES_ARGENT:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Filtre date
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📅 Filtres")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        periode = st.selectbox("Période", [
            "Toute la base",
            "Cette semaine",
            "Ce mois",
            "Ce trimestre",
            "Cette année",
            "Personnalisée"
        ])
    date_debut = date_fin = None
    if periode == "Personnalisée":
        with col_f2:
            date_debut = st.date_input("Du", value=date(date.today().year, 1, 1))
        with col_f3:
            date_fin = st.date_input("Au", value=date.today())

    # Appliquer filtre date sur date_financement
    df_filtre = df.copy()
    if periode != "Toute la base" and 'date_financement' in df_filtre.columns:
        today = date.today()
        def parse_date(s):
            for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%m/%d/%Y'):
                try:
                    return datetime.strptime(str(s).strip(), fmt).date()
                except Exception:
                    pass
            return None
        df_filtre['_date'] = df_filtre['date_financement'].apply(parse_date)
        if periode == "Cette semaine":
            lun = today - pd.Timedelta(days=today.weekday())
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d >= lun)]
        elif periode == "Ce mois":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.month == today.month and d.year == today.year)]
        elif periode == "Ce trimestre":
            q = (today.month - 1) // 3
            mois_debut = q * 3 + 1
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year and (d.month-1)//3 == q)]
        elif periode == "Cette année":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year)]
        elif periode == "Personnalisée" and date_debut and date_fin:
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and date_debut <= d <= date_fin)]

    st.caption(f"**{len(df_filtre)}** dossiers sélectionnés sur {len(df)} total")
    st.markdown("</div>", unsafe_allow_html=True)

    # Métriques globales
    st.markdown("### 💰 Vue Globale")
    c1, c2, c3, c4 = st.columns(4)
    total_pnr  = df_filtre['montant_pnr'].sum()
    total_remb = df_filtre['montant_rembourse'].sum()
    total_rest = df_filtre['reste_rembourser'].sum()
    taux_global = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
    c1.metric("Total Dossiers", len(df_filtre))
    c2.metric("PNR Engagé", f"{total_pnr:,.0f} DA")
    c3.metric("Total Recouvré", f"{total_remb:,.0f} DA")
    c4.metric("Reste", f"{total_rest:,.0f} DA")
    st.progress(min(taux_global / 100, 1.0))
    st.caption(f"Taux de recouvrement global : **{taux_global:.1f}%**")

    # Onglets bilans
    tabs = st.tabs(["👥 Par Agent", "🗺️ Par Zone", "🏭 Par Activité", "🏦 Par Banque", "👤 Par Promoteur", "⚠️ Contentieux"])

    # --- PAR AGENT ---
    with tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        if 'gestionnaire' in df_filtre.columns:
            df_agent = df_filtre.groupby('gestionnaire').agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_agent = df_agent[df_agent['gestionnaire'].str.strip() != ""]
            df_agent['Taux %'] = (df_agent['Recouvre'] / df_agent['PNR'] * 100).fillna(0).round(1)
            df_agent = df_agent.sort_values('Dossiers', ascending=False)
            st.dataframe(df_agent, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_agent.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name="bilan_agents.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ZONE ---
    with tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        zone_col = st.selectbox("Regrouper par", ["daira", "commune", "wilaya", "zone", "adresse"], key="zone_col")
        if zone_col in df_filtre.columns:
            df_zone = df_filtre.groupby(zone_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_zone = df_zone[df_zone[zone_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_zone['Taux %'] = (df_zone['Recouvre'] / df_zone['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_zone, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_zone.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{zone_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ACTIVITÉ ---
    with tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        act_col = st.selectbox("Regrouper par", ["secteur", "activite", "code_activite"], key="act_col")
        if act_col in df_filtre.columns:
            df_act = df_filtre.groupby(act_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_act = df_act[df_act[act_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_act['Taux %'] = (df_act['Recouvre'] / df_act['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_act, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_act.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{act_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR BANQUE ---
    with tabs[3]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        banque_col = st.selectbox("Regrouper par", ["banque_nom", "agence_bancaire"], key="banque_col")
        if banque_col in df_filtre.columns:
            df_banque = df_filtre.groupby(banque_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_banque = df_banque[df_banque[banque_col].str.strip() != ""].sort_values('PNR', ascending=False)
            df_banque['Taux %'] = (df_banque['Recouvre'] / df_banque['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_banque, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_banque.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{banque_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR PROMOTEUR ---
    with tabs[4]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        promo_col = st.selectbox("Regrouper par", ["genre", "niveau_instruction", "statut_dossier"], key="promo_col")
        if promo_col in df_filtre.columns:
            df_promo = df_filtre.groupby(promo_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
            ).reset_index()
            df_promo = df_promo[df_promo[promo_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            st.dataframe(df_promo, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                })
            buf = io.BytesIO()
            df_promo.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{promo_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- CONTENTIEUX ---
    with tabs[5]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        df_cont = df_filtre[
            (df_filtre['etat_dette'].str.upper().str.contains('CONTENTIEUX|RETARD', na=False)) |
            (df_filtre['statut_dossier'] == 'Contentieux / Retard')
        ].copy()
        st.metric("Dossiers en contentieux", len(df_cont))
        if not df_cont.empty:
            st.metric("Montant en souffrance", f"{df_cont['reste_rembourser'].sum():,.0f} DA")
            cols_aff = [c for c in ["identifiant","nom","prenom","gestionnaire","daira","commune","montant_pnr","reste_rembourser","etat_dette","nb_echeance_tombee"] if c in df_cont.columns]
            st.dataframe(df_cont[cols_aff], use_container_width=True, hide_index=True)
            buf = io.BytesIO()
            df_cont[cols_aff].to_excel(buf, index=False)
            st.download_button("📥 Export Contentieux Excel", data=buf.getvalue(), file_name="contentieux.xlsx", use_container_width=True)
            st.download_button("📄 Export Contentieux PDF", data=_generer_contentieux_pdf(df_cont),
                               file_name="Contentieux_ANGEM.pdf", mime="application/pdf", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Export global
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📤 Export Global")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📊 Bilan Global PDF", data=generer_rapport_global_pdf(df_filtre),
                           file_name="Bilan_ANGEM.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        df_exp = df_filtre.copy()
        try:
            dyn = df_exp['champs_dynamiques'].apply(lambda x: json.loads(x) if x and x != '{}' else {})
            df_exp = pd.concat([df_exp.drop(columns=['champs_dynamiques']), pd.json_normalize(dyn)], axis=1)
        except Exception:
            pass
        df_exp.to_excel(buf, index=False)
        st.download_button("🟢 Export Excel Complet", data=buf.getvalue(),
                           file_name="Backup_ANGEM.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _generer_contentieux_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 15, "DOSSIERS EN CONTENTIEUX - ANGEM", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        texte = f"ID:{clean_pdf_text(row.get('identifiant',''))} | {clean_pdf_text(row.get('nom',''))} {clean_pdf_text(row.get('prenom',''))} | Reste:{float(row.get('reste_rembourser',0)):,.0f} DA | Agent:{clean_pdf_text(row.get('gestionnaire',''))}"
        pdf.cell(0, 7, texte, ln=True, border='B')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data

# ==========================================
# ADMINISTRATION
# ==========================================

def page_integration_admin():
    env  = st.session_state.user['env']
    role = st.session_state.user['role']
    st.title("⚙️ Administration")

    if role == "finance":
        tabs = st.tabs(["💰 Import Finance"])
        t1, t2, t3, t4, t5, t6, t7, t8 = tabs[0], None, None, None, None, None, None, None
    else:
        t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
            "💰 Import Finance", "📈 Import Recouvrement",
            "📊 MAJ Remboursement", "👤 MAJ Gestionnaire",
            "🧹 Maintenance", "🔐 Équipes", "🔄 Gestion Agents",
            "👥 Gestionnaires anciens"
        ])

    with t1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx','xls','csv'], key="ff")
        if f_fin:
            _onglet_import_generique(f_fin, env, 'in_finance', "form_fin", "Finance")
        st.markdown("</div>", unsafe_allow_html=True)

    if t2:
        with t2:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx','xls','csv'], key="fr")
            if f_rec:
                # ✅ Mapping limité aux 12 champs du fichier recouvrement
                champs_recouvrement = [
                    'identifiant', 'nom', 'prenom', 'date_naissance',
                    'telephone', 'commune', 'daira', 'type_dispositif',
                    'date_financement', 'total_echue', 'montant_rembourse', 'reste_rembourser'
                ]
                _onglet_import_generique(f_rec, env, 'in_recouvrement', "form_rec", "Recouvrement",
                                         targets_filtre=champs_recouvrement)
            st.markdown("</div>", unsafe_allow_html=True)



    if t4:
        with t4:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            # ✅ Bouton réparation daïras
            if st.button("🔧 Réparer daïras manquantes", type="primary", key="btn_repair_daira"):
                env_r = st.session_state.user['env']
                with get_session() as session:
                    dossiers = session.query(Dossier).filter(Dossier.type_dispositif == env_r).all()
                    c_repare = 0
                    for d in dossiers:
                        if (not d.daira or d.daira.strip() == "") and d.commune:
                            d_deduite = deduire_daira_de_commune(d.commune)
                            if d_deduite:
                                d.daira = d_deduite
                                c_repare += 1
                if c_repare > 0:
                    st.success(f"✅ {c_repare} daïra(s) reconstituée(s) à partir des communes.")
                else:
                    st.info("Aucune daïra à réparer.")
            st.markdown("---")
            if st.button("🧹 Nettoyer Doublons", type="primary"):
                with get_session() as session:
                    dossiers = session.query(Dossier).all()
                    seen = {}
                    ids_del = []
                    for d in dossiers:
                        key = (str(d.identifiant).strip(), d.type_dispositif, d.in_finance, d.in_recouvrement)
                        if key in seen:
                            ids_del.append(d.id)
                        else:
                            seen[key] = d.id
                    if ids_del:
                        session.query(Dossier).filter(Dossier.id.in_(ids_del)).delete(synchronize_session=False)
                        st.success(f"{len(ids_del)} doublons supprimés.")
                    else:
                        st.info("Aucun doublon détecté.")
            st.markdown("---")
            st.error("⚠️ Zone de danger")
            if st.button("🗑️ VIDER TOUTE LA BASE"):
                with get_session() as session:
                    session.query(Dossier).delete()
                st.success("Base vidée.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t5:
        with t5:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            try:
                with engine.connect() as conn:
                    df_u = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", conn)
            except Exception:
                df_u = pd.DataFrame()
            if not df_u.empty:
                ed_u = st.data_editor(df_u, use_container_width=True, hide_index=True,
                    column_config={"id": None,
                                   "identifiant": st.column_config.TextColumn(disabled=True),
                                   "nom": st.column_config.TextColumn(disabled=True),
                                   "daira": st.column_config.SelectboxColumn(options=LISTE_DAIRAS)})
                if st.button("💾 Sauvegarder équipe", type="primary"):
                    with get_session() as session:
                        for _, r in ed_u.iterrows():
                            u = session.get(UtilisateurAuth, int(r['id']))
                            if u:
                                u.mot_de_passe = r['mot_de_passe']
                                u.daira = r['daira']
                    st.success("Équipe mise à jour.")

            st.markdown("---")
            with st.form("ajout_agent"):
                c1, c2, c3 = st.columns([1,1.5,1])
                n_id  = c1.text_input("Identifiant")
                n_nom = c2.text_input("Nom complet")
                n_dai = c3.selectbox("Daïra", LISTE_DAIRAS)
                if st.form_submit_button("Créer le compte") and n_id and n_nom:
                    with get_session() as session:
                        # ✅ Anti-doublon par similarité 80%
                        agents_exist = session.query(UtilisateurAuth).filter_by(role='agent').all()
                        doublon = next((a for a in agents_exist if similarite(a.nom, n_nom) >= 0.80), None)
                        if doublon:
                            st.warning(f"⚠️ Compte similaire existant : **{doublon.nom}**. Vérifiez avant de créer.")
                        elif session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first():
                            st.error("Cet identifiant existe déjà.")
                        else:
                            session.add(UtilisateurAuth(identifiant=n_id.lower(), nom=n_nom.strip().upper(),
                                                        daira=n_dai, mot_de_passe="angem2026", role="agent"))
                            st.success(f"Compte {n_nom} créé !")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t6:
        with t6:
            pass  # ancien onglet gestionnaires — déplacé

    # ✅ ONGLET MAJ REMBOURSEMENT
    if t3:
        with t3:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.info("📊 Mettez à jour uniquement les données de remboursement. PNR, banque et gestionnaire ne sont pas touchés.")
            f_remb = st.file_uploader("Fichier Excel Remboursement", type=['xlsx','xls','csv'], key="f_maj_remb")
            if f_remb:
                try:
                    df_raw = safe_read_dataframe(f_remb)
                except Exception as e:
                    st.error(f"Erreur lecture : {e}")
                    df_raw = None
                if df_raw is not None:
                    df_raw = df_raw.fillna('')
                    header_idx = get_header_row(df_raw)
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    df = fix_colonnes_doublons(df)
                    mapping_auto = auto_mapper(list(df.columns))
                    excel_cols = ["-- Ignorer --"] + list(df.columns)
                    st.success(f"✅ {len(df)} lignes détectées")
                    st.dataframe(df.head(3), use_container_width=True)
                    champs_remb = ['identifiant','nom','prenom','date_naissance',
                                   'montant_rembourse','reste_rembourser','total_echue',
                                   'nb_echeance_tombee','date_ech_tomb','prochaine_ech',
                                   'etat_dette','anticip','ech_anticip','observations']
                    with st.form("form_maj_remb"):
                        st.write("### 🎛️ Mapping Remboursement")
                        c1, c2, c3 = st.columns(3)
                        mapping_final = {}
                        for idx, db_f in enumerate(champs_remb):
                            auto_val = mapping_auto.get(db_f, "-- Ignorer --")
                            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
                            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
                            with col:
                                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"maj_remb_{db_f}")
                        sub = st.form_submit_button("🚀 Mettre à jour les remboursements", type="primary")
                    if sub:
                        _maj_remboursement(df, mapping_final, env)
            st.markdown("</div>", unsafe_allow_html=True)

    # ✅ ONGLET MAJ GESTIONNAIRE
    if t4:
        with t4:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.info("👤 Met à jour UNIQUEMENT le gestionnaire. Les noms sont normalisés pour correspondre exactement aux comptes agents.")
            st.markdown("**Colonnes requises dans le fichier :** `identifiant`, `nom`, `prenom`, `gestionnaire`")
            f_gest_maj = st.file_uploader("Fichier Excel Gestionnaires", type=['xlsx','xls','csv'], key="f_maj_gest")
            if f_gest_maj:
                try:
                    df_raw = safe_read_dataframe(f_gest_maj)
                except Exception as e:
                    st.error(f"Erreur lecture : {e}")
                    df_raw = None
                if df_raw is not None:
                    df_raw = df_raw.fillna('')
                    header_idx = get_header_row(df_raw)
                    df = df_raw.iloc[header_idx:].copy()
                    df.columns = df.iloc[0].astype(str).tolist()
                    df = df.iloc[1:].reset_index(drop=True)
                    df = fix_colonnes_doublons(df)
                    mapping_auto = auto_mapper(list(df.columns))
                    excel_cols = ["-- Ignorer --"] + list(df.columns)
                    st.success(f"✅ {len(df)} lignes détectées")
                    st.dataframe(df.head(3), use_container_width=True)
                    champs_gest = ['identifiant','nom','prenom','gestionnaire']
                    with st.form("form_maj_gest"):
                        st.write("### 🎛️ Mapping Gestionnaire")
                        c1, c2 = st.columns(2)
                        mapping_final = {}
                        for idx, db_f in enumerate(champs_gest):
                            auto_val = mapping_auto.get(db_f, "-- Ignorer --")
                            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
                            col = c1 if idx % 2 == 0 else c2
                            with col:
                                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"maj_gest_{db_f}")
                        sub = st.form_submit_button("🚀 Mettre à jour les gestionnaires", type="primary")
                    if sub:
                        _maj_gestionnaire(df, mapping_final, env)
            st.markdown("</div>", unsafe_allow_html=True)

    if t7:
        with t7:
            _outil_gestion_agents()

    if t8:
        with t8:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.warning("👥 Assigne le gestionnaire sur TOUTES les fiches portant le même ID.")
            f_gest = st.file_uploader("Fichier Gestionnaires", type=['xlsx','xls','csv'], key="fgest_old")
            if f_gest:
                _onglet_import_generique(f_gest, env, 'gestionnaire_only', "form_gest_old", "Gestionnaires")
            st.markdown("</div>", unsafe_allow_html=True)

def _outil_gestion_agents():
    """3 outils : fusion doublons, passation, réécriture noms."""
    st.markdown("### 🔄 Gestion des Agents & Dossiers")

    sous_tabs = st.tabs(["🔁 Fusion Doublons", "📦 Passation de Dossiers", "✏️ Réécriture des Noms"])

    # ==========================================
    # OUTIL 1 — FUSION DOUBLONS AGENTS
    # ==========================================
    with sous_tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Détecte automatiquement les comptes similaires et les fusionne en un seul.")

        with get_session() as session:
            agents = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_data = [(a.id, a.nom, a.daira, a.mot_de_passe) for a in agents]

        # Détecter les groupes similaires
        groupes = []
        traites = set()
        for i, (id1, nom1, d1, pwd1) in enumerate(agents_data):
            if id1 in traites:
                continue
            groupe = [(id1, nom1, d1, pwd1)]
            for j, (id2, nom2, d2, pwd2) in enumerate(agents_data):
                if i != j and id2 not in traites:
                    if similarite(nom1, nom2) >= 0.80:
                        groupe.append((id2, nom2, d2, pwd2))
                        traites.add(id2)
            if len(groupe) > 1:
                traites.add(id1)
                groupes.append(groupe)

        if not groupes:
            st.success("✅ Aucun doublon détecté. Tous les comptes sont uniques.")
        else:
            st.warning(f"⚠️ **{len(groupes)}** groupe(s) de doublons détectés :")
            for g_idx, groupe in enumerate(groupes):
                st.markdown(f"**Groupe {g_idx+1} :**")
                noms_groupe = [f"{nom} ({daira or '—'})" for _, nom, daira, _ in groupe]
                choix = st.selectbox(
                    "Compte à garder :",
                    options=[n[1] for n in groupe],
                    key=f"fusion_keep_{g_idx}"
                )
                st.caption(f"Comptes détectés : {', '.join(noms_groupe)}")

                if st.button(f"🔁 Fusionner ce groupe", key=f"btn_fusion_{g_idx}", type="primary"):
                    id_garde = next(n[0] for n in groupe if n[1] == choix)
                    ids_suppr = [n[0] for n in groupe if n[0] != id_garde]
                    noms_suppr = [n[1] for n in groupe if n[0] != id_garde]

                    with get_session() as session:
                        # Réaffecter tous les dossiers des comptes supprimés vers le compte gardé
                        c_reaffect = 0
                        for nom_s in noms_suppr:
                            dossiers = session.query(Dossier).filter(
                                Dossier.gestionnaire.ilike(f"%{nom_s.split()[0]}%")
                            ).all()
                            for d in dossiers:
                                if similarite(d.gestionnaire, nom_s) >= 0.75:
                                    d.gestionnaire = choix
                                    c_reaffect += 1
                        # Supprimer les comptes doublons
                        for id_s in ids_suppr:
                            u = session.get(UtilisateurAuth, id_s)
                            if u:
                                session.delete(u)

                    st.success(f"✅ Comptes fusionnés. {c_reaffect} dossiers réaffectés vers **{choix}**.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 2 — PASSATION DE DOSSIERS
    # ==========================================
    with sous_tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Transfère tous les dossiers d'un agent vers un autre (changement de poste, départ, etc.)")

        with get_session() as session:
            agents_noms = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()]

        if len(agents_noms) < 2:
            st.warning("Il faut au moins 2 agents.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                agent_source = st.selectbox("👤 Agent qui PART (source)", agents_noms, key="pass_source")
            with col2:
                agents_dest = [a for a in agents_noms if a != agent_source]
                agent_dest  = st.selectbox("👤 Agent qui REPREND (destination)", agents_dest, key="pass_dest")

            env_pass = st.session_state.user['env']

            # Récupérer toutes les communes existantes
            try:
                with engine.connect() as conn:
                    df_temp = pd.read_sql_query(
                        text("SELECT DISTINCT commune FROM dossiers WHERE type_dispositif=:env AND commune != ''"),
                        conn, params={"env": env_pass}
                    )
                liste_communes = [""] + sorted(df_temp['commune'].dropna().tolist())
            except Exception:
                liste_communes = [""]

            col_filtre1, col_filtre2 = st.columns(2)
            with col_filtre1:
                filtre_daira = st.checkbox("🏛️ Filtrer par Daïra", key="pass_filtre_d")
                daira_choisie = ""
                if filtre_daira:
                    daira_choisie = st.selectbox("Daïra", LISTE_DAIRAS, key="pass_daira")
            with col_filtre2:
                filtre_commune = st.checkbox("🏘️ Filtrer par Commune", key="pass_filtre_c")
                commune_choisie = ""
                if filtre_commune:
                    commune_choisie = st.selectbox("Commune", liste_communes, key="pass_commune")

            motif = st.text_input("Motif de la passation (optionnel)", placeholder="Ex: Mutation vers Chéraga")

            # Aperçu
            try:
                with engine.connect() as conn:
                    df_pass = pd.read_sql_query(
                        text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_pass}
                    ).fillna('')
                mask = df_pass['gestionnaire'].apply(lambda x: similarite(x, agent_source) >= 0.80)
                if daira_choisie:
                    # ✅ Filtre intelligent : daïra OU communes de la daïra
                    communes_daira = communes_de_daira(daira_choisie)
                    def match_zone(row):
                        d = str(row.get('daira','')).strip().upper()
                        c = str(row.get('commune','')).strip().upper()
                        if daira_choisie.upper() in d:
                            return True
                        for com in communes_daira:
                            com_n = unicodedata.normalize('NFKD', com.upper()).encode('ascii','ignore').decode('ascii')
                            if com_n in unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii'):
                                return True
                        return False
                    mask = mask & df_pass.apply(match_zone, axis=1)
                if commune_choisie:
                    mask = mask & df_pass['commune'].str.contains(commune_choisie, case=False, na=False)
                df_concernes = df_pass[mask]
                st.metric("Dossiers concernés", len(df_concernes))
                if not df_concernes.empty:
                    st.dataframe(df_concernes[['identifiant','nom','prenom','daira','commune']].head(10), use_container_width=True)
            except Exception:
                df_concernes = pd.DataFrame()

            if st.button("📦 Confirmer la passation", type="primary", key="btn_passation",
                         disabled=df_concernes.empty if not df_concernes.empty else True):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                note = f"🔄 **[Passation {date_str}]** Transféré de {agent_source} vers {agent_dest}"
                if motif:
                    note += f" — Motif : {motif}"
                with get_session() as session:
                    c = 0
                    for _, row in df_concernes.iterrows():
                        d = session.get(Dossier, int(row['id']))
                        if d:
                            d.gestionnaire = agent_dest.strip().upper()
                            d.historique_visites = note + "\n" + (d.historique_visites or "")
                            c += 1
                st.success(f"✅ {c} dossiers transférés de **{agent_source}** vers **{agent_dest}**.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 3 — RÉÉCRITURE DES NOMS
    # ==========================================
    with sous_tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Scanne toute la base et corrige les noms de gestionnaires mal écrits pour les aligner sur les comptes officiels.")

        with get_session() as session:
            agents_officiels = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]

        env_ree = st.session_state.user['env']

        if st.button("🔍 Analyser la base", key="btn_analyse_noms"):
            try:
                with engine.connect() as conn:
                    df_all = pd.read_sql_query(
                        text("SELECT id, gestionnaire FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_ree}
                    ).fillna('')
            except Exception:
                df_all = pd.DataFrame()

            corrections = []
            for _, row in df_all.iterrows():
                gest = str(row['gestionnaire']).strip()
                if not gest or gest.upper() in ('NAN','NONE',''):
                    continue
                meilleur = max(agents_officiels, key=lambda a: similarite(gest, a), default=None)
                if meilleur and similarite(gest, meilleur) >= 0.80 and gest != meilleur:
                    corrections.append({'id': row['id'], 'avant': gest, 'apres': meilleur})

            if not corrections:
                st.success("✅ Tous les noms sont déjà corrects.")
            else:
                df_corr = pd.DataFrame(corrections)
                st.warning(f"**{len(df_corr)}** corrections à appliquer :")
                st.dataframe(df_corr[['avant','apres']], use_container_width=True, hide_index=True)
                if st.button(f"✏️ Appliquer {len(df_corr)} corrections", type="primary", key="btn_appliquer_noms"):
                    with get_session() as session:
                        for corr in corrections:
                            d = session.get(Dossier, corr['id'])
                            if d:
                                d.gestionnaire = corr['apres']
                    st.success(f"✅ {len(corrections)} noms corrigés dans la base.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def _onglet_import_generique(file_obj, env, badge, form_key, label, targets_filtre=None):
    try:
        df_raw = safe_read_dataframe(file_obj)
    except Exception as e:
        st.error(f"Erreur : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df = fix_colonnes_doublons(df)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(3), use_container_width=True)
    with st.form(form_key):
        st.write(f"### 🎛️ Mapping — {label}")
        # ✅ Si targets_filtre fourni, on ne montre QUE ces champs
        if targets_filtre:
            targets = targets_filtre
            st.info(f"📋 Mapping limité aux {len(targets)} champs nécessaires pour {label}.")
        else:
            targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        mapping_final = {}
        for idx, db_f in enumerate(targets):
            auto_val = mapping_auto.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"{form_key}_{db_f}")
        sub = st.form_submit_button(f"🚀 Importer {label}", type="primary")
    if sub:
        if badge == 'gestionnaire_only':
            _import_gestionnaires(df, mapping_final, env)
        else:
            with get_session() as session:
                agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
                with st.status("Import en cours...", expanded=True) as status:
                    stats = moteur_import(df, mapping_final, env, badge, session, agents_db)
                status.update(label="✅ Terminé !", state="complete")
            st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
            if stats['erreurs']:
                with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                    for e in stats['erreurs'][:20]:
                        st.code(e)

def _maj_remboursement(df, mapping, env):
    """✅ MAJ ciblée : uniquement les champs de remboursement."""
    champs_remb = ['montant_rembourse','reste_rembourser','total_echue',
                   'nb_echeance_tombee','date_ech_tomb','prochaine_ech',
                   'etat_dette','anticip','ech_anticip','observations']
    with get_session() as session:
        # Cache identifiants Finance
        rows = session.query(Dossier.id, Dossier.identifiant, Dossier.nom, Dossier.prenom,
                             Dossier.date_naissance).filter(
            Dossier.type_dispositif == env).all()
        cache_ident = {(r[1] or '').strip().upper(): r[0] for r in rows if r[1]}
        cache_nom   = [(r[0], normaliser_nom(f"{r[2] or ''} {r[3] or ''}"),
                        (r[4] or '').strip()) for r in rows]

        c_maj = 0
        progress_bar = st.progress(0)
        total = len(df)
        for idx, row in df.iterrows():
            progress_bar.progress(min(1.0, (idx+1)/max(total,1)))
            # Identifier le dossier
            xl_id = mapping.get('identifiant','-- Ignorer --')
            ident = clean_identifiant(row.get(xl_id,'')) if xl_id != '-- Ignorer --' else ''
            dos_id = None
            if ident and ident.upper() in cache_ident:
                dos_id = cache_ident[ident.upper()]
            else:
                # Fallback nom+prenom
                xl_nom = mapping.get('nom','-- Ignorer --')
                xl_pre = mapping.get('prenom','-- Ignorer --')
                nom_imp = row.get(xl_nom,'') if xl_nom != '-- Ignorer --' else ''
                pre_imp = row.get(xl_pre,'') if xl_pre != '-- Ignorer --' else ''
                if nom_imp:
                    nom_norm = normaliser_nom(f"{nom_imp} {pre_imp}")
                    prefixe = nom_norm[:2] if len(nom_norm) >= 2 else nom_norm
                    for cand_id, cand_nom, cand_date in cache_nom:
                        if prefixe and not cand_nom.startswith(prefixe):
                            continue
                        if difflib.SequenceMatcher(None, nom_norm, cand_nom).ratio() >= 0.80:
                            dos_id = cand_id
                            break
            if not dos_id:
                continue
            dos = session.get(Dossier, dos_id)
            if not dos:
                continue
            # MAJ uniquement les champs remboursement
            for champ in champs_remb:
                xl_col = mapping.get(champ,'-- Ignorer --')
                if xl_col == '-- Ignorer --':
                    continue
                val = row.get(xl_col,'')
                if pd.isna(val) or str(val).strip() in ('','NAN','None','nan'):
                    continue
                if champ in COLONNES_ARGENT:
                    setattr(dos, champ, clean_money(val))
                else:
                    setattr(dos, champ, str(val).strip().upper())
            dos.in_recouvrement = 'OUI'
            c_maj += 1
            if (idx+1) % 100 == 0:
                session.commit()

    st.success(f"✅ {c_maj} dossiers mis à jour avec les données de remboursement.")

def _maj_gestionnaire(df, mapping, env):
    """✅ MAJ ciblée : UNIQUEMENT le champ gestionnaire, normalisé sur le nom officiel."""
    with get_session() as session:
        # Charger les agents officiels
        agents_officiels = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
        # Cache identifiants
        rows = session.query(Dossier.id, Dossier.identifiant, Dossier.nom,
                             Dossier.prenom).filter(Dossier.type_dispositif == env).all()
        cache_ident = {(r[1] or '').strip().upper(): r[0] for r in rows if r[1]}
        cache_nom   = [(r[0], normaliser_nom(f"{r[2] or ''} {r[3] or ''}")) for r in rows]

        c_maj = 0
        progress_bar = st.progress(0)
        total = len(df)
        for idx, row in df.iterrows():
            progress_bar.progress(min(1.0, (idx+1)/max(total,1)))
            xl_id   = mapping.get('identifiant','-- Ignorer --')
            xl_gest = mapping.get('gestionnaire','-- Ignorer --')
            if xl_gest == '-- Ignorer --':
                continue
            gest_brut = row.get(xl_gest,'')
            if pd.isna(gest_brut) or str(gest_brut).strip() in ('','NAN','None'):
                continue
            # ✅ Normaliser le nom du gestionnaire vers le nom officiel
            gest_officiel = trouver_agent_intelligent(str(gest_brut), agents_officiels)

            # Trouver le dossier
            ident = clean_identifiant(row.get(xl_id,'')) if xl_id != '-- Ignorer --' else ''
            dos_id = None
            if ident and ident.upper() in cache_ident:
                dos_id = cache_ident[ident.upper()]
            else:
                xl_nom = mapping.get('nom','-- Ignorer --')
                xl_pre = mapping.get('prenom','-- Ignorer --')
                nom_imp = row.get(xl_nom,'') if xl_nom != '-- Ignorer --' else ''
                pre_imp = row.get(xl_pre,'') if xl_pre != '-- Ignorer --' else ''
                if nom_imp:
                    nom_norm = normaliser_nom(f"{nom_imp} {pre_imp}")
                    prefixe = nom_norm[:2] if len(nom_norm) >= 2 else nom_norm
                    for cand_id, cand_nom in cache_nom:
                        if prefixe and not cand_nom.startswith(prefixe):
                            continue
                        if difflib.SequenceMatcher(None, nom_norm, cand_nom).ratio() >= 0.80:
                            dos_id = cand_id
                            break
            if not dos_id:
                continue
            dos = session.get(Dossier, dos_id)
            if not dos:
                continue
            # ✅ MAJ UNIQUEMENT le gestionnaire avec le nom officiel normalisé
            dos.gestionnaire = gest_officiel.strip().upper()
            c_maj += 1
            if (idx+1) % 100 == 0:
                session.commit()

    st.success(f"✅ {c_maj} dossiers affectés à leur accompagnateur (noms normalisés). Les dossiers apparaissent maintenant dans le bon profil.")

def _import_gestionnaires(df, mapping, env):
    with get_session() as session:
        agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
        c_affect = 0
        for _, row in df.iterrows():
            xl_id   = mapping.get('identifiant', '-- Ignorer --')
            xl_gest = mapping.get('gestionnaire', '-- Ignorer --')
            if xl_id == '-- Ignorer --' or xl_gest == '-- Ignorer --':
                continue
            ident = clean_identifiant(row.get(xl_id, ''))
            gest  = trouver_agent_intelligent(row.get(xl_gest, ''), agents_db)
            if not ident or not gest:
                continue
            dossiers = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).all()
            for d in dossiers:
                d.gestionnaire = gest
                c_affect += 1
    st.success(f"✅ {c_affect} fiches affectées.")

# ==========================================
# CORBEILLE
# ==========================================

def page_corbeille():
    env   = st.session_state.user['env']
    agent = st.session_state.user['nom']
    daira = st.session_state.user.get('daira', '').strip()
    st.title("🗑️ Corbeille — Dossiers non assignés")

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("La base est vide.")
        return

    def est_non_assigne(val):
        return str(val).strip().upper() in ('', 'NAN', 'NONE', 'NON', '-', 'N/A')

    df_non_assignes = df[df['gestionnaire'].apply(est_non_assigne)].copy()
    if df_non_assignes.empty:
        st.success("✅ Tous les dossiers sont assignés.")
        return

    if daira:
        # ✅ Détection intelligente : daïra → communes → adresse
        ma_daira = daira.strip()
        ma_daira_norm = unicodedata.normalize('NFKD', ma_daira.upper()).encode('ascii','ignore').decode('ascii')
        communes_ma_daira = communes_de_daira(ma_daira)
        communes_norm = [unicodedata.normalize('NFKD', c.upper()).encode('ascii','ignore').decode('ascii') for c in communes_ma_daira]
        def ma_zone(row):
            d = str(row.get('daira','')).strip().upper()
            c = str(row.get('commune','')).strip().upper()
            a = str(row.get('adresse','')).strip().upper()
            d_n = unicodedata.normalize('NFKD', d).encode('ascii','ignore').decode('ascii')
            c_n = unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii')
            a_n = unicodedata.normalize('NFKD', a).encode('ascii','ignore').decode('ascii')
            # 1. Daïra match
            if ma_daira_norm in d_n:
                return True
            # 2. Commune match
            for com_n in communes_norm:
                if com_n and com_n in c_n:
                    return True
            # 3. Adresse match
            for com_n in communes_norm:
                if com_n and com_n in a_n:
                    return True
            if ma_daira_norm in a_n:
                return True
            # 4. Aucune zone définie → visible pour tous
            if not d_n and not c_n and not a_n:
                return True
            return False
        orphans = df_non_assignes[df_non_assignes.apply(ma_zone, axis=1)].copy()
    else:
        st.warning("⚠️ Pas de Daïra assignée — vous voyez tous les dossiers non assignés.")
        orphans = df_non_assignes.copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total non assignés", len(df_non_assignes))
    c2.metric(f"Dans votre zone ({daira or 'toutes'})", len(orphans))
    nb_sans_zone = len(df_non_assignes[df_non_assignes.apply(
        lambda r: not str(r.get('daira','')).strip() and not str(r.get('commune','')).strip(), axis=1)])
    c3.metric("Sans zone définie", nb_sans_zone)

    if orphans.empty:
        st.success(f"✅ Aucun dossier orphelin dans votre secteur.")
        return

    rech = st.text_input("🔍 Filtrer...", placeholder="Nom, ID, commune...")
    if rech:
        orphans = orphans[orphans.apply(lambda x: x.astype(str).str.contains(rech, case=False).any(), axis=1)]

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    orphans_aff = orphans.copy()
    orphans_aff["✅ C'est le mien !"] = False
    cols_aff = [c for c in ["✅ C'est le mien !","identifiant","nom","prenom","activite","commune","daira","montant_pnr","id"]
                if c in orphans_aff.columns or c == "✅ C'est le mien !"]
    ed = st.data_editor(orphans_aff[cols_aff], hide_index=True, use_container_width=True, height=500,
        column_config={
            "id": None,
            "✅ C'est le mien !": st.column_config.CheckboxColumn("Prendre", default=False),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
        })
    ids_sel = ed[ed["✅ C'est le mien !"] == True]['id'].tolist()
    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        if ids_sel:
            st.info(f"**{len(ids_sel)} dossier(s) sélectionné(s)**")
        else:
            st.caption("Cochez les dossiers à prendre en charge.")
    with col_b2:
        if st.button(f"📥 M'attribuer {len(ids_sel)} dossier(s)", type="primary",
                     use_container_width=True, disabled=(len(ids_sel) == 0)):
            with get_session() as session:
                session.query(Dossier).filter(Dossier.id.in_(ids_sel)).update(
                    {"gestionnaire": agent.strip().upper(), "est_nouveau": "NON"},
                    synchronize_session=False)
            st.success(f"✅ {len(ids_sel)} dossier(s) attribués à {agent}.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE COMMUNICATION
# ==========================================

def page_communication():
    """Page réservée au Service Communication — recherche + fiche synthèse uniquement."""
    st.title("📢 Service Communication — Recherche Promoteurs")
    env = st.session_state.user['env']

    # Barre de recherche
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("**🔍 Rechercher un promoteur**")
    rech = st.text_input("Tapez un nom, prénom, identifiant, activité ou commune...",
                          placeholder="Ex: BENALI, 12345678, Hydra, commerce...")
    st.markdown("</div>", unsafe_allow_html=True)

    if not rech or len(rech.strip()) < 2:
        st.info("Tapez au moins 2 caractères pour lancer la recherche.")
        return

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env ORDER BY nom"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base est vide.")
        return

    # Filtrage
    df_res = df[df.apply(
        lambda x: x.astype(str).str.contains(rech.strip(), case=False, na=False).any(), axis=1
    )]

    st.caption(f"**{len(df_res)}** résultat(s) trouvé(s) pour **{rech}**")

    if df_res.empty:
        st.info("Aucun promoteur trouvé.")
        return

    # Affichage résultats (colonnes non sensibles uniquement)
    cols_com = [c for c in [
        "identifiant","nom","prenom","telephone","activite",
        "secteur","commune","daira","gestionnaire","statut_dossier","id"
    ] if c in df_res.columns]

    df_res.insert(0, "Fiche 📄", False)
    cols_com = ["Fiche 📄"] + cols_com

    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(
        df_res[cols_com],
        hide_index=True,
        use_container_width=True,
        height=400,
        column_config={
            "Fiche 📄": st.column_config.CheckboxColumn("Fiche", default=False),
            "id": None,
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ✅ 2 boutons : Fiche Arabe + Fiche Française
    sel = edited[edited["Fiche 📄"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        with get_session() as session:
            dos = session.get(Dossier, dos_id)
            if dos:
                st.success(f"Promoteur sélectionné : **{dos.nom} {dos.prenom}**")
                bc1, bc2 = st.columns(2)
                with bc1:
                    try:
                        pdf_ar = _generer_bطاقة_ar(dos)
                        st.download_button(
                            label="📄 بطاقة تقنية (عربي)",
                            data=pdf_ar,
                            file_name=f"Bطاقة_{dos.identifiant}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur PDF Arabe: {e}")
                with bc2:
                    try:
                        pdf_fr = _generer_fiche_fr(dos)
                        st.download_button(
                            label="📄 Fiche Technique (Français)",
                            data=pdf_fr,
                            file_name=f"Fiche_{dos.identifiant}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur PDF Français: {e}")

def _ar_text(text):
    """Prépare texte arabe pour reportlab."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        if not text or str(text).strip() in ('','nan','None'):
            return '---'
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

def _generer_bطاقة_ar(dos) -> bytes:
    """✅ Fiche technique en ARABE — reportlab + arabic_reshaper."""
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    import io as _io

    FONT   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        pdfmetrics.registerFont(TTFont('Ar2', FONT))
        pdfmetrics.registerFont(TTFont('ArB2', FONT_B))
    except Exception:
        pass

    buf = _io.BytesIO()
    W, H = A4
    ML, MR = 2*cm, 2*cm
    c = rl_canvas.Canvas(buf, pagesize=A4)
    NAVY = HexColor('#0f172a')
    GBG  = HexColor('#f1f5f9')
    BDR  = HexColor('#cbd5e1')
    BLUE = HexColor('#1d4ed8')

    def draw_section_ar(y, title):
        c.setFillColor(GBG)
        c.setStrokeColor(BDR)
        c.rect(ML, y-0.55*cm, W-ML-MR, 0.65*cm, fill=1, stroke=1)
        c.setFont('ArB2', 12)
        c.setFillColor(NAVY)
        c.drawCentredString(W/2, y-0.42*cm, _ar_text(title))
        return y - 0.72*cm

    def draw_field_ar(y, label, value):
        val = str(value) if value and str(value) not in ('nan','None','0','0.0','') else '...'
        c.setFont('ArB2', 10)
        c.setFillColor(NAVY)
        c.drawRightString(W-MR, y, _ar_text(f"{label} : {val}"))
        c.setStrokeColor(BDR)
        c.setLineWidth(0.3)
        c.line(ML, y-0.12*cm, W-MR, y-0.12*cm)
        return y - 0.62*cm

    y = H - 2*cm
    c.setFont('ArB2', 16); c.setFillColor(NAVY)
    c.drawCentredString(W/2, y, _ar_text("الوكالة الوطنية لتسيير القرض المصغر"))
    y -= 0.7*cm
    c.setFont('ArB2', 10); c.setFillColor(BLUE)
    c.drawCentredString(W/2, y, "AGENCE NATIONALE DE GESTION DU MICRO CREDIT")
    y -= 0.5*cm
    c.setStrokeColor(NAVY); c.setLineWidth(1)
    c.line(ML, y, W-MR, y)
    y -= 0.7*cm
    c.setFont('ArB2', 14); c.setFillColor(NAVY)
    c.drawCentredString(W/2, y, _ar_text("بطاقة تقنية"))
    y -= 0.6*cm
    c.setStrokeColor(BDR); c.setLineWidth(0.5)
    c.line(ML, y, W-MR, y)
    y -= 0.5*cm

    y = draw_section_ar(y, "هوية المقاول")
    c.setStrokeColor(NAVY); c.setLineWidth(0.8)
    c.rect(ML, y-3.5*cm, 2.5*cm, 3.5*cm, fill=0)
    c.setFont('Ar2', 7); c.setFillColor(HexColor('#94a3b8'))
    c.drawCentredString(ML+1.25*cm, y-1.9*cm, _ar_text("الصورة"))
    y = draw_field_ar(y, "الاسم", dos.nom)
    y = draw_field_ar(y, "اللقب", dos.prenom)
    y = draw_field_ar(y, "العمر", dos.age)
    y = draw_field_ar(y, "المستوى الدراسي", dos.niveau_instruction)
    y = draw_field_ar(y, "العنوان", f"{dos.adresse} — {dos.commune}")
    y = draw_field_ar(y, "الهاتف", dos.telephone)
    y -= 0.3*cm

    y = draw_section_ar(y, "تقديم المشروع")
    y = draw_field_ar(y, "طبيعة النشاط", dos.activite)
    y = draw_field_ar(y, "نوع النشاط", dos.secteur)
    y = draw_field_ar(y, "نوع التمويل", dos.type_dispositif)
    try: pnr_s = f"{float(dos.montant_pnr):,.0f} DA"
    except: pnr_s = str(dos.montant_pnr)
    y = draw_field_ar(y, "قيمة المشروع", pnr_s)
    y = draw_field_ar(y, "تاريخ بداية النشاط", dos.debut_consommation)
    y = draw_field_ar(y, "مكان النشاط", f"{dos.commune} — {dos.daira}")
    y -= 0.3*cm

    y = draw_section_ar(y, "المرافقة")
    y = draw_field_ar(y, "المرافق", dos.gestionnaire)
    y = draw_field_ar(y, "البنك", dos.banque_nom)
    y = draw_field_ar(y, "تاريخ التمويل", dos.date_financement)

    c.setFont('Ar2', 8); c.setFillColor(HexColor('#94a3b8'))
    c.drawCentredString(W/2, 1.2*cm, _ar_text(f"تم الإنشاء بتاريخ {datetime.now().strftime('%d/%m/%Y')}"))
    c.showPage(); c.save()
    return buf.getvalue()

def _generer_fiche_fr(dos) -> bytes:
    """✅ Fiche technique en FRANÇAIS — FPDF avec clean_pdf_text sur tout."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(29, 78, 216)
    pdf.rect(0, 0, 210, 38, 'F')
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "AGENCE NATIONALE DE GESTION DU MICRO CREDIT", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "ANGEM ALGER OUEST", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 9, "FICHE TECHNIQUE", ln=True, align='C')
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    def sec(title, color):
        pdf.set_fill_color(*color)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, clean_pdf_text(title), border=1, ln=True, fill=True)
        pdf.set_font("Arial", '', 9)

    def fld(label, value, w1=80, w2=110):
        val = clean_pdf_text(str(value)) if value and str(value) not in ('nan','None','0','0.0','') else '...'
        pdf.cell(w1, 6, f"  {clean_pdf_text(label)} :", border='LB')
        pdf.cell(w2, 6, f"  {val}", border='RB', ln=True)

    sec("IDENTITE DU PROMOTEUR", (219, 234, 254))
    fld("Nom", dos.nom); fld("Prenom", dos.prenom)
    fld("Age", dos.age); fld("Niveau d instruction", dos.niveau_instruction)
    fld("Adresse", f"{dos.adresse} — {dos.commune} ({dos.daira})", 55, 135)
    fld("Telephone", dos.telephone, 55, 135)
    pdf.ln(2)

    sec("PRESENTATION DU PROJET", (209, 250, 229))
    fld("Nature de l activite", dos.activite)
    fld("Type d activite", dos.secteur)
    fld("Type de financement", dos.type_dispositif)
    try: pnr_s = f"{float(dos.montant_pnr):,.0f} DA"
    except: pnr_s = str(dos.montant_pnr)
    fld("Valeur du projet", pnr_s)
    fld("Date debut d activite", dos.debut_consommation)
    fld("Lieu d activite", f"{dos.commune} — {dos.daira}", 55, 135)
    pdf.ln(2)

    sec("INFORMATIONS DE FINANCEMENT", (254, 243, 199))
    fld("Banque", dos.banque_nom)
    fld("N Ordre de Virement", dos.num_ordre_versement)
    fld("Date de Financement", dos.date_financement)
    fld("Agent accompagnateur", dos.gestionnaire, 65, 125)
    pdf.ln(5)

    pdf.set_font("Arial", 'I', 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4,
        clean_pdf_text(f"Document confidentiel — Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}"),
        align='C')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data


# ==========================================
# ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if "Administration" in page or "Import" in page:
        page_integration_admin()
    elif "Bilans" in page:
        page_bilans()
    elif "Corbeille" in page:
        page_corbeille()
    elif "Recherche Promoteurs" in page:
        page_communication()
    elif "Mes Dossiers" in page:
        page_gestion(mode="unifie", vue_admin=("admin" == st.session_state.user['role']))
