import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Code Principal Officiel", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE GOOGLE SHEETS ---
def save_to_gsheet(data_dict):
    try:
        # Utilisation des secrets Streamlit pour la connexion
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        worksheet = sh.worksheet("SAISIE_BRUTE")
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (MISE EN FORME EXACTE DU MODÈLE) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(5)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

    def section_header(self, title):
        self.set_fill_color(255, 230, 204) # Couleur Beige Orangé du modèle
        self.set_font('Arial', 'B', 10)
        self.cell(190, 8, title, 1, 1, 'L', True)
        self.ln(2)

def generate_pdf_bytes(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 10, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.ln(5)

    # Fonction pour dessiner les lignes de données dans le PDF
    def draw_row(headers, keys):
        pdf.set_font('Arial', 'B', 7)
        width = 190 / len(headers)
        for h in headers: pdf.cell(width, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        for k in keys: pdf.cell(width, 7, str(data.get(k, 0)), 1, 0, 'C')
        pdf.ln(8)

    # 1. Matière Première
    pdf.section_header("1. Formule : Achat de matière premières")
    draw_row(["Déposés", "Traités CEF", "Validés CEF", "Transmis AR", "Financés"], 
             ["MP_Dép", "MP_Tra", "MP_Val", "MP_T_AR", "MP_Fin"])
    draw_row(["Reçus Remb.", "Montant Remboursé (DA)"], ["MP_Rec", "MP_Mnt"])

    # 2. Triangulaire
    pdf.section_header("2. Formule : Triangulaire")
    draw_row(["Déposés", "Traités", "Validés", "Trans. Banque", "Notif. Bq"], 
             ["TRI_Dép", "TRI_Tra", "TRI_Val", "TRI_T_Bq", "TRI_Not"])
    draw_row(["Trans. AR", "Financés", "OE 10%", "OE 90%"], 
             ["TRI_T_AR", "TRI_Fin", "TRI_OE10", "TRI_OE90"])
    draw_row(["PV Exist.", "PV Dém.", "Reçus Remb.", "Montant Remb."], 
             ["TRI_PV_E", "TRI_PV_D", "TRI_Rec", "TRI_Mnt"])

    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCÈS ANGEM PRO")
    u = st.selectbox("Sélectionnez votre nom", [""] + LISTE_NOMS)
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DÉPLIÉ (AUCUNE ABRÉVIATION) ---
st.title(f"Bilan Mensuel - {st.session_state.user}")
col_m, col_a = st.columns(2)
mois_sel = col_m.selectbox("Mois du rapport", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = col_a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Spécifiques (AT/REC)", "4. Tricycle / AE", "5. Accueil / Terrain"])

# --- SECTION 1 : MP ---
with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    c1, c2, c3, c4, c5 = st.columns(5)
    data["MP_Dép"] = c1.number_input("Nbrs. Dossiers déposés (MP)", key="mp1")
    data["MP_Tra"] = c2.number_input("Nbrs. Dossiers traités CEF (MP)", key="mp2")
    data["MP_Val"] = c3.number_input("Nbrs. Dossiers validés CEF (MP)", key="mp3")
    data["MP_T_AR"] = c4.number_input("Nbrs. Dossiers transmis AR (MP)", key="mp4")
    data["MP_Fin"] = c5.number_input("Nbrs. Dossiers financés (MP)", key="mp5")
    c6, c7 = st.columns(2)
    data["MP_Rec"] = c6.number_input("Nbrs. reçus de remboursement (MP)", key="mp6")
    data["MP_Mnt"] = c7.number_input("Montant remboursé (DA) (MP)", key="mp7")

# --- SECTION 2 : TRI ---
with tabs[1]:
    st.subheader("2. Formule : Triangulaire")
    t1, t2, t3, t4, t5 = st.columns(5)
    data["TRI_Dép"] = t1.number_input("Dossiers déposés (TRI)", key="tr1")
    data["TRI_Tra"] = t2.number_input("Traités CEF (TRI)", key="tr2")
    data["TRI_Val"] = t3.number_input("Validés CEF (TRI)", key="tr3")
    data["TRI_T_Bq"] = t4.number_input("Transmis Banque (TRI)", key="tr4")
    data["TRI_Not"] = t5.number_input("Notifications bancaires (TRI)", key="tr5")
    t6, t7, t8, t9 = st.columns(4)
    data["TRI_T_AR"] = t6.number_input("Transmis AR (TRI)", key="tr6")
    data["TRI_Fin"] = t7.number_input("Dossiers financés (TRI)", key="tr7")
    data["TRI_OE10"] = t8.number_input("Ordre enlèvement 10% (TRI)", key="tr8")
    data["TRI_OE90"] = t9.number_input("Ordre enlèvement 90% (TRI)", key="tr9")
    t10, t11, t12, t13 = st.columns(4)
    data["TRI_PV_E"] = t10.number_input("PV Existence (TRI)", key="tr10")
    data["TRI_PV_D"] = t11.number_input("PV Démarrage (TRI)", key="tr11")
    data["TRI_Rec"] = t12.number_input("Nbrs. reçus remboursement (TRI)", key="tr12")
    data["TRI_Mnt"] = t13.number_input("Montant remboursé (TRI)", key="tr13")

# --- SECTION 5 : ACCUEIL / TERRAIN ---
with tabs[4]:
    st.subheader("Accueil & Terrain")
    data["ACC_Total"] = st.number_input("Nbrs. de citoyens reçus (CAM)", key="ac1")
    st.info("Motifs de visite :")
    ca1, ca2, ca3 = st.columns(3)
    data["ACC_Info"] = ca1.number_input("Demande d'information", key="ac2")
    data["ACC_Depot"] = ca2.number_input("Dépôt de dossier", key="ac3")
    data["ACC_Accomp"] = ca3.number_input("Accompagnement", key="ac4")
    data["ST_Total"] = st.number_input("Nombre de sorties sur terrain", key="st1")

st.markdown("---")

# --- 6. ACTIONS SÉPARÉES ---
btn_save, btn_pdf, btn_excel = st.columns(3)

with btn_save:
    if st.button("💾 ENREGISTRER (Google Sheets)", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Données sauvegardées dans la base !")

with btn_pdf:
    pdf_out = generate_pdf_bytes(data)
    st.download_button("📥 TÉLÉCHARGER LE PDF OFFICIEL", data=pdf_out, file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)

with btn_excel:
    df_export = pd.DataFrame([data])
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False)
    st.download_button("📊 EXPORTER VERS EXCEL", data=excel_io.getvalue(), file_name=f"Bilan_{mois_sel}.xlsx", use_container_width=True)
