import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO", layout="wide")

# --- 2. ACCÈS ---
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

def get_client():
    return gspread.service_account_from_dict({
        "type": st.secrets["type"], "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"], "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"], "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"], "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"]
    })

# --- 3. PDF ---
def generate_pdf(data, promos=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, "C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 8, f"Accompagnateur : {data.get('Accompagnateur')}")
    pdf.cell(90, 8, f"Mois : {data.get('Mois')} 2026", 0, 1, "R")
    
    def box(title, heads, keys):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(190, 7, title, 1, 1, "L", True)
        pdf.set_font("Arial", "B", 5)
        w = 190 / len(heads)
        for h in heads: pdf.cell(w, 5, h, 1, 0, "C")
        pdf.ln()
        pdf.set_font("Arial", "", 7)
        for k in keys: pdf.cell(w, 6, str(data.get(k, 0)), 1, 0, "C")
        pdf.ln(8)

    box("1. Matière Première", ["Déposés", "Traités", "Validés", "AR", "Financés", "Reçus", "Montant"], ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])
    h_s = ["Déposés", "Validés", "Banque", "Notif", "AR", "Financés", "10%", "90%", "Exist", "Dém", "Reçus", "Montant"]
    box("2. Triangulaire", h_s, ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    box("5. Algérie Télécom", h_s, ["AT_D", "AT_V", "AT_B", "AT_N", "AT_A", "AT_F", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    box("9. Rappels", ["Appels", "NESDA", "Terrain", "27k", "40k", "100k", "400k", "1M"], ["TEL", "NE", "ST", "R1", "R2", "R3", "R4", "R5"])
    
    return bytes(pdf.output())

# --- 4. AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO")
    role = st.radio("Compte", ["Accompagnateur", "Administrateur"])
    u = st.selectbox("Utilisateur", list(ACCES.keys()) if role == "Accompagnateur" else ["admin"])
    p = st.text_input("Code", type="password")
    if st.button("Connexion"):
        if ACCES.get(u) == p:
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, role
            st.rerun()
    st.stop()

# --- 5. ADMIN ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration")
    if st.button("Calculer Cumul Agence"):
        try:
            ws = get_client().open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM").worksheet("SAISIE_BRUTE")
            df = pd.DataFrame(ws.get_all_values()[1:])
            st.success("Données chargées. Prêt pour le cumul.")
        except: st.error("Erreur GSheet")
    if st.button("Déconnexion"): st.session_state.auth = False; st.rerun()
    st.stop()

# --- 6. FORMULAIRE ---
st.title(f"Bilan : {st.session_state.user}")
m_s = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
data = {"Accompagnateur": st.session_state.user, "Mois": m_s, "Annee": 2026, "Date": datetime.now().strftime("%d/%m/%Y")}

def ui_sec(label, p, kp):
    st.subheader(label); c = st.columns(5)
    data[f"{p}_D"]=c[0].number_input("Déposés", key=f"{kp}1"); data[f"{p}_V"]=c[1].number_input("Validés CEF", key=f"{kp}2")
    data[f"{p}_B"]=c[2].number_input("Transmis Banque", key=f"{kp}3"); data[f"{p}_N"]=c[3].number_input("Notifications", key=f"{kp}4")
    data[f"{p}_A"]=c[4].number_input("Transmis AR", key=f"{kp}5")
    c2 = st.columns(4)
    data[f"{p}_F"]=c2[0].number_input("Financés", key=f"{kp}6"); data[f"{p}_1"]=c2[1].number_input("OE 10%", key=f"{kp}7")
    data[f"{p}_9"]=c2[2].number_input("OE 90%", key=f"{kp}8"); data[f"{p}_E"]=c2[3].number_input("PV Existence", key=f"{kp}9")
    c3 = st.columns(3)
    data[f"{p}_D"]=c3[0].number_input("PV Démarrage", key=f"{kp}10"); data[f"{p}_R"]=c3[1].number_input("Reçus", key=f"{kp}11"); data[f"{p}_M"]=c3[2].number_input("Montant", key=f"{kp}12")

t = st.tabs(["MP", "Triangulaire", "Telecom", "Suivi"])
with t[0]:
    cx=st.columns(5); data["MP_D"]=cx[0].number_input("Dossiers Déposés", key="m1"); data["MP_T"]=cx[1].number_input("Traités", key="m2")
    data["MP_V"]=cx[2].number_input("Validés", key="m3"); data["MP_A"]=cx[3].number_input("AR", key="m4"); data["MP_F"]=cx[4].number_input("Financés", key="m5")
    data["MP_R"]=st.number_input("Nombre de Reçus", key="m6"); data["MP_M"]=st.number_input("Montant Remboursé", key="m7")
with t[1]: ui_sec("2. Triangulaire", "TR", "tri")
with t[2]: ui_sec("5. Algérie Télécom", "AT", "atl")
with t[3]:
    data["TEL"]=st.number_input("Appels", key="tel1"); data["NE"]=st.number_input("NESDA", key="n1"); data["ST"]=st.number_input("Terrain", key="n2")
    r=st.columns(5); data["R1"]=r[0].number_input("27k", key="r1"); data["R2"]=r[1].number_input("40k", key="r2"); data["R3"]=r[2].number_input("100k", key="r3"); data["R4"]=r[3].number_input("400k", key="r4"); data["R5"]=r[4].number_input("1M", key="r5")
    df_p = st.data_editor(pd.DataFrame(columns=["Nom", "Activité", "Financement", "Tel"]), num_rows="dynamic")

st.markdown("---")
b = st.columns(3)
if b[0].button("💾 ENREGISTRER"):
    try:
        get_client().open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM").worksheet("SAISIE_BRUTE").append_row(list(data.values()))
        st.success("✅ OK")
    except: st.error("Erreur Cloud")
b[1].download_button("📥 PDF", generate_pdf(data), f"Bilan_{m_s}.pdf")
b[2].download_button("📊 EXCEL", pd.DataFrame([data]).to_csv().encode('utf-8'), "Bilan.csv")
