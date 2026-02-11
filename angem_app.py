import streamlit as st
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

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
            worksheet = sh.add_worksheet(title="SAISIE_BRUTE", rows="2000", cols="150")
            worksheet.append_row(list(data_dict.keys()))
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (MODÈLE EXACT DE L'IMAGE) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf_bytes(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.ln(5)

    def draw_table(title, prefix, headers):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 6)
        w = 190 / len(headers)
        for h in headers: pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for h in headers:
            key = f"{prefix}_{h}"
            pdf.cell(w, 7, str(data.get(key, 0)), 1, 0, 'C')
        pdf.ln(8)

    # Reconstruction des tableaux PDF
    h_mp = ["Déposés", "Traités_CEF", "Validés_CEF", "Transmis_AR", "Financés", "Reçus_Remb", "Montant_Remb"]
    draw_table("1. Formule : Achat de matière premières", "MP", h_mp)

    h_ext = ["Déposés", "Validés_CEF", "Transmis_Banque", "Financés", "BC_10%", "BC_90%", "PV_Existence", "PV_Démarrage", "Montant_Remb"]
    draw_table("2. Formule : Triangulaire", "TRI", h_ext)
    draw_table("5. Dossiers (Algérie télécom)", "AT", h_ext)
    draw_table("6. Dossiers (Recyclage)", "REC", h_ext)
    draw_table("7. Dossiers (Tricycle)", "TC", h_ext)
    draw_table("8. Dossiers (Auto Entrepreneur)", "AE", h_ext)

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur (trice) : {data['Accompagnateur']}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès")
    u = st.selectbox("Sélectionnez votre nom", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DÉPLIÉ (84 CASES) ---
st.title(f"Bilan mensuel : {st.session_state.user}")
if 'v' not in st.session_state: st.session_state.v = set()

c1, c2 = st.columns(2)
mois = c1.selectbox("Mois du rapport", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee = c2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Algérie Télécom", "4. Recyclage", "5. Tricycle", "6. Auto-Entrepreneur", "7. CAM / NESDA / Rappels"])

# --- SECTION 1 : MATIERE PREMIERE ---
with tabs[0]:
    st.session_state.v.add("1")
    st.subheader("1. Achat de matière première")
    colA, colB, colC, colD, colE = st.columns(5)
    data["MP_Déposés"] = colA.number_input("Dossiers déposés (MP)", key="mp_d", value=0)
    data["MP_Traités_CEF"] = colB.number_input("Traités CEF (MP)", key="mp_t", value=0)
    data["MP_Validés_CEF"] = colC.number_input("Validés CEF (MP)", key="mp_v", value=0)
    data["MP_Transmis_AR"] = colD.number_input("Transmis AR (MP)", key="mp_ar", value=0)
    data["MP_Financés"] = colE.number_input("Dossiers financés (MP)", key="mp_f", value=0)
    colF, colG = st.columns(2)
    data["MP_Reçus_Remb"] = colF.number_input("Nbrs. reçus remboursés (MP)", key="mp_rn", value=0)
    data["MP_Montant_Remb"] = colG.number_input("Montant remboursé (MP)", key="mp_rm", value=0.0)

# --- FONCTION POUR LES SECTIONS COMPLEXES (TRI, AT, REC, TC, AE) ---
def render_full_section(label, p, tab_index):
    st.session_state.v.add(str(tab_index))
    st.subheader(label)
    cA, cB, cC, cD = st.columns(4)
    data[f"{p}_Déposés"] = cA.number_input(f"Dossiers déposés ({p})", key=f"{p}_d", value=0)
    data[f"{p}_Validés_CEF"] = cB.number_input(f"Validés CEF ({p})", key=f"{p}_v", value=0)
    data[f"{p}_Transmis_Banque"] = cC.number_input(f"Transmis Banque ({p})", key=f"{p}_tb", value=0)
    data[f"{p}_Financés"] = cD.number_input(f"Dossiers financés ({p})", key=f"{p}_f", value=0)
    
    cE, cF, cG, cH = st.columns(4)
    data[f"{p}_BC_10%"] = cE.number_input(f"BC 10% ({p})", key=f"{p}_bc1", value=0)
    data[f"{p}_BC_90%"] = cF.number_input(f"BC 90% ({p})", key=f"{p}_bc9", value=0)
    data[f"{p}_PV_Existence"] = cG.number_input(f"PV Existence ({p})", key=f"{p}_pve", value=0)
    data[f"{p}_PV_Démarrage"] = cH.number_input(f"PV Démarrage ({p})", key=f"{p}_pvd", value=0)
    
    data[f"{p}_Montant_Remb"] = st.number_input(f"Montant remboursé ({p})", key=f"{p}_rm", value=0.0)

with tabs[1]: render_full_section("2. Formule Triangulaire", "TRI", 2)
with tabs[2]: render_full_section("5. Algérie Télécom", "AT", 3)
with tabs[3]: render_full_section("6. Recyclage", "REC", 4)
with tabs[4]: render_full_section("7. Tricycle", "TC", 5)
with tabs[5]: render_full_section("8. Auto-Entrepreneur", "AE", 6)

with tabs[6]:
    st.session_state.v.add("7")
    st.subheader("Accueil & Rappels")
    data["CAM_Citoyens_Reçus"] = st.number_input("Citoyens reçus (CAM)", value=0)
    data["NESDA_Dossiers"] = st.number_input("Dossiers NESDA", value=0)
    data["ST_Sorties_Terrain"] = st.number_input("Sorties sur terrain", value=0)

st.markdown("---")
# --- 6. BOUTON FINAL ---
if len(st.session_state.v) >= 7:
    if st.button("💾 ENREGISTRER & GÉNÉRER PDF", type="primary", use_container_width=True):
        if save_to_gsheet(data):
            st.success("✅ Données enregistrées !")
            pdf_data = generate_pdf_bytes(data)
            st.download_button("📥 TÉLÉCHARGER LE PDF OFFICIEL", data=pdf_data, file_name=f"Bilan_{mois}.pdf", mime="application/pdf")
            st.balloons()
else:
    st.warning(f"Veuillez parcourir les 7 onglets avant d'enregistrer ({len(st.session_state.v)}/7)")
