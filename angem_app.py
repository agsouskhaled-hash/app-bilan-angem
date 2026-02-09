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

# --- GÉNÉRATEUR PDF (MODÈLE FIDÈLE) ---
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
    pdf.ln(5)

    def draw_section(title, prefix, headers):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 7)
        w = 190 / len(headers)
        for h in headers: pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        for h in headers:
            val = data.get(f"{prefix}_{h.replace(' ', '_')}", 0)
            pdf.cell(w, 7, str(val), 1, 0, 'C')
        pdf.ln(10)

    # Sections du document
    draw_section("1. Formule : Achat de matiere premieres", "MP", ["Deposes", "Traites_CEF", "Valides_CEF", "Transmis_AR", "Finances", "Remb_Nb", "Remb_Mnt"])
    draw_section("2. Formule : Triangulaire", "TRI", ["Deposes", "Valides_CEF", "Transmis_Bq", "Finances", "BC_10", "BC_90", "PV_Exist", "PV_Dem", "Remb_Mnt"])

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur (trice) : {data['Accompagnateur']}", 0, 1, 'R')
    
    # --- CORRECTION DE L'ERREUR ATTRIBUTEERROR ---
    return pdf.output() # Dans FPDF2 moderne, output() sans argument renvoie des bytes par défaut

# --- UTILISATEURS & AUTH ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]
USERS_DB = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS): USERS_DB[nom] = str(1234 + (i * 11))

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès")
    u = st.selectbox("Nom", [""] + list(USERS_DB.keys()))
    p = st.text_input("Code", type="password")
    if st.button("Connexion"):
        if u in USERS_DB and USERS_DB[u] == p:
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- FORMULAIRE 84 RUBRIQUES ---
st.title(f"Saisie Officielle - {st.session_state.user}")
if 'v' not in st.session_state: st.session_state.v = set()

c1, c2 = st.columns(2)
mois = c1.selectbox("Mois", ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"])
annee = c2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

def render_full_box(label, p):
    st.subheader(label)
    cols = st.columns(5)
    data[f"{p}_Deposes"] = cols[0].number_input("Deposes", key=f"{p}1", value=0)
    data[f"{p}_Traites_CEF"] = cols[1].number_input("Traites CEF", key=f"{p}2", value=0)
    data[f"{p}_Valides_CEF"] = cols[2].number_input("Valides CEF", key=f"{p}3", value=0)
    data[f"{p}_Transmis_AR"] = cols[3].number_input("Transmis AR/Bq", key=f"{p}4", value=0)
    data[f"{p}_Finances"] = cols[4].number_input("Finances", key=f"{p}5", value=0)
    c2 = st.columns(4)
    data[f"{p}_BC
