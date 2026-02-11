import streamlit as st
import pandas as pd
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
        worksheet = sh.worksheet("SAISIE_BRUTE")
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur Base de données : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (CORRECTION FPDF2) ---
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
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Mois : {data.get('Mois', '').upper()} {data.get('Annee', '')}", 0, 1, 'R')
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(130, 8, "Rubrique", 1, 0, 'L', True)
    pdf.cell(60, 8, "Valeur", 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 8)
    for key, val in data.items():
        if key not in ["Accompagnateur", "Mois", "Annee", "Date"]:
            pdf.cell(130, 7, str(key).replace('_', ' '), 1)
            pdf.cell(60, 7, str(val), 1, 1, 'C')
            
    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCÈS ANGEM")
    u = st.selectbox("Utilisateur", [""] + LISTE_NOMS)
    p = st.text_input("Code", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DÉPLIÉ (AUCUNE ABRÉVIATION) ---
st.title(f"Bilan de : {st.session_state.user}")
m, a = st.columns(2)
mois_sel = m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Télécom", "4. Recyclage", "5. Tricycle", "6. Auto-Entrepreneur", "7. NESDA / Terrain"])

# --- 1. MP ---
with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    c1, c2, c3 = st.columns(3)
    data["MP_Nbrs_Dossiers_déposés"] = c1.number_input("Nbrs. Dossiers déposés", key="mp1")
    data["MP_Nbrs_Dossiers_traités_par_CEF"] = c2.number_input("Nbrs. Dossiers traités par CEF", key="mp2")
    data["MP_Nbrs_Dossiers_validés_par_la_CEF"] = c3.number_input("Nbrs. Dossiers validés par la CEF", key="mp3")
    c4, c5 = st.columns(2)
    data["MP_Nbrs_Dossiers_transmis_AR"] = c4.number_input("Nbrs. Dossiers transmis à L'AR", key="mp4")
    data["MP_Nbrs_dossiers_financés"] = c5.number_input("Nbrs. dossiers financés", key="mp5")

# --- FONCTION SECTIONS ---
def render_tab(label, prefix, kp):
    st.subheader(label)
    cols1 = st.columns(3)
    data[f"{prefix}_Dossiers_déposés"] = cols1[0].number_input(f"Dossiers déposés ({prefix})", key=f"{kp}1")
    data[f"{prefix}_Dossiers_validés_CEF"] = cols1[1].number_input(f"Validés CEF ({prefix})", key=f"{kp}2")
    data[f"{prefix}_Transmis_Banque"] = cols1[2].number_input(f"Transmis Banque ({prefix})", key=f"{kp}3")
    cols2 = st.columns(3)
    data[f"{prefix}_Notifications_bancaires"] = cols2[0].number_input(f"Notifications bancaires ({prefix})", key=f"{kp}4")
    data[f"{prefix}_Ordre_enlèvement_10"] = cols2[1].number_input(f"Ordre enlèvement 10% ({prefix})", key=f"{kp}5")
    data[f"{prefix}_Ordre_enlèvement_90"] = cols2[2].number_input(f"Ordre enlèvement 90% ({prefix})", key=f"{kp}6")
    cols3 = st.columns(2)
    data[f"{prefix}_PV_Existence"] = cols3[0].number_input(f"PV Existence ({prefix})", key=f"{kp}7")
    data[f"{prefix}_PV_Démarrage"] = cols3[1].number_input(f"PV Démarrage ({prefix})", key=f"{kp}8")

with tabs[1]: render_tab("2. Formule : Triangulaire", "TRI", "t")
with tabs[2]: render_tab("5. Dossiers (Algérie télécom)", "AT", "at")
with tabs[3]: render_tab("6. Dossiers (Recyclage)", "REC", "re")
with tabs[4]: render_tab("7. Dossiers (Tricycle)", "TC", "tc")

# --- AE ---
with tabs[5]:
    st.subheader("8. Dossiers (Auto-entrepreneur)")
    data["AE_Dossiers_déposés"] = st.number_input("Nbrs. Dossiers déposés (AE)", key="ae1")
    data["AE_Dossiers_validés_CEF"] = st.number_input("Nbrs. Dossiers validés CEF (AE)", key="ae3")

# --- NESDA ---
with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels")
    data["NESDA_Dossiers"] = st.number_input("Dossiers orientés NESDA", key="nes1")
    data["Sorties_Terrain"] = st.number_input("Sorties terrain", key="st1")
    data["Rappels_Total"] = st.number_input("Total Lettres de rappel", key="r1")

st.markdown("---")

# --- 6. ACTIONS SÉPARÉES ---
btn_save, btn_pdf, btn_excel = st.columns(3)

with btn_save:
    if st.button("💾 ENREGISTRER DANS LA BASE", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Données enregistrées !")

with btn_pdf:
    pdf_out = generate_pdf_bytes(data)
    st.download_button("📥 TÉLÉCHARGER PDF", data=pdf_out, file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)

with btn_excel:
    try:
        df = pd.DataFrame([data])
        excel_io = io.BytesIO()
        with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📊 EXPORTER VERS EXCEL", data=excel_io.getvalue(), file_name=f"Bilan_{mois_sel}.xlsx", use_container_width=True)
    except Exception as e:
        st.error(f"Installez xlsxwriter dans requirements.txt : {e}")
