import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE ---
def get_gsheet_client():
    creds = {
        "type": st.secrets["type"], "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"], "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"], "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"], "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"]
    }
    return gspread.service_account_from_dict(creds)

def save_to_gsheet(data_dict):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        try:
            worksheet = sh.worksheet("SAISIE_BRUTE")
        except:
            worksheet = sh.add_worksheet(title="SAISIE_BRUTE", rows="2000", cols="100")
            worksheet.append_row(list(data_dict.keys()))
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur Sheets : {e}")
        return False

# --- GÉNÉRATEUR PDF (CORRIGÉ POUR STREAMLIT) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Regionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf_bytes(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activites mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.cell(190, 8, f"Accompagnateur : {data['Accompagnateur']}", 0, 1, 'L')
    pdf.ln(5)

    # Exemple de tableau simplifié pour le PDF
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(70, 8, "Rubrique", 1, 0, 'C', True)
    pdf.cell(30, 8, "Deposes", 1, 0, 'C', True)
    pdf.cell(30, 8, "Finances", 1, 0, 'C', True)
    pdf.cell(60, 8, "Remboursement (DA)", 1, 1, 'C', True)

    pdf.set_font('Arial', '', 9)
    # Ligne MP
    pdf.cell(70, 8, "Achat de Matiere Premiere", 1)
    pdf.cell(30, 8, str(data.get('MP_Deposes', 0)), 1, 0, 'C')
    pdf.cell(30, 8, str(data.get('MP_Finances', 0)), 1, 0, 'C')
    pdf.cell(60, 8, str(data.get('MP_Rembourse', 0)), 1, 1, 'C')

    # Ligne TRI
    pdf.cell(70, 8, "Formule Triangulaire", 1)
    pdf.cell(30, 8, str(data.get('TRI_Deposes', 0)), 1, 0, 'C')
    pdf.cell(30, 8, str(data.get('TRI_Finances', 0)), 1, 0, 'C')
    pdf.cell(60, 8, str(data.get('TRI_Rembourse', 0)), 1, 1, 'C')

    # --- RETOURNER EN BYTES (IMPORTANT) ---
    return pdf.output(dest='S').encode('latin-1')

# --- UTILISATEURS ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]
USERS_DB = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS): USERS_DB[nom] = str(1234 + (i * 11))

# --- AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO")
    u = st.selectbox("Nom", [""] + list(USERS_DB.keys()))
    p = st.text_input("Code", type="password")
    if st.button("Connexion"):
        if u in USERS_DB and USERS_DB[u] == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- FORMULAIRE ---
st.title(f"Saisie Officielle : {st.session_state.user}")
if 'v' not in st.session_state: st.session_state.v = set()

c1, c2 = st.columns(2)
mois = c1.selectbox("Mois", ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"])
annee = c2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

def render_fields(label, p):
    st.subheader(label)
    cols = st.columns(5)
    data[f"{p}_Deposes"] = cols[0].number_input("Deposes", key=f"{p}d", value=0)
    data[f"{p}_Traites"] = cols[1].number_input("Traites", key=f"{p}t", value=0)
    data[f"{p}_Valides"] = cols[2].number_input("Valides", key=f"{p}v", value=0)
    data[f"{p}_Transmis"] = cols[3].number_input("Transmis", key=f"{p}m", value=0)
    data[f"{p}_Finances"] = cols[4].number_input("Finances", key=f"{p}f", value=0)
    c2 = st.columns(2)
    data[f"{p}_Remb_Nb"] = c2[0].number_input("Nb Recus", key=f"{p}n", value=0)
    data[f"{p}_Rembourse"] = c2[1].number_input("Montant (DA)", key=f"{p}r", value=0.0)

t_names = ["1. MP", "2. TRI", "3. AUTRES"]
tabs = st.tabs(t_names)

with tabs[0]: st.session_state.v.add(t_names[0]); render_fields("Achat Matiere Premiere", "MP")
with tabs[1]: st.session_state.v.add(t_names[1]); render_fields("Formule Triangulaire", "TRI")
with tabs[2]: 
    st.session_state.v.add(t_names[2])
    data["CAM"] = st.number_input("Accueil CAM", 0)
    data["NESDA"] = st.number_input("NESDA", 0)

st.markdown("---")
if len(st.session_state.v) >= 3:
    if st.button("💾 ENREGISTRER ET GÉNÉRER PDF", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Enregistré !")
            # Génération en octets bruts pour corriger l'erreur
            pdf_bytes = generate_pdf_bytes(data)
            st.download_button("📥 TÉLÉCHARGER LE PDF", data=pdf_bytes, file_name=f"Bilan_{mois}.pdf", mime="application/pdf")
            st.balloons()
else:
    st.warning(f"Veuillez visiter tous les onglets ({len(st.session_state.v)}/3)")
