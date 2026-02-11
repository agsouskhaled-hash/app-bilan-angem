import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Rapport Officiel", layout="wide", page_icon="🇩🇿")

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

# --- 3. GÉNÉRATEUR PDF (MODÈLE FIDÈLE) ---
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
    pdf.cell(190, 8, f"Mois : {data.get('Mois', '').upper()} {data.get('Annee', '')}", 0, 1, 'R')
    pdf.ln(5)
    
    # Structure simple pour le test PDF
    pdf.set_fill_color(255, 230, 204)
    pdf.cell(190, 8, "Résumé des activités", 1, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    for key, val in data.items():
        if isinstance(val, (int, float)) and val > 0:
            pdf.cell(100, 7, f"{key}:", 1)
            pdf.cell(90, 7, str(val), 1, 1, 'C')
            
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Accès")
    u = st.selectbox("Sélectionnez votre nom", [""] + LISTE_NOMS)
    p = st.text_input("Code", type="password")
    if st.button("Connexion"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DÉTAILLÉ (10 RUBRIQUES - NOMS ENTIERS) ---
st.title(f"Bilan mensuel : {st.session_state.user}")
c_m, c_a = st.columns(2)
mois_sel = c_m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = c_a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Algérie Télécom", "4. Recyclage", "5. Tricycle", "6. Auto-Entrepreneur", "7. NESDA / Terrain"])

# --- 1. MATIERE PREMIERE ---
with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    c1, c2, c3 = st.columns(3)
    data["MP_Dossiers_déposés"] = c1.number_input("Nombre de dossiers déposés (MP)", key="mp1")
    data["MP_Dossiers_traités_CEF"] = c2.number_input("Nombre de dossiers traités par la CEF (MP)", key="mp2")
    data["MP_Dossiers_validés_CEF"] = c3.number_input("Nombre de dossiers validés par la CEF (MP)", key="mp3")
    c4, c5, c6 = st.columns(3)
    data["MP_Dossiers_transmis_AR"] = c4.number_input("Nombre de dossiers transmis à l'AR (MP)", key="mp4")
    data["MP_Dossiers_financés"] = c5.number_input("Nombre de dossiers financés (MP)", key="mp5")
    data["MP_Recus_remboursement"] = c6.number_input("Nombre de reçus de remboursement (MP)", key="mp6")
    data["MP_Montant_remboursé"] = st.number_input("Montant total remboursé (DA) (MP)", key="mp7")

# --- 2. TRIANGULAIRE ---
with tabs[1]:
    st.subheader("2. Formule : Triangulaire")
    t1, t2, t3, t4 = st.columns(4)
    data["TRI_Dossiers_déposés"] = t1.number_input("Nbrs. Dossiers déposés (TRI)", key="tri1")
    data["TRI_Dossiers_traités_CEF"] = t2.number_input("Nbrs. Dossiers traités CEF (TRI)", key="tri2")
    data["TRI_Dossiers_validés_CEF"] = t3.number_input("Nbrs. Dossiers validés CEF (TRI)", key="tri3")
    data["TRI_Dossiers_transmis_Banque"] = t4.number_input("Nbrs. Dossiers transmis à la Banque (TRI)", key="tri4")
    t5, t6, t7 = st.columns(3)
    data["TRI_Notifications_bancaires"] = t5.number_input("Nbrs. Notifications bancaires (TRI)", key="tri5")
    data["TRI_Dossiers_transmis_AR"] = t6.number_input("Nbrs. Dossiers transmis à l'AR (TRI)", key="tri6")
    data["TRI_Dossiers_financés"] = t7.number_input("Nbrs. Dossiers financés (TRI)", key="tri7")
    t8, t9, t10, t11 = st.columns(4)
    data["TRI_Ordre_10"] = t8.number_input("Nbrs. Ordre d'enlèvement 10% (TRI)", key="tri8")
    data["TRI_Ordre_90"] = t9.number_input("Nbrs. Ordre d'enlèvement 90% (TRI)", key="tri9")
    data["TRI_PV_Existence"] = t10.number_input("Nbrs. PV d'Existence (TRI)", key="tri10")
    data["TRI_PV_Démarrage"] = t11.number_input("Nbrs. PV Démarrage (TRI)", key="tri11")

# --- 3. ALGERIE TELECOM ---
with tabs[2]:
    st.subheader("5. Dossiers (Algérie télécom)")
    a1, a2, a3, a4 = st.columns(4)
    data["AT_Dossiers_déposés"] = a1.number_input("Nbrs. Dossiers déposés (AT)", key="at1")
    data["AT_Dossiers_validés_CEF"] = a2.number_input("Nbrs. Dossiers validés CEF (AT)", key="at2")
    data["AT_Dossiers_transmis_Banque"] = a3.number_input("Nbrs. Dossiers transmis à la Banque (AT)", key="at3")
    data["AT_Notifications_bancaires"] = a4.number_input("Nbrs. Notifications bancaires (AT)", key="at4")
    a5, a6, a7, a8 = st.columns(4)
    data["AT_Ordre_10"] = a5.number_input("Nbrs. Ordre d'enlèvement 10% (AT)", key="at5")
    data["AT_Ordre_90"] = a6.number_input("Nbrs. Ordre d'enlèvement 90% (AT)", key="at6")
    data["AT_PV_Existence"] = a7.number_input("Nbrs. PV d'Existence (AT)", key="at7")
    data["AT_PV_Démarrage"] = a8.number_input("Nbrs. PV Démarrage (AT)", key="at8")

# --- 4. RECYCLAGE ---
with tabs[3]:
    st.subheader("6. Dossiers (Recyclage)")
    r1, r2, r3, r4 = st.columns(4)
    data["REC_Dossiers_déposés"] = r1.number_input("Nbrs. Dossiers déposés (REC)", key="rec1")
    data["REC_Dossiers_validés_CEF"] = r2.number_input("Nbrs. Dossiers validés CEF (REC)", key="rec2")
    data["REC_Dossiers_transmis_Banque"] = r3.number_input("Nbrs. Dossiers transmis à la Banque (REC)", key="rec3")
    data["REC_PV_Existence"] = r4.number_input("Nbrs. PV d'Existence (REC)", key="rec4")

# --- 7. NESDA / TERRAIN ---
with tabs[6]:
    st.subheader("9. Dossiers orientés / 10. Rappels")
    n1, n2 = st.columns(2)
    data["NESDA_Dossiers"] = n1.number_input("Nbrs. de dossiers orientés NESDA", key="nes1")
    data["Sorties_Terrain"] = n2.number_input("Nbrs. Sortie sur terrain", key="st1")
    data["Rappels_27k"] = st.number_input("Lettres de rappel 27 000 DA", key="r1")
    data["Rappels_40k"] = st.number_input("Lettres de rappel 40 000 DA", key="r2")
    data["Rappels_100k"] = st.number_input("Lettres de rappel 100 000 DA", key="r3")

st.markdown("---")

# --- 6. ACTIONS SÉPARÉES ---
col_save, col_pdf, col_excel = st.columns(3)

with col_save:
    if st.button("💾 ENREGISTRER", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Données enregistrées !")

with col_pdf:
    pdf_out = generate_pdf_bytes(data)
    st.download_button("📥 PDF", data=pdf_out, file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)

with col_excel:
    df = pd.DataFrame([data])
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📊 EXCEL", data=excel_io.getvalue(), file_name=f"Bilan_{mois_sel}.xlsx", use_container_width=True)
