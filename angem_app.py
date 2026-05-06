import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base
import unicodedata
import re
import io
import json
import contextlib
from datetime import datetime
from fpdf import FPDF
import tempfile
import os
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURATION PAGE
# ==========================================
st.set_page_config(
    page_title="ANGEM Workspace",
    page_icon="🇩🇿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CREDENTIALS (via st.secrets en prod)
# ==========================================
# En production, utiliser st.secrets["supabase"]["url"] etc.
# Pour migration simple, on garde les valeurs ici mais on les isole
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
# 3. CONSTANTES MÉTIER
# ==========================================
LISTE_DAIRAS = ["", "Zéralda", "Chéraga", "Draria", "Bir Mourad Rais", "Bouzareah", "Birtouta"]
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

# Dictionnaire de mapping étendu et amélioré
MAPPING_CONFIG_KEYWORDS = {
    'identifiant':         ['IDENTIFIANT','CNI','NCINPC','NAT','NATIONALITE','ID','NIN','NUMERONATIONAL'],
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
    'num_ordre_versement': ['NUMOV','ORDREVERSEMENT','OV','NUMERORDREVIREMENT','NUMORDREVIREMENT'],
    'date_financement':    ['DATEOV','DATEVIREMENT','DATEFINAN','DATEVERSEMENT','DATEOCTROI'],
    'debut_consommation':  ['DEBUTCONSOM','CONSOMMATION','DEBUT'],
    'montant_pnr':         ['PNR','MONTANTPNR','MONTANTACCORDE','MONTANTCREDIT','CREDIT','MONTANT'],
    'apport_personnel':    ['APPORT','APPORTPERSO','APPORTPERSONNEL'],
    'credit_bancaire':     ['CREDITBANC','CREDITBANCAIRE','BANQUE','MONTANTBANQUE'],
    'montant_total_credit':['MONTANTTOTAL','TOTAL','COUTPROJET'],
    'nb_echeance_tombee':  ['ECHTOMB','ECHEANCES','NBRECHTOMB','NBRECHEANCESTOMBEES'],
    'date_ech_tomb':       ['DATEECHTOMB','DATEECHEANCETOMBEE','DATEECH','DERNIEREECHEANCE'],
    'prochaine_ech':       ['PROCHAINEECH','PROCHECH','PROCHAINEECHEANCE'],
    'total_echue':         ['TOTALECHUE','MONTECHEAN','MONTANTECHU','ECHUETOTAL'],
    'montant_rembourse':   ['TOTALREMB','VERSEMENT','REMBOURSE','TOTALVERS','MONTANTREMBOURSE','MONTANTVERSE'],
    'reste_rembourser':    ['RESTAREMB','MONTANTRESTA','RESTE','SOLDE','ENCOURS'],
    'etat_dette':          ['ETATDETTE','ETAT','SITUATION','STATUT'],
    'observations':        ['OBS','OBSERVATION','OBSERVATIONS','REMARQUE','REMARQUES','NOTE'],
    'anticip':             ['ANTICIP','ANTICIPATION','ANTICIPATIF'],
    'ech_anticip':         ['ECHANTICIP','ECHEANCEANTICIP'],
}

# ==========================================
# 4. BASE DE DONNÉES — MODÈLES & SESSION
# ==========================================
Base = declarative_base()
engine = create_engine(DB_URL, echo=False, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

@contextlib.contextmanager
def get_session():
    """Context manager sécurisé — ferme toujours la session."""
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
    id                  = Column(Integer, primary_key=True)
    identifiant         = Column(String, index=True)
    type_dispositif     = Column(String, default="PNR PROJET")
    nom                 = Column(String, default="")
    prenom              = Column(String, default="")
    genre               = Column(String, default="")
    date_naissance      = Column(String, default="")
    adresse             = Column(String, default="")
    telephone           = Column(String, default="")
    niveau_instruction  = Column(String, default="")
    age                 = Column(String, default="")
    activite            = Column(String, default="")
    code_activite       = Column(String, default="")
    secteur             = Column(String, default="")
    daira               = Column(String, default="")
    commune             = Column(String, default="")
    wilaya              = Column(String, default="")
    zone                = Column(String, default="")
    gestionnaire        = Column(String, default="")
    montant_pnr         = Column(Float, default=0.0)
    apport_personnel    = Column(Float, default=0.0)
    credit_bancaire     = Column(Float, default=0.0)
    montant_total_credit= Column(Float, default=0.0)
    banque_nom          = Column(String, default="")
    agence_bancaire     = Column(String, default="")
    numero_compte       = Column(String, default="")
    num_ordre_versement = Column(String, default="")
    date_financement    = Column(String, default="")
    debut_consommation  = Column(String, default="")
    montant_rembourse   = Column(Float, default=0.0)
    reste_rembourser    = Column(Float, default=0.0)
    nb_echeance_tombee  = Column(String, default="")
    date_ech_tomb       = Column(String, default="")
    prochaine_ech       = Column(String, default="")
    total_echue         = Column(Float, default=0.0)
    etat_dette          = Column(String, default="")
    anticip             = Column(String, default="")
    ech_anticip         = Column(String, default="")
    observations        = Column(String, default="")
    statut_dossier      = Column(String, default="Phase dépôt du dossier")
    documents           = Column(String, default="")
    historique_visites  = Column(String, default="")
    prochaine_visite    = Column(String, default="")
    est_nouveau         = Column(String, default="NON")
    in_finance          = Column(String, default="NON")
    in_recouvrement     = Column(String, default="NON")
    # ✅ NOUVEAU : stocke toutes les colonnes Excel non mappées
    champs_dynamiques   = Column(Text, default="{}")

class UtilisateurAuth(Base):
    __tablename__ = 'utilisateurs_auth'
    id          = Column(Integer, primary_key=True)
    identifiant = Column(String, unique=True)
    nom         = Column(String)
    mot_de_passe= Column(String)
    role        = Column(String)
    daira       = Column(String, default="")

Base.metadata.create_all(engine)

# Migration automatique des colonnes manquantes
_MIGRATIONS = {
    'champs_dynamiques': "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS champs_dynamiques TEXT DEFAULT '{}'",
    'wilaya':            "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS wilaya VARCHAR DEFAULT ''",
    'agence_bancaire':   "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS agence_bancaire VARCHAR DEFAULT ''",
    'numero_compte':     "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS numero_compte VARCHAR DEFAULT ''",
    'montant_total_credit': "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS montant_total_credit FLOAT DEFAULT 0.0",
    'zone':              "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS zone VARCHAR DEFAULT ''",
    'secteur':           "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS secteur VARCHAR DEFAULT ''",
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
        for ident, nom, role in [("admin","Administrateur","admin"), ("finance","Service Finance","finance")]:
            u = session.query(UtilisateurAuth).filter_by(identifiant=ident).first()
            if not u:
                session.add(UtilisateurAuth(identifiant=ident, nom=nom, mot_de_passe="angem", role=role))

init_db_users()

# ==========================================
# 5. SESSION STATE
# ==========================================
for key, val in {
    'user': None,
    'portal_selection': None,
    'search_query': "",
    'import_quick_open': False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 6. THÈME DYNAMIQUE
# ==========================================
if st.session_state.user and st.session_state.user.get('env') == "PNR PROJET":
    theme_color, theme_bg = "#1f77b4", "#f4f9fc"
elif st.session_state.user:
    theme_color, theme_bg = "#28a745", "#f4fcf5"
else:
    theme_color, theme_bg = "#2c3e50", "#f8f9fa"

st.markdown(f"""
<style>
    .stApp {{ background-color: {theme_bg}; font-family: 'Segoe UI', sans-serif; }}
    .modern-card {{
        background:#fff; padding:25px; border-radius:16px;
        box-shadow:0 8px 24px rgba(0,0,0,0.04); margin:15px 0 25px;
        border:1px solid #edf2f7; border-top:4px solid {theme_color};
    }}
    .metric-card {{
        background:#fff; border-radius:16px; padding:20px;
        box-shadow:0 4px 15px rgba(0,0,0,0.03); border-left:6px solid {theme_color};
        display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;
    }}
    .metric-value {{ font-size:26px; font-weight:800; color:#1e293b; margin-top:5px; }}
    .metric-label {{ font-size:13px; color:#64748b; text-transform:uppercase; font-weight:700; }}
    .metric-danger {{ border-left-color:#ef4444; }}
    .profil-header {{
        background:linear-gradient(135deg,#fff 0%,#f8fafc 100%);
        padding:25px; border-radius:12px; border-left:8px solid {theme_color};
        margin-bottom:15px; box-shadow:0 4px 15px rgba(0,0,0,0.05);
    }}
    .block-finance {{ background:#eff6ff; border-left:5px solid #3b82f6; padding:15px; border-radius:8px; margin-bottom:15px; }}
    .block-recouvrement {{ background:#f0fdf4; border-left:5px solid #22c55e; padding:15px; border-radius:8px; margin-bottom:15px; }}
    .block-dynamique {{ background:#fefce8; border-left:5px solid #eab308; padding:15px; border-radius:8px; margin-bottom:15px; }}
    .block-title {{ font-weight:bold; color:#1e293b; margin-bottom:10px; font-size:16px; text-transform:uppercase; }}
    .btn-action {{
        flex:1; min-width:160px; padding:12px 20px; border-radius:10px;
        font-weight:bold; text-align:center; color:white !important;
        transition:all 0.3s; box-shadow:0 4px 6px rgba(0,0,0,0.1);
        display:inline-flex; align-items:center; justify-content:center; gap:8px;
        font-size:15px; text-decoration:none; margin:4px;
    }}
    .btn-call {{ background:#3b82f6; }} .btn-wa {{ background:#22c55e; }} .btn-maps {{ background:#ef4444; }}
    .badge-nouveau {{
        background:#dc2626; color:white; border-radius:20px;
        padding:2px 10px; font-size:11px; font-weight:700;
        display:inline-block; animation:pulse 1.5s infinite;
    }}
    @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.6; }} }}
    .alerte-nouveau {{
        background:#f0fdf4; border-left:6px solid #22c55e;
        padding:15px 20px; border-radius:8px; color:#15803d;
        font-weight:600; margin-bottom:20px;
    }}
    .import-rapide-box {{
        background:linear-gradient(135deg,#1e3a5f,#2563eb);
        padding:20px; border-radius:14px; color:white; margin-bottom:20px;
    }}
    .champ-dyn-item {{
        display:flex; justify-content:space-between;
        padding:6px 0; border-bottom:1px solid #f1f5f9;
        font-size:13px;
    }}
    .champ-dyn-key {{ color:#64748b; font-weight:600; }}
    .champ-dyn-val {{ color:#1e293b; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 7. UTILITAIRES AMÉLIORÉS
# ==========================================

def clean_header(v):
    """Nettoie un nom de colonne pour la comparaison."""
    return ''.join(filter(str.isalnum, unicodedata.normalize('NFKD', str(v)).encode('ascii','ignore').decode('ascii').upper()))

def clean_identifiant(v):
    """
    ✅ FIX NOTATION SCIENTIFIQUE : 1.23456789E+10 → '12345678900'
    Gère aussi les .0 trailing et les espaces.
    """
    if pd.isna(v) or str(v).strip() in ['', 'NAN', 'None', 'nan']:
        return ""
    s = str(v).strip()
    # Notation scientifique
    if re.match(r'^[\d\.\+\-eE]+$', s) and ('e' in s.lower() or 'E' in s):
        try:
            return f"{float(s):.0f}"
        except Exception:
            pass
    # Trailing .0
    if s.endswith('.0'):
        s = s[:-2]
    return s.strip().upper()

def clean_money(v):
    """
    ✅ NETTOYAGE MONTANTS ROBUSTE
    Gère : '1 234 567 DA', '1.234.567,00', '1,234,567.00', espaces insécables, etc.
    """
    if pd.isna(v) or str(v).strip() in ['', 'NAN', 'None', 'nan', '-', 'N/A']:
        return 0.0
    s = str(v).strip()
    # Supprimer unités et caractères non numériques sauf virgule et point
    s = re.sub(r'[Dd][Aa]|DZD|DA', '', s)
    s = s.replace('\xa0', '').replace(' ', '').replace('\u202f', '')
    # Format français : 1.234.567,89 → virgule = décimale
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
    """Nettoie pour FPDF (ASCII safe)."""
    if not t:
        return ""
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii')

def is_ligne_parasite(row: pd.Series, colonnes_mappees: list) -> bool:
    """
    ✅ FILTRE ANTI-LIGNES PARASITES
    Retourne True si la ligne est vide, un sous-total, un en-tête répété, etc.
    """
    vals = [str(v).strip() for v in row.values]
    vals_non_vides = [v for v in vals if v not in ('', 'NAN', 'None', 'nan', '-')]
    if len(vals_non_vides) == 0:
        return True
    premiere_val = vals_non_vides[0].upper() if vals_non_vides else ""
    mots_parasites = ['TOTAL', 'SOUS-TOTAL', 'SOUS TOTAL', 'CUMUL', 'GRAND TOTAL',
                      'IDENTIFIANT', 'CNI', 'N°', 'NOM ET PRENOM', 'PROMOTEUR', 'SUITE']
    if any(mot in premiere_val for mot in mots_parasites):
        return True
    return False

def get_header_row(df_raw: pd.DataFrame) -> int:
    """
    ✅ DÉTECTION EN-TÊTE AMÉLIORÉE
    Cherche jusqu'à 50 lignes, score par mots-clés, retourne la meilleure ligne.
    """
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

def safe_read_dataframe(file_obj) -> pd.DataFrame:
    """Lecture Excel/CSV avec fallback encodages."""
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
        for engine_type in ['openpyxl', 'xlrd']:
            try:
                file_obj.seek(0)
                return pd.read_excel(file_obj, header=None, dtype=str, engine=engine_type)
            except Exception:
                pass
    raise ValueError("Impossible de lire le fichier.")

def auto_mapper(df_cols: list) -> dict:
    """
    ✅ MAPPING AUTOMATIQUE AMÉLIORÉ
    Retourne un dict {champ_db: colonne_excel} pour les colonnes détectées.
    """
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

def extraire_champs_dynamiques(row: pd.Series, colonnes_mappees: list, all_cols: list) -> dict:
    """
    ✅ COLONNES DYNAMIQUES
    Retourne un dict de toutes les colonnes non mappées avec leur valeur.
    """
    champs = {}
    for col in all_cols:
        if col not in colonnes_mappees:
            val = row.get(col, '')
            val_str = str(val).strip()
            if val_str not in ('', 'NAN', 'None', 'nan', '-'):
                champs[col] = val_str
    return champs

def trouver_agent_par_zone(daira: str, commune: str, session) -> str:
    """
    ✅ AFFECTATION PAR ZONE (fallback si pas d'agent dans Excel)
    Cherche un agent dont la daïra correspond.
    """
    if not daira and not commune:
        return ""
    agents = session.query(UtilisateurAuth).filter_by(role='agent').all()
    zone_recherche = (daira + " " + commune).upper()
    for agent in agents:
        if agent.daira and agent.daira.upper() in zone_recherche:
            return agent.nom
    return ""

def trouver_agent_intelligent(nom_excel: str, agents_db: list) -> str:
    """Matching flou sur le nom de l'agent."""
    if not nom_excel or str(nom_excel).strip().upper() in ['', 'NAN', 'NONE']:
        return ""
    nom_ex = str(nom_excel).strip().upper()
    # Match exact
    for agent in agents_db:
        if agent.upper() == nom_ex:
            return agent
    # Match partiel
    for agent in agents_db:
        if agent.upper() in nom_ex or nom_ex in agent.upper():
            return agent
    # Match par token (prénom + nom séparés)
    tokens_ex = set(re.split(r'\s+', nom_ex))
    for agent in agents_db:
        tokens_ag = set(re.split(r'\s+', agent.upper()))
        if len(tokens_ex & tokens_ag) >= 1:
            return agent
    return nom_ex  # On garde la valeur brute si aucun match

def verifier_doublon(session, identifiant: str, env: str, badge: str) -> object:
    """
    ✅ DÉTECTION DOUBLONS AMÉLIORÉE
    Cherche par identifiant + environnement + badge.
    """
    if not identifiant:
        return None
    return session.query(Dossier).filter(
        Dossier.identifiant == identifiant,
        Dossier.type_dispositif == env,
        **({badge: 'OUI'} if badge == 'in_finance' else {})
    ).filter(
        getattr(Dossier, badge) == 'OUI'
    ).first()

# ==========================================
# 8. MOTEUR D'IMPORT UNIVERSEL
# ==========================================

def moteur_import(
    df: pd.DataFrame,
    mapping: dict,
    env: str,
    badge: str,          # 'in_finance' ou 'in_recouvrement'
    session,
    agents_db: list,
    affectation_auto: bool = False
) -> dict:
    """
    ✅ MOTEUR D'IMPORT CENTRALISÉ
    Retourne un dict de stats : {'crees', 'mis_a_jour', 'ignores', 'non_assignes', 'erreurs'}
    """
    stats = {'crees': 0, 'mis_a_jour': 0, 'ignores': 0, 'non_assignes': 0, 'erreurs': []}
    colonnes_mappees = [v for v in mapping.values() if v != "-- Ignorer --"]
    total = len(df)

    progress_bar = st.progress(0)

    for idx, row in df.iterrows():
        try:
            progress_bar.progress(min(1.0, (idx + 1) / max(total, 1)))

            # 1. Filtre lignes parasites
            if is_ligne_parasite(row, colonnes_mappees):
                stats['ignores'] += 1
                continue

            # 2. Extraire les données mappées
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

            # 3. Identifiant obligatoire
            ident = data.get('identifiant', '')
            if not ident:
                stats['ignores'] += 1
                continue

            # 4. Champs dynamiques (colonnes non mappées)
            champs_dyn = extraire_champs_dynamiques(row, colonnes_mappees, list(df.columns))

            # 5. Affectation automatique si pas d'agent trouvé
            if affectation_auto and not data.get('gestionnaire'):
                daira   = data.get('daira', '')
                commune = data.get('commune', '')
                agent_zone = trouver_agent_par_zone(daira, commune, session)
                if agent_zone:
                    data['gestionnaire'] = agent_zone
                else:
                    stats['non_assignes'] += 1
                    # On importe quand même → corbeille

            # 6. Vérifier doublon
            exist = verifier_doublon(session, ident, env, badge)

            if exist:
                # Mise à jour
                for k, v in data.items():
                    if v is not None and v != '':
                        setattr(exist, k, v)
                # Merge champs dynamiques
                try:
                    cd_exist = json.loads(exist.champs_dynamiques or '{}')
                except Exception:
                    cd_exist = {}
                cd_exist.update(champs_dyn)
                exist.champs_dynamiques = json.dumps(cd_exist, ensure_ascii=False)
                stats['mis_a_jour'] += 1
            else:
                # Création
                # Filtre montant minimum pour Finance
                if badge == 'in_finance':
                    pnr = data.get('montant_pnr', 0.0) or 0.0
                    if float(pnr) <= 40000:
                        stats['ignores'] += 1
                        continue

                data['type_dispositif']  = env
                data['est_nouveau']      = 'OUI'
                data[badge]              = 'OUI'
                # Badge opposé à NON par défaut
                autre_badge = 'in_recouvrement' if badge == 'in_finance' else 'in_finance'
                data[autre_badge]        = 'NON'
                data['champs_dynamiques'] = json.dumps(champs_dyn, ensure_ascii=False)
                session.add(Dossier(**data))
                stats['crees'] += 1

        except Exception as e:
            stats['erreurs'].append(f"Ligne {idx}: {str(e)}")

    return stats

# ==========================================
# 9. GÉNÉRATION PDF AMÉLIORÉE
# ==========================================

def generer_fiche_promoteur_pdf(dos) -> bytes:
    """PDF fiche promoteur avec champs dynamiques."""
    pdf = FPDF()
    pdf.add_page()
    # En-tête
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 12, "FICHE OFFICIELLE PROMOTEUR - ANGEM", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 6, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", ln=True, align='C')
    pdf.ln(3)
    # Section Identification
    _pdf_section(pdf, "1. IDENTIFICATION")
    _pdf_ligne2(pdf, f"ID: {clean_pdf_text(dos.identifiant)}", f"Agent: {clean_pdf_text(dos.gestionnaire)}")
    _pdf_ligne2(pdf, f"Nom: {clean_pdf_text(dos.nom)} {clean_pdf_text(dos.prenom)}", f"Tel: {clean_pdf_text(dos.telephone)}")
    _pdf_ligne1(pdf, f"Adresse: {clean_pdf_text(dos.adresse)} - {clean_pdf_text(dos.commune)} - {clean_pdf_text(dos.daira)}")
    pdf.ln(2)
    # Section Financement
    _pdf_section(pdf, "2. FINANCEMENT")
    _pdf_ligne2(pdf, f"Dispositif: {clean_pdf_text(dos.type_dispositif)}", f"Banque: {clean_pdf_text(dos.banque_nom)}")
    _pdf_ligne2(pdf, f"Activite: {clean_pdf_text(dos.activite)}", f"Num OV: {clean_pdf_text(dos.num_ordre_versement)}")
    _pdf_ligne2(pdf, f"Credit PNR: {dos.montant_pnr:,.0f} DA", f"Date financement: {clean_pdf_text(dos.date_financement)}")
    pdf.ln(2)
    # Section Recouvrement
    _pdf_section(pdf, "3. RECOUVREMENT")
    _pdf_ligne2(pdf, f"Rembourse: {dos.montant_rembourse:,.0f} DA", f"Reste: {dos.reste_rembourser:,.0f} DA")
    _pdf_ligne2(pdf, f"Echue: {dos.total_echue:,.0f} DA", f"Etat: {clean_pdf_text(dos.etat_dette)}")
    _pdf_ligne1(pdf, f"Ech. Tombees: {clean_pdf_text(dos.nb_echeance_tombee)} | Prochaine: {clean_pdf_text(dos.prochaine_ech)}")
    pdf.ln(2)
    # Champs dynamiques
    try:
        cd = json.loads(dos.champs_dynamiques or '{}')
    except Exception:
        cd = {}
    if cd:
        _pdf_section(pdf, "4. INFORMATIONS COMPLEMENTAIRES")
        for k, v in cd.items():
            _pdf_ligne1(pdf, f"{clean_pdf_text(k)}: {clean_pdf_text(v)}")
    # Observations
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

def generer_rapport_global_pdf(df) -> bytes:
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
# 10. PORTAIL CONNEXION
# ==========================================

def login_page():
    st.markdown("<br><h2 style='text-align:center; color:#1e293b; font-weight:800;'>Portail de Connexion ANGEM</h2>", unsafe_allow_html=True)
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
                    st.session_state.user = {
                        "nom": user_data[0], "role": user_data[2],
                        "daira": user_data[3], "env": env
                    }
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 11. SIDEBAR
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

    # Badge notifications Finance
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
                st.sidebar.markdown(f"<div style='text-align:center; margin-bottom:10px;'><span class='badge-nouveau'>🔴 {nvx} nouveau(x) dossier(s)</span></div>", unsafe_allow_html=True)
        except Exception:
            pass

    if role == "finance":
        opts = ["💰 Rubrique Financement", "📥 Import Financement"]
    elif role == "admin":
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement", "📊 Supervision", "⚙️ Administration"]
    else:
        opts = ["🗂️ Rubrique Financement", "📈 Rubrique Recouvrement", "🗑️ Corbeille"]

    choice = st.sidebar.radio("Navigation", opts, label_visibility="collapsed")
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.user = None
        st.session_state.portal_selection = None
        st.rerun()
    return choice

# ==========================================
# 12. AFFICHAGE PROFIL PROMOTEUR
# ==========================================

def afficher_profil_complet(dos_id: int):
    with get_session() as session:
        dos = session.get(Dossier, dos_id)
        if not dos:
            st.error("Dossier introuvable.")
            return

        # Marquer comme lu
        if dos.est_nouveau == 'OUI' and dos.gestionnaire == st.session_state.user['nom'].upper():
            dos.est_nouveau = 'NON'

        taux = (dos.montant_rembourse / dos.montant_pnr) if dos.montant_pnr and dos.montant_pnr > 0 else 0

        st.markdown(f"""
        <div class='profil-header'>
            <div>
                <h2 style='margin:0;'>{dos.nom} {dos.prenom}</h2>
                <p style='margin:0; color:#64748b;'>ID: {dos.identifiant} | {dos.activite}</p>
                <p style='margin:4px 0 0;'>📍 {dos.commune} — {dos.daira}</p>
            </div>
            <div style='text-align:right;'>
                <div style='font-size:11px; color:#64748b;'>Statut</div>
                <div style='font-weight:700; color:{theme_color};'>{dos.statut_dossier}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Boutons actions rapides
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

        # Blocs info
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

        # ✅ CHAMPS DYNAMIQUES
        try:
            champs_dyn = json.loads(dos.champs_dynamiques or '{}')
        except Exception:
            champs_dyn = {}

        if champs_dyn:
            with st.expander(f"📋 Informations complémentaires Excel ({len(champs_dyn)} champs)", expanded=False):
                st.markdown("<div class='block-dynamique'><div class='block-title'>📊 Données brutes du fichier</div>", unsafe_allow_html=True)
                # Affichage en grille
                items = list(champs_dyn.items())
                for i in range(0, len(items), 2):
                    cols = st.columns(2)
                    for j, (k, v) in enumerate(items[i:i+2]):
                        with cols[j]:
                            new_val = st.text_input(k, value=v, key=f"dyn_{dos_id}_{k}")
                            if new_val != v:
                                champs_dyn[k] = new_val

                if st.button("💾 Sauvegarder champs dynamiques", key=f"save_dyn_{dos_id}"):
                    dos.champs_dynamiques = json.dumps(champs_dyn, ensure_ascii=False)
                    st.success("Champs mis à jour !")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Historique + Documents
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
            st.download_button("📄 Télécharger Fiche PDF", data=pdf_data,
                               file_name=f"ANGEM_{dos.identifiant}.pdf", mime="application/pdf",
                               use_container_width=True)
            with st.expander("📸 Joindre un document"):
                cam     = st.camera_input("Caméra", key=f"c_{dos_id}")
                file_up = st.file_uploader("Fichier image", key=f"f_{dos_id}")
                if st.button("☁️ Archiver", key=f"u_{dos_id}"):
                    data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                    if data:
                        try:
                            fname = f"{dos.identifiant}_{int(datetime.now().timestamp())}.jpg"
                            supabase_client.storage.from_("scans_angem").upload(
                                file=data, path=fname, file_options={"content-type": "image/jpeg"})
                            dos.documents = (dos.documents or "") + fname + "|"
                            st.success("Document archivé !")
                        except Exception as e:
                            st.error(f"Erreur Cloud: {e}")
            if dos.documents:
                for d in [x for x in dos.documents.split('|') if x]:
                    url = supabase_client.storage.from_('scans_angem').get_public_url(d)
                    st.markdown(f"📥 <a href='{url}' target='_blank'>Voir document</a>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 13. VUE GESTION (TABLEAU PRINCIPAL)
# ==========================================

def page_gestion(mode="financement", vue_admin=False):
    env       = st.session_state.user['env']
    role      = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    badge     = "in_finance" if mode == "financement" else "in_recouvrement"

    # ✅ BOUTON IMPORT RAPIDE (Finance uniquement)
    if mode == "financement" and role in ("finance", "admin"):
        st.markdown("<div class='import-rapide-box'>", unsafe_allow_html=True)
        col_imp1, col_imp2 = st.columns([3, 1])
        with col_imp1:
            st.markdown("**📥 Import rapide — Nouveaux dossiers financés**")
            st.caption("Importe et affecte automatiquement les dossiers aux accompagnateurs.")
        with col_imp2:
            if st.button("📂 Importer un fichier", key="btn_import_rapide", use_container_width=True):
                st.session_state.import_quick_open = not st.session_state.import_quick_open
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.import_quick_open:
            with st.expander("🚀 Interface d'import rapide", expanded=True):
                _widget_import_rapide(env)

    # Récupérer les dossiers
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(f"SELECT * FROM dossiers WHERE type_dispositif=:env AND {badge}='OUI' ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    # Badge nouveaux dossiers
    if role == 'agent':
        nvx = len(df[(df['gestionnaire'].str.upper() == nom_agent) & (df['est_nouveau'] == 'OUI')])
        if nvx > 0:
            st.markdown(f"<div class='alerte-nouveau'>🎉 {nvx} nouveau(x) dossier(s) vous ont été affectés !</div>", unsafe_allow_html=True)

    # Barre de recherche
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

    # Filtre agent — matching robuste par tokens
    if not vue_admin and role == "agent":
        def filtre_agent_robuste(nom_db):
            """
            Compare les tokens du nom DB vs nom de connexion.
            Ex: 'MME BENALI FATIMA' matche avec 'Fatima Benali'
            car les tokens {BENALI, FATIMA} ont une intersection.
            Un seul token commun suffit (le nom de famille).
            """
            prefixes = r'(MME|MR|M\.|MLLE|MELLE|MR\.|DR|PR)\.?\s*'
            def tokeniser(s):
                s = re.sub(prefixes, '', str(s).strip().upper())
                s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
                tokens = set(re.split(r'[\s\-_\./]+', s))
                tokens -= {'', 'NAN', 'NONE', 'NON', '-', 'N/A'}
                tokens = {t for t in tokens if len(t) > 1}
                return tokens

            tokens_db    = tokeniser(nom_db)
            tokens_agent = tokeniser(nom_agent)
            if not tokens_db or not tokens_agent:
                return False
            intersection = tokens_db & tokens_agent
            return len(intersection) >= min(2, len(tokens_agent))

        df_filtre = df[df['gestionnaire'].apply(filtre_agent_robuste)]

        # Diagnostic si 0 résultats
        if df_filtre.empty and not df.empty:
            with st.expander("⚠️ Aucun dossier trouvé à votre nom — Diagnostic", expanded=True):
                st.warning(f"Votre nom de connexion : **{nom_agent}**")
                st.info("Noms de gestionnaires dans la base :")
                noms = [n for n in df['gestionnaire'].dropna().unique().tolist()
                        if str(n).strip() not in ('', 'NAN')]
                st.write(noms[:30] if noms else "Aucun gestionnaire assigné.")
                st.caption("👉 Demandez à l'admin de corriger l'orthographe de votre nom dans l'Excel importé.")
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

    # Configuration colonnes
    if mode == "financement":
        cols = ["Ouvrir 📂","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=True),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
        }
    else:
        cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","montant_pnr","montant_rembourse","reste_rembourser","etat_dette","gestionnaire","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "montant_pnr": st.column_config.NumberColumn("Montant Crédit", format="%d DA", disabled=True),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA", disabled=True),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA", disabled=True),
            "gestionnaire": st.column_config.TextColumn("Agent", disabled=True),
        }

    # Filtrer colonnes existantes
    cols = [c for c in cols if c in df.columns or c == "Ouvrir 📂"]

    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(df[cols], use_container_width=True, hide_index=True,
                            column_config=config, height=500)

    if mode == "financement" and st.button("💾 Sauvegarder", type="primary"):
        with get_session() as session:
            for _, r in edited.iterrows():
                dos = session.get(Dossier, int(r['id']))
                if dos:
                    dos.statut_dossier = r['statut_dossier']
                    if role != 'agent':
                        dos.gestionnaire = str(r['gestionnaire']).strip().upper()
        st.toast("✅ Modifications enregistrées !")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Ouvrir profil
    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        afficher_profil_complet(dos_id)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 14. WIDGET IMPORT RAPIDE
# ==========================================

def _widget_import_rapide(env: str):
    """Bouton d'import rapide dans la vue Finance avec affectation auto."""
    st.info("💡 Ce module importe les nouveaux dossiers financés et les affecte automatiquement aux accompagnateurs.")
    f = st.file_uploader("📁 Fichier Excel / CSV des nouveaux financés", type=['xlsx','xls','csv'], key="f_rapide")
    if not f:
        return

    try:
        df_raw = safe_read_dataframe(f)
    except Exception as e:
        st.error(f"Impossible de lire le fichier : {e}")
        return

    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)

    # Mapping automatique
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)

    st.success(f"✅ {len(mapping_auto)} colonnes détectées automatiquement sur {len(df.columns)} total.")
    st.markdown(f"**Aperçu ({len(df)} lignes) :**")
    st.dataframe(df.head(5), use_container_width=True)

    # Afficher et ajuster le mapping
    # Mapping final : auto par défaut, ajustable via expander
    mapping_final = {k: (v if v in excel_cols else "-- Ignorer --")
                     for k, v in mapping_auto.items()}

    with st.expander("🎛️ Vérifier / Ajuster le mapping (optionnel)"):
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        for idx, db_f in enumerate(targets):
            auto_val = mapping_final.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(
                    f"`{db_f}`", excel_cols, index=auto_idx, key=f"mr_{db_f}")

    if st.button("🚀 Lancer l'import avec affectation automatique", type="primary", key="btn_go_rapide"):
        with get_session() as session:
            agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
            with st.status("Import en cours...", expanded=True) as status:
                stats = moteur_import(
                    df, mapping_final, env,
                    badge='in_finance',
                    session=session,
                    agents_db=agents_db,
                    affectation_auto=True
                )
            status.update(label="✅ Import terminé !", state="complete")

        st.success(f"**{stats['crees']}** dossiers créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
        if stats['non_assignes'] > 0:
            st.warning(f"⚠️ **{stats['non_assignes']}** dossiers sans agent trouvé → placés en corbeille (non assignés).")
        if stats['erreurs']:
            with st.expander(f"🔴 {len(stats['erreurs'])} erreurs détectées"):
                for err in stats['erreurs'][:20]:
                    st.code(err)
        st.session_state.import_quick_open = False
        st.rerun()

# ==========================================
# 15. PAGE ADMINISTRATION
# ==========================================

def page_integration_admin():
    env  = st.session_state.user['env']
    role = st.session_state.user['role']
    st.title("⚙️ Administration — Import & Gestion")

    if role == "finance":
        tabs = st.tabs(["💰 Import Finance"])
        t1, t2, t3, t4, t5 = tabs[0], None, None, None, None
    else:
        t1, t2, t3, t4, t5 = st.tabs(["💰 Import Finance", "📈 Import Recouvrement", "👥 Gestionnaires", "🧹 Maintenance", "🔐 Équipes"])

    # --- ONGLET 1 : FINANCE ---
    with t1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("💡 **Finance :** Crée ou met à jour les fiches de la rubrique Finance.")
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx','xls','csv'], key="ff")
        if f_fin:
            _onglet_import_generique(f_fin, env, 'in_finance', "form_fin", "Finance")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 2 : RECOUVREMENT ---
    if t2:
        with t2:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.warning("🛡️ **Recouvrement :** Fiches séparées pour la vue Recouvrement.")
            f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx','xls','csv'], key="fr")
            if f_rec:
                _onglet_import_generique(f_rec, env, 'in_recouvrement', "form_rec", "Recouvrement")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 3 : GESTIONNAIRES ---
    if t3:
        with t3:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.warning("👥 Assigne le gestionnaire sur TOUTES les fiches portant le même ID.")
            f_gest = st.file_uploader("Fichier Gestionnaires", type=['xlsx','xls','csv'], key="fgest")
            if f_gest:
                _onglet_import_generique(f_gest, env, 'gestionnaire_only', "form_gest", "Gestionnaires")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- ONGLET 4 : MAINTENANCE ---
    if t4:
        with t4:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
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

    # --- ONGLET 5 : ÉQUIPES ---
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
                    column_config={"id": None, "identifiant": st.column_config.TextColumn(disabled=True),
                                   "nom": st.column_config.TextColumn(disabled=True),
                                   "daira": st.column_config.SelectboxColumn(options=LISTE_DAIRAS)})
                if st.button("💾 Sauvegarder", type="primary"):
                    with get_session() as session:
                        for _, r in ed_u.iterrows():
                            u = session.get(UtilisateurAuth, int(r['id']))
                            if u:
                                u.mot_de_passe = r['mot_de_passe']
                                u.daira = r['daira']
                    st.success("Équipe mise à jour.")

            with st.form("ajout_agent"):
                c1, c2, c3 = st.columns([1,1.5,1])
                n_id  = c1.text_input("Identifiant")
                n_nom = c2.text_input("Nom complet")
                n_dai = c3.selectbox("Daïra", LISTE_DAIRAS)
                if st.form_submit_button("Créer le compte") and n_id and n_nom:
                    with get_session() as session:
                        if not session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first():
                            session.add(UtilisateurAuth(identifiant=n_id.lower(), nom=n_nom.strip().upper(),
                                                        daira=n_dai, mot_de_passe="angem2026", role="agent"))
                        st.success(f"Compte {n_nom} créé !")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def _onglet_import_generique(file_obj, env, badge, form_key, label):
    """Widget d'import générique avec mapping automatique + manuel."""
    try:
        df_raw = safe_read_dataframe(file_obj)
    except Exception as e:
        st.error(f"Impossible de lire le fichier : {e}")
        return

    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)

    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)

    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(3), use_container_width=True)

    with st.form(form_key):
        st.write(f"### 🎛️ Mapping — {label}")
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
                    stats = moteur_import(df, mapping_final, env, badge, session, agents_db, affectation_auto=False)
                status.update(label="✅ Terminé !", state="complete")
            st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
            if stats['erreurs']:
                with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                    for e in stats['erreurs'][:20]:
                        st.code(e)

def _import_gestionnaires(df, mapping, env):
    """Import spécialisé pour mise à jour des gestionnaires."""
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
    st.success(f"✅ {c_affect} fiches affectées à un gestionnaire.")

# ==========================================
# 16. SUPERVISION
# ==========================================

def page_supervision():
    st.title("📊 Supervision Globale")
    env = st.session_state.user['env']
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(text("SELECT * FROM dossiers WHERE type_dispositif=:env"), conn, params={"env": env}).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base de données est vide.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div><div class='metric-label'>Total Fiches</div><div class='metric-value'>{len(df)}</div></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div><div class='metric-label'>PNR Engagé</div><div class='metric-value'>{df['montant_pnr'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div><div class='metric-label'>Total Recouvré</div><div class='metric-value'>{df['montant_rembourse'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card metric-danger'><div><div class='metric-label' style='color:#ef4444;'>Reste à Recouvrer</div><div class='metric-value' style='color:#dc2626;'>{df['reste_rembourser'].astype(float).sum():,.0f} DA</div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📥 Extractions")
    cb1, cb2, cb3 = st.columns(3)
    with cb1:
        st.download_button("📊 Bilan PDF", data=generer_rapport_global_pdf(df),
                           file_name="Bilan_ANGEM.pdf", mime="application/pdf", use_container_width=True)
    with cb2:
        buf = io.BytesIO()
        # Export avec champs dynamiques dépliés
        df_export = df.copy()
        try:
            dyn_expanded = df_export['champs_dynamiques'].apply(
                lambda x: json.loads(x) if x and x != '{}' else {})
            dyn_df = pd.json_normalize(dyn_expanded)
            df_export = pd.concat([df_export.drop(columns=['champs_dynamiques']), dyn_df], axis=1)
        except Exception:
            pass
        df_export.to_excel(buf, index=False)
        st.download_button("🟢 Export Excel complet", data=buf.getvalue(),
                           file_name="Backup_ANGEM.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 17. CORBEILLE
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

    # Dossiers non assignés : gestionnaire vide/NAN/tiret
    def est_non_assigne(val):
        return str(val).strip().upper() in ('', 'NAN', 'NONE', 'NON', '-', 'N/A')

    df_non_assignes = df[df['gestionnaire'].apply(est_non_assigne)].copy()

    if df_non_assignes.empty:
        st.success("✅ Tous les dossiers sont assignés. Aucune corbeille.")
        return

    # Filtre zone : dossier de la même daïra OU sans zone définie
    if daira:
        def dossier_de_ma_zone(row):
            daira_dos   = str(row.get('daira',   '')).strip().upper()
            commune_dos = str(row.get('commune', '')).strip().upper()
            ma_daira    = daira.strip().upper()
            if ma_daira in daira_dos or ma_daira in commune_dos:
                return True
            # Dossier sans zone → visible pour tous
            if not daira_dos and not commune_dos:
                return True
            return False
        orphans = df_non_assignes[df_non_assignes.apply(dossier_de_ma_zone, axis=1)].copy()
    else:
        # Pas de daïra → l'agent voit tout
        st.warning("⚠️ Vous n'avez pas de Daïra assignée. Vous voyez tous les dossiers non assignés.")
        orphans = df_non_assignes.copy()

    nb_sans_zone = len(df_non_assignes[
        df_non_assignes.apply(
            lambda r: not str(r.get('daira','')).strip() and not str(r.get('commune','')).strip(), axis=1)
    ])

    # Métriques
    c1, c2, c3 = st.columns(3)
    c1.metric("Total non assignés (base)", len(df_non_assignes))
    c2.metric(f"Dans votre zone ({daira or 'toutes'})", len(orphans))
    c3.metric("Sans zone définie", nb_sans_zone)

    if orphans.empty:
        st.success(f"✅ Aucun dossier orphelin dans votre secteur ({daira}).")
        return

    # Recherche dans la corbeille
    rech = st.text_input("🔍 Filtrer...", placeholder="Nom, ID, commune...")
    if rech:
        orphans = orphans[orphans.apply(
            lambda x: x.astype(str).str.contains(rech, case=False).any(), axis=1)]

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    orphans_aff = orphans.copy()
    orphans_aff["✅ C'est le mien !"] = False
    cols_aff = [c for c in ["✅ C'est le mien !", "identifiant", "nom", "prenom",
                             "activite", "commune", "daira", "montant_pnr", "id"]
                if c in orphans_aff.columns or c == "✅ C'est le mien !"]

    ed = st.data_editor(
        orphans_aff[cols_aff], hide_index=True, use_container_width=True, height=500,
        column_config={
            "id": None,
            "✅ C'est le mien !": st.column_config.CheckboxColumn("Prendre", default=False),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
        }
    )
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
            st.success(f"✅ {len(ids_sel)} dossier(s) attribué(s) à {agent}.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 18. ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if "Administration" in page or "Import" in page:
        page_integration_admin()
    elif "Supervision" in page:
        page_supervision()
    elif "Corbeille" in page:
        page_corbeille()
    elif "Financement" in page:
        page_gestion(mode="financement", vue_admin=("admin" == st.session_state.user['role']))
    else:
        page_gestion(mode="recouvrement", vue_admin=("admin" == st.session_state.user['role']))
