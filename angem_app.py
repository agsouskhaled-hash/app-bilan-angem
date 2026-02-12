import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Expert", layout="wide", page_icon="🇩🇿")

# --- 2. BASE DE DONNÉES ET CODES ---
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

# --- 3. GÉNÉRATEUR PDF ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf(data, list_promoteurs=None):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 8, f"Accompagnateur : {data.get('Accompagnateur', '---')}", 0, 1, 'L')
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(190, 8, f"Mois : {str(data.get('Mois', '')).upper()} {data.get('Annee', '')}", 0, 1, 'R')
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
            val = data.get(k, 0)
            val_str = str(int(val)) if isinstance(val, (int, float)) and val == int(val) else str(val)
            pdf.cell(w, 7, val_str, 1, 0, 'C')
        pdf.ln(10)

    # Sections habituelles (Inchangées)
    draw_section("1. Formule : Achat de matière premières", ["Déposés", "Traités CEF", "Validés CEF", "Transmis AR", "Financés", "Reçus", "Montant"], ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])
    h_std = ["Déposés", "Validés", "Trans. Bq", "Notif. Bq", "Trans. AR", "Financés", "OE 10%", "OE 90%", "PV Exist", "PV Dém", "Reçus", "Montant"]
    draw_section("2. Formule : Triangulaire", h_std, ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    draw_section("5. Algérie Télécom", h_std, ["AT_D", "AT_V", "AT_B", "AT_N", "AT_A", "AT_F", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    draw_section("6. Recyclage", h_std, ["RE_D", "RE_V", "RE_B", "RE_N", "RE_A", "RE_F", "RE_1", "RE_9", "RE_E", "RE_D", "RE_R", "RE_M"])
    draw_section("7. Tricycle", h_std, ["TC_D", "TC_V", "TC_B", "TC_N", "TC_A", "TC_F", "TC_1", "TC_9", "TC_E", "TC_D", "TC_R", "TC_M"])
    draw_section("8. Auto-entrepreneur", h_std, ["AE_D", "AE_V", "AE_B", "AE_N", "AE_A", "AE_F", "AE_1", "AE_9", "AE_E", "AE_D", "AE_R", "AE_M"])
    draw_section("9. Suivi & Rappels", ["Appels", "NESDA", "Terrain", "R_27k", "R_40k", "R_100k", "R_400k", "R_1M"], ["TEL_A", "NE_T", "ST_T", "R_27", "R_40", "R_100", "R_400", "R_1M"])

    # NOUVELLE SECTION : LISTE DES PROMOTEURS CONTACTÉS
    if list_promoteurs is not None and not list_promoteurs.empty:
        pdf.ln(5)
        pdf.set_fill_color(200, 220, 255)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(190, 8, "DÉTAIL DES PROMOTEURS CONTACTÉS PAR TÉLÉPHONE", 1, 1, 'C', True)
        pdf.set_font('Arial', 'B', 8)
        cols = ["Nom & Prénom", "Activité", "Type Financement", "Téléphone"]
        widths = [55, 50, 45, 40]
        for i, c in enumerate(cols): pdf.cell(widths[i], 7, c, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        for _, row in list_promoteurs.iterrows():
            if any(row.values): # N'afficher que les lignes remplies
                pdf.cell(55, 7, str(row[0]), 1, 0, 'L')
                pdf.cell(50, 7, str(row[1]), 1, 0, 'L')
                pdf.cell(45, 7, str(row[2]), 1, 0, 'C')
                pdf.cell(40, 7, str(row[3]), 1, 0, 'C')
                pdf.ln()
    
    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION (Inchangée) ---
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

# --- 5. ESPACE ADMIN (Inchangé) ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration Centrale")
    t1, t2, t3 = st.tabs(["Base de Données", "Téléchargements PDF", "Codes"])
    client = get_gsheet_client()
    sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
    ws = sh.worksheet("SAISIE_BRUTE")
    df = pd.DataFrame(ws.get_all_values()[1:], columns=[h if h!="" else f"V_{i}" for i,h in enumerate(ws.get_all_values()[0])]) if len(ws.get_all_values())>1 else pd.DataFrame()

    with t2:
        if not df.empty:
            m_sel = st.selectbox("Mois pour cumul", df['Mois'].unique())
            if st.button("Générer le PDF de synthèse"):
                df_f = df[df['Mois'] == m_sel].copy()
                cols = [c for c in df_f.columns if c not in ["Accompagnateur", "Mois", "Annee", "Date"]]
                for c in cols: df_f[c] = pd.to_numeric(df_f[c], errors='coerce').fillna(0)
                total_data = {'Accompagnateur': "TOTAL AGENCE", 'Mois': m_sel, 'Annee': 2026, **df_f[cols].sum().to_dict()}
                st.download_button("📥 CUMUL", generate_pdf(total_data), f"Total_{m_sel}.pdf")
    st.stop()

# --- 6. FORMULAIRE ACCOMPAGNATEUR ---
st.title(f"Bilan : {st.session_state.user}")
m_s = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
data = {"Accompagnateur": st.session_state.user, "Mois": m_s, "Annee": 2026, "Date": datetime.now().strftime("%d/%m/%Y")}

def ui_sec(label, p, kp):
    st.subheader(label); c1,c2,c3,c4,c5 = st.columns(5)
    data[f"{p}_D"]=c1.number_input("Dép.", key=f"{kp}1"); data[f"{p}_V"]=c2.number_input("Val.", key=f"{kp}2")
    data[f"{p}_B"]=c3.number_input("Bq", key=f"{kp}3"); data[f"{p}_N"]=c4.number_input("Notif", key=f"{kp}4")
    data[f"{p}_A"]=c5.number_input("AR", key=f"{kp}5")
    c6,c7,c8,c9 = st.columns(4)
    data[f"{p}_F"]=c6.number_input("Fin.", key=f"{kp}6"); data[f"{p}_1"]=c7.number_input("10%", key=f"{kp}7")
    data[f"{p}_9"]=c8.number_input("90%", key=f"{kp}8"); data[f"{p}_E"]=c9.number_input("Exist", key=f"{kp}9")
    c10,c11,c12 = st.columns(3)
    data[f"{p}_D"]=c10.number_input("Dém.", key=f"{kp}10"); data[f"{p}_R"]=c11.number_input("Reçus", key=f"{kp}11"); data[f"{p}_M"]=c12.number_input("Montant", key=f"{kp}12")

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "Suivi & Rappels"])
with tabs[6]:
    st.subheader("9. Suivi & Rappels")
    data["TEL_A"] = st.number_input("Total Appels effectués", key="tel1")
    data["NE_T"]=st.number_input("NESDA", key="n1"); data["ST_T"]=st.number_input("Terrain", key="n2")
    r=st.columns(5); data["R_27"]=r[0].number_input("27k", key="r1"); data["R_40"]=r[1].number_input("40k", key="r2"); data["R_100"]=r[2].number_input("100k", key="r3"); data["R_400"]=r[3].number_input("400k", key="r4"); data["R_1M"]=r[4].number_input("1M", key="r5")
    
    st.markdown("---")
    st.subheader("📞 Liste détaillée des promoteurs contactés")
    df_promos = st.data_editor(pd.DataFrame(columns=["Nom & Prénom", "Activité", "Type Financement", "Téléphone"]), num_rows="dynamic")

# Inchangé pour les autres onglets...
with tabs[0]: 
    cx=st.columns(5); data["MP_D"]=cx[0].number_input("Dép.", key="m1"); data["MP_T"]=cx[1].number_input("Tra.", key="m2"); data["MP_V"]=cx[2].number_input("Val.", key="m3"); data["MP_A"]=cx[3].number_input("AR", key="m4"); data["MP_F"]=cx[4].number_input("Fin.", key="m5")
    data["MP_R"]=st.number_input("Reçus", key="m6"); data["MP_M"]=st.number_input("Montant", key="m7")
with tabs[1]: ui_sec("2. Triangulaire", "TR", "tri")
with tabs[2]: ui_sec("5. Algérie Télécom", "AT", "atl")
with tabs[3]: ui_sec("6. Recyclage", "RE", "rec")
with tabs[4]: ui_sec("7. Tricycle", "TC", "trc")
with tabs[5]: ui_sec("8. Auto-entrepreneur", "AE", "aen")

# --- 7. ACTIONS ---
b1, b2, b3 = st.columns(3)
with b2: st.download_button("📥 TÉLÉCHARGER LE PDF", generate_pdf(data, df_promos), f"Bilan_{st.session_state.user}.pdf")
