import streamlit as st
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Rapport Officiel", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE ---
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
            worksheet = sh.add_worksheet(title="SAISIE_BRUTE", rows="2000", cols="150")
            worksheet.append_row(list(data_dict.keys()))
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur Sheets : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (STRUCTURE DÉTAILLÉE FIDÈLE AU MODÈLE) ---
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

    def draw_pdf_table(title, prefix, headers):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 7)
        w = 190 / len(headers)
        for h in headers: pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for h in headers:
            key = f"{prefix}_{h}"
            val = data.get(key, 0)
            pdf.cell(w, 7, str(val), 1, 0, 'C')
        pdf.ln(8)

    # Reconstruction des tableaux
    h_std = ["Deposes", "Traites", "Valides", "Transmis", "Finances", "Recus_Remb", "Mnt_Remb"]
    h_ext = ["Deposes", "Valides", "Transmis_Bq", "Finances", "BC_10", "BC_90", "PV_Exis", "PV_Dem", "Mnt_Remb"]
    
    draw_pdf_table("1. Formule : Achat de matiere premieres", "MP", h_std)
    draw_pdf_table("2. Formule : Triangulaire", "TRI", h_ext)
    draw_pdf_table("5. Dossiers (Algerie telecom)", "AT", h_ext)
    draw_pdf_table("6. Dossiers (Recyclage)", "REC", h_ext)
    draw_pdf_table("7. Dossiers (Tricycle)", "TC", h_ext)
    draw_pdf_table("8. Dossiers (Auto Entrepreneur)", "AE", h_ext)

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur : {data['Accompagnateur']}", 0, 1, 'R')
    
    # SOLUTION RADICALE : Utilisation de BytesIO pour le téléchargement
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès")
    u = st.selectbox("Nom", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DÉTAILLÉ (84 CASES) ---
st.title(f"Bilan de {st.session_state.user}")
if 'v' not in st.session_state: st.session_state.v = set()

c1, c2 = st.columns(2)
mois = c1.selectbox("Mois", ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"])
annee = c2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

# STRUCTURE DÉPLIÉE (ONGLETS)
tabs = st.tabs(["1. MP", "2. TRI", "3. AT", "4. REC", "5. TC", "6. AE", "7. CAM/NESDA"])

with tabs[0]:
    st.session_state.v.add("1")
    st.subheader("1. Achat de matière première")
    c = st.columns(5)
    data["MP_Deposes"] = c[0].number_input("Déposés (MP)", key="mp1", value=0)
    data["MP_Traites"] = c[1].number_input("Traités CEF (MP)", key="mp2", value=0)
    data["MP_Valides"] = c[2].number_input("Validés CEF (MP)", key="mp3", value=0)
    data["MP_Transmis"] = c[3].number_input("Transmis AR (MP)", key="mp4", value=0)
    data["MP_Finances"] = c[4].number_input("Financés (MP)", key="mp5", value=0)
    cr = st.columns(2)
    data["MP_Recus_Remb"] = cr[0].number_input("Nombre Reçus (MP)", key="mp6", value=0)
    data["MP_Mnt_Remb"] = cr[1].number_input("Montant (DA)", key="mp7", value=0.0)

with tabs[1]:
    st.session_state.v.add("2")
    st.subheader("2. Formule Triangulaire")
    c = st.columns(4)
    data["TRI_Deposes"] = c[0].number_input("Déposés (TRI)", key="tr1", value=0)
    data["TRI_Valides"] = c[1].number_input("Validés (TRI)", key="tr2", value=0)
    data["TRI_Transmis_Bq"] = c[2].number_input("Transmis Banque (TRI)", key="tr3", value=0)
    data["TRI_Finances"] = c[3].number_input("Financés (TRI)", key="tr4", value=0)
    c2 = st.columns(4)
    data["TRI_BC_10"] = c2[0].number_input("BC 10% (TRI)", key="tr5", value=0)
    data["TRI_BC_90"] = c2[1].number_input("BC 90% (TRI)", key="tr6", value=0)
    data["TRI_PV_Exis"] = c2[2].number_input("PV Existence (TRI)", key="tr7", value=0)
    data["TRI_PV_Dem"] = c2[3].number_input("PV Démarrage (TRI)", key="tr8", value=0)

with tabs[2]:
    st.session_state.v.add("3")
    st.subheader("5. Algérie Télécom")
    c = st.columns(4)
    data["AT_Deposes"] = c[0].number_input("Déposés (AT)", key="at1", value=0)
    data["AT_Valides"] = c[1].number_input("Validés (AT)", key="at2", value=0)
    data["AT_Transmis_Bq"] = c[2].number_input("Transmis Banque (AT)", key="at3", value=0)
    data["AT_Finances"] = c[3].number_input("Financés (AT)", key="at4", value=0)

with tabs[6]:
    st.session_state.v.add("7")
    data["CAM"] = st.number_input("Citoyens reçus (CAM)", key="cam1", value=0)
    data["NESDA"] = st.number_input("Dossiers NESDA", key="nes1", value=0)
    data["ST_Total"] = st.number_input("Sorties terrain", key="st1", value=0)

st.markdown("---")

# --- 6. BOUTON FINAL ---
if len(st.session_state.v) >= 7:
    if st.button("💾 ENREGISTRER & GÉNÉRER PDF", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Données enregistrées !")
            # Génération sous forme de flux d'octets
            pdf_data = generate_pdf_bytes(data)
            st.download_button(
                label="📥 TÉLÉCHARGER LE PDF OFFICIEL", 
                data=pdf_data, 
                file_name=f"Bilan_{st.session_state.user}.pdf", 
                mime="application/pdf"
            )
            st.balloons()
else:
    st.warning(f"Consultez les 7 onglets avant d'enregistrer ({len(st.session_state.v)}/7)")
