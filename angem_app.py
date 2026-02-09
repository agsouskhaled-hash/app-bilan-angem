import streamlit as st
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE ---
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
            # Création de l'onglet si inexistant avec assez de colonnes pour les 84 cases
            worksheet = sh.add_worksheet(title="SAISIE_BRUTE", rows="2000", cols="150")
            worksheet.append_row(list(data_dict.keys()))
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde Sheets : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (LE MODÈLE EXACT DE VOTRE IMAGE) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(5)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf_bytes(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 10, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.ln(5)

    def draw_pdf_table(title, prefix, headers):
        pdf.set_fill_color(255, 230, 204) # Couleur Beige du modèle
        pdf.set_font('Arial', 'BI', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 7)
        w = 190 / len(headers)
        for h in headers:
            pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for h in headers:
            key = f"{prefix}_{h}"
            val = data.get(key, 0)
            pdf.cell(w, 7, str(val), 1, 0, 'C')
        pdf.ln(8)

    # Reconstruction des tableaux PDF selon votre modèle
    h_std = ["Déposés", "Traités_CEF", "Validés_CEF", "Transmis_AR", "Financés", "Recus_Remb", "Montant_Remb"]
    draw_pdf_table("1. Formule : Achat de matière premières", "MP", h_std)
    
    h_tri = ["Déposés", "Traités_CEF", "Validés_CEF", "Transmis_Bq", "Notif_Bq", "Financés", "BC_10", "BC_90", "PV_Exist", "PV_Dem", "Recus_Remb", "Montant_Remb"]
    draw_pdf_table("2. Formule : Triangulaire", "TRI", h_tri)
    
    draw_pdf_table("5. Dossiers (Algérie télécom)", "AT", h_tri)
    draw_pdf_table("6. Dossiers (Recyclage)", "REC", h_tri)
    draw_pdf_table("7. Dossiers (Tricycle)", "TC", h_tri)
    draw_pdf_table("8. Dossiers (Auto Entrepreneur)", "AE", h_tri)

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur (trice) : {data['Accompagnateur']}", 0, 1, 'R')
    
    return pdf.output()

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès")
    u = st.selectbox("Sélectionnez votre nom", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if p == "1234": # Remplacez par votre logique de code si besoin
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE (LES 84 CASES) ---
st.title(f"Bilan de {st.session_state.user}")
if 'v' not in st.session_state:
    st.session_state.v = set()

c1, c2 = st.columns(2)
mois = c1.selectbox("Mois du bilan", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee = c2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

# Fonction de création automatique des rubriques pour garantir les 84 cases
def create_rubrique(label, p, extension=False):
    st.subheader(label)
    cols = st.columns(5)
    data[f"{p}_Déposés"] = cols[0].number_input("Déposés", key=f"{p}d", value=0)
    data[f"{p}_Traités_CEF"] = cols[1].number_input("Traités CEF", key=f"{p}t", value=0)
    data[f"{p}_Validés_CEF"] = cols[2].number_input("Validés CEF", key=f"{p}v", value=0)
    
    if not extension:
        data[f"{p}_Transmis_AR"] = cols[3].number_input("Transmis AR", key=f"{p}ar", value=0)
    else:
        data[f"{p}_Transmis_Bq"] = cols[3].number_input("Transmis Banque", key=f"{p}bq", value=0)
        data[f"{p}_Notif_Bq"] = cols[4].number_input("Notif. Banque", key=f"{p}nb", value=0)
    
    data[f"{p}_Financés"] = st.columns(5)[4].number_input("Financés", key=f"{p}f", value=0)

    if extension:
        c_ext = st.columns(4)
        data[f"{p}_BC_10"] = c_ext[0].number_input("BC 10%", key=f"{p}bc1", value=0)
        data[f"{p}_BC_90"] = c_ext[1].number_input("BC 90%", key=f"{p}bc9", value=0)
        data[f"{p}_PV_Exist"] = c_ext[2].number_input("PV Exist", key=f"{p}pve", value=0)
        data[f"{p}_PV_Dem"] = c_ext[3].number_input("PV Dém", key=f"{p}pvd", value=0)

    c_rem = st.columns(2)
    data[f"{p}_Recus_Remb"] = c_rem[0].number_input("Nb Reçus Remb.", key=f"{p}rn", value=0)
    data[f"{p}_Montant_Remb"] = c_rem[1].number_input("Montant (DA)", key=f"{p}rm", value=0.0)

# Organisation par onglets pour la clarté
tabs = st.tabs(["Matière Première", "Triangulaire", "Spécifiques (AT/REC)", "Tricycle / AE", "NESDA / Rappels"])

with tabs[0]: st.session_state.v.add("1"); create_rubrique("Achat Matière Première", "MP")
with tabs[1]: st.session_state.v.add("2"); create_rubrique("Formule Triangulaire", "TRI", True)
with tabs[2]:
    st.session_state.v.add("3")
    create_rubrique("Dossiers Algérie Télécom", "AT", True)
    create_rubrique("Dossiers Recyclage", "REC", True)
with tabs[3]:
    st.session_state.v.add("4")
    create_rubrique("Dossiers Tricycle", "TC", True)
    create_rubrique("Dossiers Auto-Entrepreneur", "AE", True)
with tabs[4]:
    st.session_state.v.add("5")
    data["CAM_Recus"] = st.number_input("Citoyens reçus (CAM)", 0)
    data["NESDA_Total"] = st.number_input("Total NESDA", 0)
    data["Sorties_Terrain"] = st.number_input("Sorties terrain", 0)

st.markdown("---")

# --- 6. BOUTON FINAL ---
if len(st.session_state.v) >= 5:
    if st.button("💾 ENREGISTRER & GÉNÉRER PDF", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Données enregistrées avec succès !")
            pdf_bytes = generate_pdf_bytes(data)
            st.download_button("📥 TÉLÉCHARGER LE PDF OFFICIEL", data=pdf_bytes, file_name=f"Bilan_{mois}.pdf", mime="application/pdf")
            st.balloons()
else:
    st.warning(f"Veuillez parcourir les 5 onglets avant d'enregistrer ({len(st.session_state.v)}/5)")
