import streamlit as st
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Rapport Officiel", layout="wide")

# --- CONNEXION SÉCURISÉE ---
def get_gsheet_client():
    creds = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
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
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- GÉNÉRATEUR PDF (STRUCTURE DU MODÈLE IMAGE) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(5)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)
        
    def section_title(self, label):
        self.set_fill_color(255, 230, 204) # Couleur orange clair/beige du modèle
        self.set_font('Arial', 'BI', 11)
        self.cell(190, 8, label, 1, 1, 'L', True)

def generate_angem_pdf(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    
    # Titre Principal
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 10, f"Mois : {data['Mois'].upper()}", 0, 1, 'R')
    
    # 1. Matière Première
    pdf.section_title("1. Formule : Achat de matière premières")
    pdf.set_font('Arial', '', 8)
    # Entêtes
    cols = ["Nbrs. Dossiers déposés", "Nbrs. Dossiers traités CEF", "Nbrs. Dossiers validés CEF", "Nbrs. Transmis AR", "Nbrs. Financés"]
    for col in cols: pdf.cell(38, 7, col, 1, 0, 'C')
    pdf.ln()
    # Valeurs
    pdf.cell(38, 7, str(data['MP_Dep']), 1, 0, 'C')
    pdf.cell(38, 7, str(data['MP_Trt']), 1, 0, 'C')
    pdf.cell(38, 7, str(data['MP_Val']), 1, 0, 'C')
    pdf.cell(38, 7, str(data['MP_Tms']), 1, 0, 'C')
    pdf.cell(38, 7, str(data['MP_Fin']), 1, 1, 'C')
    
    # 2. Triangulaire
    pdf.ln(5)
    pdf.section_title("2. Formule : Triangulaire")
    # ... (Structure similaire pour les autres rubriques)
    
    pdf.ln(20)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur (trice) : {data['Nom']}", 0, 1, 'R')
    
    return pdf.output()

# --- INTERFACE UTILISATEUR ---
LISTE_NOMS = [
    "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH",
    "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA",
    "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA",
    "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL",
    "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA",
    "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA",
    "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA",
    "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH",
    "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"
]

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🇩🇿 Portail Saisie Bilan ANGEM")
    u = st.selectbox("Utilisateur", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code d'accès", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- FORMULAIRE ---
st.title(f"Saisie du Rapport : {st.session_state.user}")
mois = st.selectbox("Mois du bilan", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee = st.number_input("Année", 2026)

data = {"Nom": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

tab1, tab2, tab3 = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Autres"])

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    data["MP_Dep"] = c1.number_input("Dossiers déposés", 0, key="mp1")
    data["MP_Trt"] = c2.number_input("Traités CEF", 0, key="mp2")
    data["MP_Val"] = c3.number_input("Validés CEF", 0, key="mp3")
    data["MP_Tms"] = c4.number_input("Transmis AR", 0, key="mp4")
    data["MP_Fin"] = c5.number_input("Financés", 0, key="mp5")

# ... (Complétez les autres rubriques ici)

st.markdown("---")
if st.button("💾 ENREGISTRER ET GÉNÉRER LE PDF OFFICIEL", type="primary", use_container_width=True):
    if save_to_gsheet(data):
        st.success("✅ Données sauvegardées dans Excel !")
        pdf_bytes = generate_angem_pdf(data)
        st.download_button("📥 TÉLÉCHARGER LE BILAN PDF", data=pdf_bytes, file_name=f"Bilan_{st.session_state.user}_{mois}.pdf", mime="application/pdf")
        st.balloons()
