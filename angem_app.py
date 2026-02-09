import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Intégral", layout="wide", page_icon="🇩🇿")

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

# --- GÉNÉRATEUR PDF (MODÈLE ANGEM) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Regionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(8)
    def section_title(self, label):
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 10)
        self.cell(190, 7, label, 1, 1, 'L', True)

def generate_pdf(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activites mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.cell(190, 8, f"Accompagnateur : {data['Accompagnateur']}", 0, 1, 'L')
    pdf.ln(5)

    def quick_table(title, prefix, keys):
        pdf.section_title(title)
        pdf.set_font('Arial', 'B', 7)
        w = 190 / len(keys)
        for k in keys: pdf.cell(w, 6, k[:15], 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        for k in keys:
            val = data.get(f"{prefix}_{k.replace(' ', '_')}", 0)
            pdf.cell(w, 6, str(val), 1, 0, 'C')
        pdf.ln(10)

    quick_table("1. Matiere Premiere", "MP", ["Deposes", "Traites", "Valides", "Transmis", "Finances", "Rembourse"])
    quick_table("2. Triangulaire", "TRI", ["Deposes", "Valides", "Transmis", "Finances", "BC10", "BC90", "Rembourse"])
    
    pdf.ln(10)
    pdf.cell(190, 10, "Signature de l'accompagnateur", 0, 1, 'R')
    return pdf.output()

# --- UTILISATEURS ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]
USERS_DB = {"admin": "admin123"}
for i, nom in enumerate(LISTE_NOMS): USERS_DB[nom] = str(1234 + (i * 11))

# --- AUTHENTIFICATION ---
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

# --- NAVIGATION ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    if st.session_state.user == "admin":
        st.link_button("📂 Voir Google Sheets", "https://docs.google.com/spreadsheets/d/1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM/edit")
    menu = ["📝 Bilan"]
    if st.session_state.user == "admin": menu += ["📊 Suivi", "🔑 Codes"]
    choix = st.radio("Menu", menu)
    if st.button("🚪 Déconnexion"): st.session_state.auth = False; st.rerun()

# --- SAISIE DES 84 RUBRIQUES ---
if choix == "📝 Bilan":
    st.title(f"Saisie Officielle - {st.session_state.user}")
    if 'visite' not in st.session_state: st.session_state.visite = set()
    
    c1, c2 = st.columns(2)
    mois = c1.selectbox("Mois", ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"])
    annee = c2.number_input("Année", 2026)
    
    data = {"Accompagnateur": st.session_state.user, "Mois": mois, "Annee": annee, "Date": datetime.now().strftime("%d/%m/%Y")}

    def rub(titre, p):
        st.subheader(titre)
        c = st.columns(5)
        data[f"{p}_Deposes"] = c[0].number_input("Deposes", key=f"{p}d", value=0)
        data[f"{p}_Traites"] = c[1].number_input("Traites", key=f"{p}t", value=0)
        data[f"{p}_Valides"] = c[2].number_input("Valides", key=f"{p}v", value=0)
        data[f"{p}_Transmis"] = c[3].number_input("Transmis", key=f"{p}m", value=0)
        data[f"{p}_Finances"] = c[4].number_input("Finances", key=f"{p}f", value=0)
        c2 = st.columns(4)
        data[f"{p}_BC10"] = c2[0].number_input("BC 10%", key=f"{p}o1", value=0)
        data[f"{p}_BC90"] = c2[1].number_input("BC 90%", key=f"{p}o9", value=0)
        data[f"{p}_PV_Exist"] = c2[2].number_input("PV Exist", key=f"{p}pe", value=0)
        data[f"{p}_PV_Dem"] = c2[3].number_input("PV Dem", key=f"{p}pd", value=0)
        c3 = st.columns(2)
        data[f"{p}_Remb_Nb"] = c3[0].number_input("Nb Recus", key=f"{p}rn", value=0)
        data[f"{p}_Rembourse"] = c3[1].number_input("Montant Remb.", key=f"{p}rm", value=0.0)

    t_names = ["1. MP", "2. Tri", "3. CAM", "4. Telecom", "5. Recyclage", "6. Tricycle", "7. AE", "8. NESDA", "9. Rappels"]
    tabs = st.tabs(t_names)
    
    for i, t in enumerate(tabs):
        with t:
            st.session_state.visite.add(t_names[i])
            if i == 0: rub("Achat Matiere Premiere", "MP")
            elif i == 1: rub("Formule Triangulaire", "TRI")
            elif i == 2: data["CAM_Recus"] = st.number_input("Citoyens reçus", 0)
            elif i == 3: rub("Dossiers Telecom", "AT")
            elif i == 4: rub("Dossiers Recyclage", "REC")
            elif i == 5: rub("Dossiers Tricycle", "TC")
            elif i == 6: rub("Dossiers Auto-Entrepreneur", "AE")
            elif i == 7: data["NESDA"] = st.number_input("Total NESDA", 0)
            elif i == 8: data["Visites"] = st.number_input("Sorties terrain", 0)

    st.markdown("---")
    if len(st.session_state.visite) >= 9:
        if st.button("💾 ENREGISTRER ET GÉNÉRER PDF", type="primary", use_container_width=True):
            if save_to_gsheet(data):
                st.success("Données sauvegardées !")
                pdf = generate_pdf(data)
                st.download_button("📥 TELECHARGER PDF", data=pdf, file_name=f"Bilan_{mois}.pdf", mime="application/pdf")
                st.balloons()
    else:
        st.warning(f"Consultez les 9 onglets avant d'enregistrer ({len(st.session_state.visite)}/9)")

# --- VUES ADMIN ---
elif choix == "📊 Suivi":
    st.title("Suivi des saisies")
    st.info("L'Admin peut voir ici le tableau global du mois.")
elif choix == "🔑 Codes":
    st.table([{"Nom": k, "Code": v} for k, v in USERS_DB.items()])
