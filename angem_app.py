import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Expert", layout="wide", page_icon="🇩🇿")

# --- 2. BASE DE DONNÉES ET CODES PERSONNELS ---
ACCES = {
    "admin": "admin77",
    "Mme GUESSMIA ZAHIRA": "ZAH24", "M. BOULAHLIB REDOUANE": "RED24", "Mme DJAOUDI SARAH": "SAR24",
    "Mme BEN SAHNOUN LILA": "LIL24", "Mme NASRI RIM": "RIM24", "Mme MECHALIKHE FATMA": "FAT24",
    "Mlle SALMI NOUR EL HOUDA": "NOU24", "M. BERRABEH DOUADI": "DOU24", "Mme BELAID FAZIA": "FAZ24",
    "M. METMAR OMAR": "OMA24", "Mme AIT OUARAB AMINA": "AMI24", "Mme MILOUDI AMEL": "AME24",
    "Mme BERROUANE SAMIRA": "SAM24", "M. MAHREZ MOHAMED": "MOH24", "Mlle FELFOUL SAMIRA": "FELS24",
    "Mlle MEDJHOUM RAOUIA": "RAO24", "Mme SAHNOUNE IMENE": "IME24", "Mme KHERIF FADILA": "KHE24",
    "Mme MERAKEB FAIZA": "MER24", "Mme MEJDOUB AMEL": "MEJ24", "Mme BEN AICHE MOUNIRA": "MOU24",
    "Mme SEKAT MANEL FATIMA": "MAN24", "Mme KADRI SIHEM": "SIH24", "Mme TOUAKNI SARAH": "TOU24",
    "Mme MAASSOUM EPS LAKHDARI SAIDA": "SAI24", "M. TALAMALI IMAD": "IMA24", "Mme BOUCHAREB MOUNIA": "BOU24"
}

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

# --- 3. GÉNÉRATEUR PDF (AVEC FIX CHIFFRES) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Regionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf(data_dict, promos_df=None):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activites mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Accompagnateur : {data_dict.get('Accompagnateur', '---')}", 0, 1, 'L')
    pdf.cell(190, 8, f"Mois : {str(data_dict.get('Mois', '')).upper()} 2026", 0, 1, 'R')
    pdf.ln(5)

    def draw_section(title, headers, keys):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 5.5)
        w = 190 / len(headers)
        for h in headers: pdf.cell(w, 5, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for k in keys:
            val = data_dict.get(k, 0)
            try:
                # Force l'affichage du chiffre propre
                v_str = str(int(float(val))) if str(val).replace('.','').replace('-','').isdigit() else str(val)
            except: v_str = str(val)
            pdf.cell(w, 7, v_str, 1, 0, 'C')
        pdf.ln(10)

    draw_section("1. Formule : Achat de matiere premieres", ["Deposes", "Traites CEF", "Valides CEF", "Transmis AR", "Finances", "Recus", "Montant"], ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])
    h_std = ["Deposes", "Valides", "Trans. Bq", "Notif. Bq", "Trans. AR", "Finances", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"]
    draw_section("2. Formule : Triangulaire", h_std, ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    draw_section("5. Algerie Telecom", h_std, ["AT_D", "AT_V", "AT_B", "AT_N", "AT_A", "AT_F", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    draw_section("9. Suivi & Rappels", ["Appels", "NESDA", "Terrain", "R_27k", "R_40k", "R_100k", "R_400k", "R_1M"], ["TEL_A", "NE_T", "ST_T", "R_27", "R_40", "R_100", "R_400", "R_1M"])

    if promos_df is not None and not promos_df.empty:
        pdf.ln(5); pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 10)
        pdf.cell(190, 8, "LISTE DES PROMOTEURS CONTACTES", 1, 1, 'C', True)
        pdf.set_font('Arial', 'B', 8); w_p = [55, 50, 45, 40]
        for i, c in enumerate(["Nom & Prenom", "Activite", "Financement", "Telephone"]): pdf.cell(w_p[i], 7, c, 1, 0, 'C')
        pdf.ln(); pdf.set_font('Arial', '', 8)
        for _, row in promos_df.iterrows():
            if any(str(x).strip() != "" for x in row):
                pdf.cell(55, 7, str(row[0]), 1, 0, 'L'); pdf.cell(50, 7, str(row[1]), 1, 0, 'L')
                pdf.cell(45, 7, str(row[2]), 1, 0, 'C'); pdf.cell(40, 7, str(row[3]), 1, 0, 'C')
                pdf.ln()
    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO")
    role = st.radio("Connexion", ["Accompagnateur", "Administrateur"])
    u = st.selectbox("Utilisateur", list(ACCES.keys()) if role == "Accompagnateur" else ["admin"])
    p = st.text_input("Code Personnel", type="password")
    if st.button("Se connecter"):
        if ACCES.get(u) == p:
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, role
            st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# --- 5. ESPACE ADMIN (DÉTAILLÉ) ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration Centrale")
    t1, t2, t3 = st.tabs(["Données Agence", "Téléchargements PDF", "Liste des Codes"])
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        ws = sh.worksheet("SAISIE_BRUTE")
        all_v = ws.get_all_values()
        df = pd.DataFrame(all_v[1:], columns=[h if h!="" else f"V_{i}" for i,h in enumerate(all_v[0])]) if len(all_v)>1 else pd.DataFrame()
    except Exception as e:
        st.error(f"Connexion impossible : {e}")
        st.stop()

    with t1:
        st.subheader("📁 Historique des saisies")
        st.dataframe(df)
        if not df.empty:
            del_idx = st.selectbox("Ligne à supprimer", df.index, format_func=lambda x: f"Ligne {x+2}: {df.loc[x,'Accompagnateur']} ({df.loc[x,'Mois']})")
            if st.button("❌ SUPPRIMER L'ENREGISTREMENT"):
                ws.delete_rows(del_idx + 2)
                st.success("Donnée supprimée !")
                st.rerun()

    with t2:
        if not df.empty:
            idx = st.selectbox("Sélectionner une fiche", df.index, format_func=lambda x: f"{df.loc[x, 'Accompagnateur']} - {df.loc[x, 'Mois']}")
            st.download_button("📥 PDF INDIVIDUEL", generate_pdf(df.loc[idx].to_dict()), f"Bilan_{df.loc[idx, 'Accompagnateur']}.pdf")
            st.markdown("---")
            m_sel = st.selectbox("Mois pour le CUMUL", df['Mois'].unique())
            if st.button("CALCULER LE TOTAL MENSUEL"):
                df_f = df[df['Mois'] == m_sel].copy()
                cols = [c for c in df_f.columns if c not in ["Accompagnateur", "Mois", "Annee", "Date"]]
                for c in cols: df_f[c] = pd.to_numeric(df_f[c], errors='coerce').fillna(0)
                total_data = {'Accompagnateur': "TOTAL AGENCE", 'Mois': m_sel, 'Annee': 2026, **df_f[cols].sum().to_dict()}
                st.download_button("📥 TÉLÉCHARGER LE CUMUL PDF", generate_pdf(total_data), f"Total_{m_sel}.pdf")
    
    with t3:
        st.subheader("🔑 Codes d'accès personnels")
        st.table(pd.DataFrame(list(ACCES.items()), columns=["Nom", "Code"]))
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()
    st.stop()

# --- 6. FORMULAIRE ACCOMPAGNATEUR ---
st.title(f"Bilan : {st.session_state.user}")
m_s = st.selectbox("Mois du rapport", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
data = {"Accompagnateur": st.session_state.user, "Mois": m_s, "Annee": 2026, "Date": datetime.now().strftime("%d/%m/%Y")}

def ui_sec(label, p, kp):
    st.subheader(label); c1,c2,c3,c4,c5 = st.columns(5)
    data[f"{p}_D"]=c1.number_input(f"Dossiers Déposés", key=f"{kp}1")
    data[f"{p}_V"]=c2.number_input(f"Dossiers Validés CEF", key=f"{kp}2")
    data[f"{p}_B"]=c3.number_input(f"Transmis Banque", key=f"{kp}3")
    data[f"{p}_N"]=c4.number_input(f"Notifications Banque", key=f"{kp}4")
    data[f"{p}_A"]=c5.number_input(f"Transmis AR", key=f"{kp}5")
    c6,c7,c8,c9 = st.columns(4)
    data[f"{p}_F"]=c6.number_input(f"Dossiers Financés", key=f"{kp}6")
    data[f"{p}_1"]=c7.number_input(f"OE 10%", key=f"{kp}7")
    data[f"{p}_9"]=c8.number_input(f"OE 90%", key=f"{kp}8")
    data[f"{p}_E"]=c9.number_input(f"PV d'Existence", key=f"{kp}9")
    c10,c11,c12 = st.columns(3)
    data[f"{p}_D"]=c10.number_input(
