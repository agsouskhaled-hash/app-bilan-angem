import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

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

# --- 3. GÉNÉRATEUR PDF (NOMS COMPLETS) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 9)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(4)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf(data, title_prefix="Rapport"):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, f"{title_prefix} d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, f"Mois : {str(data.get('Mois', '')).upper()} {data.get('Annee', '')}", 0, 1, 'R')
    pdf.ln(5)

    def draw_section(title, headers, keys):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 5.5) # Police plus petite pour les noms longs
        w = 190 / len(headers)
        for h in headers: pdf.multi_cell(w, 4, h, 1, 'C', 0)
        # Re-ajustement après multi_cell pour les données
        y_before = pdf.get_y()
        pdf.set_xy(10, y_before - 4) # On remonte pour aligner la ligne de données
        pdf.set_font('Arial', '', 7)
        for k in keys: pdf.cell(w, 7, str(data.get(k, 0)), 1, 0, 'C')
        pdf.ln(12)

    # --- RUBRIQUES AVEC NOMS COMPLETS ---
    h_mp = ["Dossiers déposés", "Traités par CEF", "Validés par CEF", "Transmis AR", "Dossiers Financés", "Reçus Rembours.", "Montant Remboursé"]
    draw_section("1. Formule : Achat de matière premières", h_mp, ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])

    h_tr = ["Déposés", "Validés CEF", "Trans. Banque", "Notif. Banque", "Trans. AR", "Financés", "Ordre 10%", "Ordre 90%", "PV Existence", "PV Démarrage", "Reçus Remb.", "Montant Remb."]
    draw_section("2. Formule : Triangulaire", h_tr, ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])

    draw_section("5. Algérie Télécom", h_tr, ["AT_D", "AT_V", "AT_B", "AT_N", "AT_A", "AT_F", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    
    h_rap = ["NESDA", "Terrain", "Rappel 27k", "Rappel 40k", "Rappel 100k", "Rappel 400k", "Rappel 1M"]
    draw_section("9. NESDA / 10. Rappels", h_rap, ["NE_T", "ST_T", "R_27", "R_40", "R_100", "R_400", "R_1M"])
    
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

# --- 5. ESPACE ADMIN (CUMUL ET INDIVIDUEL) ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration Centrale")
    t1, t2, t3 = st.tabs(["Données", "Téléchargements PDF", "Codes"])
    
    try:
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        all_v = sh.worksheet("SAISIE_BRUTE").get_all_values()
        if len(all_v) > 1:
            headers = [h if h != "" else f"VIDE_{i}" for i, h in enumerate(all_v[0])]
            df = pd.DataFrame(all_v[1:], columns=headers)
        else: df = pd.DataFrame()
    except: df = pd.DataFrame()

    with t1: st.dataframe(df)
    with t2:
        if not df.empty:
            idx = st.selectbox("Choisir une saisie", df.index, format_func=lambda x: f"{df.loc[x, 'Accompagnateur']} - {df.loc[x, 'Mois']}")
            st.download_button("📥 PDF Individuel", generate_pdf(df.loc[idx].to_dict()), f"Bilan_{df.loc[idx, 'Accompagnateur']}.pdf")
            st.markdown("---")
            m_sel = st.selectbox("Mois pour cumul", df['Mois'].unique())
            if st.button("Calculer le Total Agence"):
                df_f = df[df['Mois'] == m_sel].copy()
                for col in df_f.columns:
                    if col not in ["Accompagnateur", "Mois", "Annee", "Date"]:
                        df_f[col] = pd.to_numeric(df_f[col], errors='coerce').fillna(0)
                total_data = df_f.sum(numeric_only=True).to_dict()
                total_data.update({'Accompagnateur': "TOTAL", 'Mois': m_sel, 'Annee': 2026})
                st.download_button("📥 TÉLÉCHARGER LE CUMUL", generate_pdf(total_data, "TOTAL"), f"Total_{m_sel}.pdf")
    with t3: st.table(pd.DataFrame(list(ACCES.items()), columns=["Nom", "Code"]))
    if st.button("Déconnexion"): st.session_state.auth = False; st.rerun()
    st.stop()

# --- 6. FORMULAIRE ACCOMPAGNATEUR ---
st.title(f"Bilan : {st.session_state.user}")
m_s = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
data = {"Accompagnateur": st.session_state.user, "Mois": m_s, "Annee": 2026, "Date": datetime.now().strftime("%d/%m/%Y")}

def ui_sec(label, p, kp):
    st.subheader(label)
    c1, c2, c3, c4, c5 = st.columns(5)
    data[f"{p}_D"] = c1.number_input(f"Nombre de dossiers déposés", key=f"{kp}1")
    data[f"{p}_V"] = c2.number_input(f"Dossiers validés par CEF", key=f"{kp}2")
    data[f"{p}_B"] = c3.number_input(f"Dossiers transmis à la Banque", key=f"{kp}3")
    data[f"{p}_N"] = c4.number_input(f"Notifications bancaires reçues", key=f"{kp}4")
    data[f"{p}_A"] = c5.number_input(f"Dossiers transmis à l'AR", key=f"{kp}5")
    c6, c7, c8, c9 = st.columns(4)
    data[f"{p}_F"] = c6.number_input(f"Dossiers financés", key=f"{kp}6")
    data[f"{p}_1"] = c7.number_input(f"Ordre d'enlèvement 10%", key=f"{kp}7")
    data[f"{p}_9"] = c8.number_input(f"Ordre d'enlèvement 90%", key=f"{kp}8")
    data[f"{p}_E"] = c9.number_input(f"PV d'Existence", key=f"{kp}9")
    c10, c11, c12 = st.columns(3)
    data[f"{p}_D"] = c10.number_input(f"PV de Démarrage", key=f"{kp}10")
    data[f"{p}_R"] = c11.number_input(f"Nombre de reçus", key=f"{kp}11")
    data[f"{p}_M"] = c12.number_input(f"Montant remboursé (DA)", key=f"{kp}12")

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "Rappels"])
with tabs[0]:
    st.subheader("1. Matière Première")
    cx = st.columns(5)
    data["MP_D"]=cx[0].number_input("Dossiers déposés", key="m1"); data["MP_T"]=cx[1].number_input("Traités CEF", key="m2"); data["MP_V"]=cx[2].number_input("Validés CEF", key="m3"); data["MP_A"]=cx[3].number_input("Transmis AR", key="m4"); data["MP_F"]=cx[4].number_input("Financés", key="m5")
    data["MP_R"]=st.number_input("Nombre de reçus de remboursement", key="m6"); data["MP_M"]=st.number_input("Montant total remboursé (DA)", key="m7")

with tabs[1]: ui_sec("2. Formule Triangulaire", "TR", "tri")
with tabs[2]: ui_sec("5. Algérie Télécom", "AT", "atl")
with tabs[3]: ui_sec("6. Recyclage", "RE", "rec")
with tabs[4]: ui_sec("7. Tricycle", "TC", "trc")
with tabs[5]: ui_sec("8. Auto-entrepreneur", "AE", "aen")
with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels")
    data["NE_T"]=st.number_input("Dossiers orientés NESDA", key="n1"); data["ST_T"]=st.number_input("Sorties terrain", key="n2")
    r=st.columns(5); data["R_27"]=r[0].number_input("Rappel 27k", key="r1"); data["R_40"]=r[1].number_input("Rappel 40k", key="r2"); data["R_100"]=r[2].number_input("Rappel 100k", key="r3"); data["R_400"]=r[3].number_input("Rappel 400k", key="r4"); data["R_1M"]=r[4].number_input("Rappel 1M", key="r5")

st.markdown("---")
# --- 7. ACTIONS ---
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("💾 ENREGISTRER"):
        get_gsheet_client().open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM").worksheet("SAISIE_BRUTE").append_row(list(data.values()))
        st.success("✅ Enregistré !")
with b2: st.download_button("📥 PDF COMPLET", generate_pdf(data), f"Bilan_{st.session_state.user}.pdf")
with b3:
    io_x = io.BytesIO()
    with pd.ExcelWriter(io_x, engine='xlsxwriter') as wr: pd.DataFrame([data]).to_excel(wr, index=False)
    st.download_button("📊 EXCEL", io_x.getvalue(), "Bilan.xlsx")
