import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Code Principal", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE (MÉTHODE CHAMP PAR CHAMP) ---
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
        worksheet = sh.worksheet("SAISIE_BRUTE")
        worksheet.append_row(list(data_dict.values()))
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- 3. GÉNÉRATEUR PDF (MISE EN FORME MIROIR INTÉGRALE) ---
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
    pdf.cell(190, 8, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.ln(5)

    def draw_section(title, headers, keys):
        pdf.set_fill_color(255, 230, 204) # Beige Orangé
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 6)
        width = 190 / len(headers)
        for h in headers: pdf.cell(width, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for k in keys: pdf.cell(width, 7, str(data.get(k, 0)), 1, 0, 'C')
        pdf.ln(8)

    # --- TOUTES LES SECTIONS DANS LE PDF ---
    h_std = ["Déposés", "Traités CEF", "Validés CEF", "Trans. AR", "Financés", "Reçus", "Montant"]
    draw_section("1.Formule : Achat de matière premières", h_std, 
                 ["MP_Dép", "MP_Tra", "MP_Val", "MP_TAR", "MP_Fin", "MP_Rec", "MP_Mnt"])

    h_ext = ["Déposés", "Traités", "Validés", "Trans. Bq", "Notif. Bq", "Trans. AR", "Financés", "OE 10%", "OE 90%", "PV Exis", "PV Dém", "Reçus", "Montant"]
    draw_section("2.Formule : Triangulaire", h_ext, 
                 ["TR_Dép", "TR_Tra", "TR_Val", "TR_TBq", "TR_Not", "TR_TAR", "TR_Fin", "TR_O10", "TR_O90", "TR_PVE", "TR_PVD", "TR_Rec", "TR_Mnt"])

    draw_section("5. Dossiers (Algérie télécom)", h_ext, 
                 ["AT_Dép", "AT_Tra", "AT_Val", "AT_TBq", "AT_Not", "AT_TAR", "AT_Fin", "AT_O10", "AT_O90", "AT_PVE", "AT_PVD", "AT_Rec", "AT_Mnt"])

    draw_section("6. Dossiers (Recyclage)", h_ext, 
                 ["RE_Dép", "RE_Tra", "RE_Val", "RE_TBq", "RE_Not", "RE_TAR", "RE_Fin", "RE_O10", "RE_O90", "RE_PVE", "RE_PVD", "RE_Rec", "RE_Mnt"])

    draw_section("7. Dossiers (Tricycle)", h_ext, 
                 ["TC_Dép", "TC_Tra", "TC_Val", "TC_TBq", "TC_Not", "TC_TAR", "TC_Fin", "TC_O10", "TC_O90", "TC_PVE", "TC_PVD", "TC_Rec", "TC_Mnt"])

    draw_section("8. Dossiers (Auto-Entrepreneur)", h_ext, 
                 ["AE_Dép", "AE_Tra", "AE_Val", "AE_TBq", "AE_Not", "AE_TAR", "AE_Fin", "AE_O10", "AE_O90", "AE_PVE", "AE_PVD", "AE_Rec", "AE_Mnt"])

    h_acc = ["Total Reçus", "Info", "Dépôt", "Accomp.", "Remb.", "Autres"]
    draw_section("4. L'accueil des citoyens au niveau de la CAM", h_acc, 
                 ["AC_Tot", "AC_Inf", "AC_Dép", "AC_Acc", "AC_Rem", "AC_Aut"])

    h_rap = ["NESDA", "Terrain", "Rap. 27k", "Rap. 40k", "Rap. 100k", "Rap. 400k", "Rap. 1M"]
    draw_section("9. NESDA / 10. Rappels et Sorties", h_rap, 
                 ["NE_Tot", "ST_Tot", "R_27k", "R_40k", "R_100k", "R_400k", "R_1M"])

    return pdf.output()

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

# --- 5. FORMULAIRE DÉPLIÉ (86 CASES) ---
st.title(f"Bilan : {st.session_state.user}")
m, a = st.columns(2)
mois_sel = m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

def full_input(label, p, key_p):
    st.subheader(label)
    c1, c2, c3, c4, c5 = st.columns(5)
    data[f"{p}_Dép"] = c1.number_input(f"Déposés ({p})", key=f"{key_p}1")
    data[f"{p}_Tra"] = c2.number_input(f"Traités CEF ({p})", key=f"{key_p}2")
    data[f"{p}_Val"] = c3.number_input(f"Validés CEF ({p})", key=f"{key_p}3")
    data[f"{p}_TBq"] = c4.number_input(f"Transmis Banque ({p})", key=f"{key_p}4")
    data[f"{p}_Not"] = c5.number_input(f"Notif. Banque ({p})", key=f"{key_p}5")
    c6, c7, c8, c9, c10 = st.columns(5)
    data[f"{p}_TAR"] = c6.number_input(f"Transmis AR ({p})", key=f"{key_p}6")
    data[f"{p}_Fin"] = c7.number_input(f"Financés ({p})", key=f"{key_p}7")
    data[f"{p}_O10"] = c8.number_input(f"OE 10% ({p})", key=f"{key_p}8")
    data[f"{p}_O90"] = c9.number_input(f"OE 90% ({p})", key=f"{key_p}9")
    data[f"{p}_PVE"] = c10.number_input(f"PV Existence ({p})", key=f"{key_p}10")
    c11, c12 = st.columns(2)
    data[f"{p}_PVD"] = c11.number_input(f"PV Démarrage ({p})", key=f"{key_p}11")
    data[f"{p}_Rec"] = c12.number_input(f"Reçus Remb. ({p})", key=f"{key_p}12")
    data[f"{p}_Mnt"] = st.number_input(f"Montant Remboursé ({p})", key=f"{key_p}13")

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Télécom / Recyclage", "4. Tricycle / AE", "5. Accueil / Terrain"])

with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    cx1, cx2, cx3, cx4, cx5 = st.columns(5)
    data["MP_Dép"] = cx1.number_input("Dossiers déposés (MP)", key="m1")
    data["MP_Tra"] = cx2.number_input("Traités CEF (MP)", key="m2")
    data["MP_Val"] = cx3.number_input("Validés CEF (MP)", key="m3")
    data["MP_TAR"] = cx4.number_input("Transmis AR (MP)", key="m4")
    data["MP_Fin"] = cx5.number_input("Financés (MP)", key="m5")
    cx6, cx7 = st.columns(2)
    data["MP_Rec"] = cx6.number_input("Nbrs reçus remb. (MP)", key="m6")
    data["MP_Mnt"] = cx7.number_input("Montant remboursé (MP)", key="m7")

with tabs[1]: full_input("2. Formule : Triangulaire", "TR", "tri")

with tabs[2]:
    full_input("5. Dossiers (Algérie Télécom)", "AT", "atl")
    st.markdown("---")
    full_input("6. Dossiers (Recyclage)", "RE", "rec")

with tabs[3]:
    full_input("7. Dossiers (Tricycle)", "TC", "tric")
    st.markdown("---")
    full_input("8. Dossiers (Auto-Entrepreneur)", "AE", "aen")

with tabs[4]:
    st.subheader("4. Accueil (CAM)")
    ca1, ca2, ca3 = st.columns(3)
    data["AC_Tot"] = ca1.number_input("Total Citoyens Reçus", key="acc1")
    data["AC_Inf"] = ca2.number_input("Demande Info", key="acc2")
    data["AC_Dép"] = ca3.number_input("Dépôt Dossier", key="acc3")
    ca4, ca5, ca6 = st.columns(3)
    data["AC_Acc"] = ca4.number_input("Accompagnement", key="acc4")
    data["AC_Rem"] = ca5.number_input("Remboursement", key="acc5")
    data["AC_Aut"] = ca6.number_input("Autres motifs", key="acc6")
    st.subheader("9. NESDA / 10. Terrain & Rappels")
    ra1, ra2, ra3 = st.columns(3)
    data["NE_Tot"] = ra1.number_input("Dossiers NESDA", key="rap1")
    data["ST_Tot"] = ra2.number_input("Sorties Terrain", key="rap2")
    data["R_27k"] = ra3.number_input("Rappel 27.000 DA", key="rap3")
    ra4, ra5, ra6, ra7 = st.columns(4)
    data["R_40k"] = ra4.number_input("Rappel 40.000 DA", key="rap4")
    data["R_100k"] = ra5.number_input("Rappel 100.000 DA", key="rap5")
    data["R_400k"] = ra6.number_input("Rappel 400.000 DA", key="rap6")
    data["R_1M"] = ra7.number_input("Rappel 1.000.000 DA", key="rap7")

st.markdown("---")

# --- 6. ACTIONS ---
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("💾 ENREGISTRER DANS LA BASE", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Enregistré !")
with b2:
    st.download_button("📥 TÉLÉCHARGER LE PDF COMPLET", data=generate_pdf_bytes(data), file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)
with b3:
    df_x = pd.DataFrame([data])
    io_x = io.BytesIO()
    with pd.ExcelWriter(io_x, engine='xlsxwriter') as wr:
        df_x.to_excel(wr, index=False)
    st.download_button("📊 EXPORTER VERS EXCEL", data=io_x.getvalue(), file_name=f"Bilan_{mois_sel}.xlsx", use_container_width=True)
