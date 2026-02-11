import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Code Principal Officiel", layout="wide", page_icon="🇩🇿")

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

# --- 3. GESTION DES CODES D'ACCÈS ---
CODES_ACCES = {
    "admin": "admin123",
    "Mme GUESSMIA ZAHIRA": "1234", "M. BOULAHLIB REDOUANE": "1234", "Mme DJAOUDI SARAH": "1234",
    "Mme BEN SAHNOUN LILA": "1234", "Mme NASRI RIM": "1234", "Mme MECHALIKHE FATMA": "1234",
    "Mlle SALMI NOUR EL HOUDA": "1234", "M. BERRABEH DOUADI": "1234", "Mme BELAID FAZIA": "1234",
    "M. METMAR OMAR": "1234", "Mme AIT OUARAB AMINA": "1234", "Mme MILOUDI AMEL": "1234",
    "Mme BERROUANE SAMIRA": "1234", "M. MAHREZ MOHAMED": "1234", "Mlle FELFOUL SAMIRA": "1234",
    "Mlle MEDJHOUM RAOUIA": "1234", "Mme SAHNOUNE IMENE": "1234", "Mme KHERIF FADILA": "1234",
    "Mme MERAKEB FAIZA": "1234", "Mme MEJDOUB AMEL": "1234", "Mme BEN AICHE MOUNIRA": "1234",
    "Mme SEKAT MANEL FATIMA": "1234", "Mme KADRI SIHEM": "1234", "Mme TOUAKNI SARAH": "1234",
    "Mme MAASSOUM EPS LAKHDARI SAIDA": "1234", "M. TALAMALI IMAD": "1234", "Mme BOUCHAREB MOUNIA": "1234"
}

# --- 4. GÉNÉRATEUR PDF (TOUTES RUBRIQUES) ---
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

    def draw_section(title, headers, keys):
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        pdf.set_font('Arial', 'B', 6)
        w = 190 / len(headers)
        for h in headers: pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 7)
        for k in keys: pdf.cell(w, 7, str(data.get(k, 0)), 1, 0, 'C')
        pdf.ln(8)

    # Affichage de TOUTES les rubriques
    draw_section("1.Formule : Achat de matière premières", ["Dép.", "Traités", "Validés", "T. AR", "Fin.", "Reçus", "Mnt"], ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])
    draw_section("2.Formule : Triangulaire", ["Dép.", "Val.", "T. Bq", "Notif.", "T. AR", "Fin.", "OE10", "OE90", "PV.E", "PV.D", "Rec", "Mnt"], ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    draw_section("5. Algérie Télécom", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Rec", "Mnt"], ["AT_D", "AT_V", "AT_B", "AT_N", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    draw_section("6. Recyclage", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Rec", "Mnt"], ["RE_D", "RE_V", "RE_B", "RE_N", "RE_1", "RE_9", "RE_E", "RE_D", "RE_R", "RE_M"])
    draw_section("7. Tricycle", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Rec", "Mnt"], ["TC_D", "TC_V", "TC_B", "TC_N", "TC_1", "TC_9", "TC_E", "TC_D", "TC_R", "TC_M"])
    draw_section("8. Auto-entrepreneur", ["Dép.", "Tra.", "Val.", "T. Bq", "Notif.", "T. AR", "Fin.", "OE10", "OE90", "PV.E", "PV.D", "Rec", "Mnt"], ["AE_D", "AE_T", "AE_V", "AE_B", "AE_N", "AE_A", "AE_F", "AE_1", "AE_9", "AE_E", "AE_D", "AE_R", "AE_M"])
    draw_section("9. NESDA / 10. Rappels", ["NESDA", "Terrain", "R.27k", "R.40k", "R.100k", "R.400k", "R.1M"], ["NE_T", "ST_T", "R_27", "R_40", "R_100", "R_400", "R_1M"])

    return bytes(pdf.output())

# --- 5. AUTHENTIFICATION ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCÈS ANGEM PRO")
    role = st.radio("Type de compte", ["Accompagnateur", "Administrateur"])
    u = st.selectbox("Utilisateur", list(CODES_ACCES.keys()) if role == "Accompagnateur" else ["admin"])
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if CODES_ACCES.get(u) == p:
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, role
            st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# --- 6. ESPACE ADMIN ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration")
    t1, t2 = st.tabs(["Données", "Codes d'accès"])
    with t1:
        if st.button("🔄 Charger les données"):
            try:
                client = get_gsheet_client()
                sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
                all_v = sh.worksheet("SAISIE_BRUTE").get_all_values()
                if len(all_v) > 1: st.dataframe(pd.DataFrame(all_v[1:], columns=all_v[0]))
                else: st.warning("Base vide")
            except Exception as e: st.error(f"Erreur : {e}")
    with t2:
        st.table(pd.DataFrame(list(CODES_ACCES.items()), columns=["Nom", "Code"]))
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()
    st.stop()

# --- 7. FORMULAIRE ACCOMPAGNATEUR ---
st.title(f"Bilan : {st.session_state.user}")
m, a = st.columns(2)
mois_sel = m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

def full_sec(label, p, kp):
    st.subheader(label)
    c = st.columns(5)
    data[f"{p}_D"] = c[0].number_input(f"Déposés ({p})", key=f"{kp}1")
    data[f"{p}_V"] = c[1].number_input(f"Validés CEF ({p})", key=f"{kp}2")
    data[f"{p}_B"] = c[2].number_input(f"Trans. Banque ({p})", key=f"{kp}3")
    data[f"{p}_N"] = c[3].number_input(f"Notif. Banque ({p})", key=f"{kp}4")
    data[f"{p}_A"] = c[4].number_input(f"Trans. AR ({p})", key=f"{kp}5")
    c2 = st.columns(4)
    data[f"{p}_F"] = c2[0].number_input(f"Financés ({p})", key=f"{kp}6")
    data[f"{p}_1"] = c2[1].number_input(f"OE 10% ({p})", key=f"{kp}7")
    data[f"{p}_9"] = c2[2].number_input(f"OE 90% ({p})", key=f"{kp}8")
    data[f"{p}_E"] = c2[3].number_input(f"PV Existence ({p})", key=f"{kp}9")
    c3 = st.columns(3)
    data[f"{p}_D"] = c3[0].number_input(f"PV Démarrage ({p})", key=f"{kp}10")
    data[f"{p}_R"] = c3[1].number_input(f"Reçus ({p})", key=f"{kp}11")
    data[f"{p}_M"] = c3[2].number_input(f"Montant ({p})", key=f"{kp}12")

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "Terrain/Rappels"])

with tabs[0]:
    st.subheader("1. Matière Première")
    cx = st.columns(5)
    data["MP_D"] = cx[0].number_input("Déposés", key="m1")
    data["MP_T"] = cx[1].number_input("Traités CEF", key="m2")
    data["MP_V"] = cx[2].number_input("Validés CEF", key="m3")
    data["MP_A"] = cx[3].number_input("Trans. AR", key="m4")
    data["MP_F"] = cx[4].number_input("Financés", key="m5")
    data["MP_R"] = st.number_input("Reçus", key="m6")
    data["MP_M"] = st.number_input("Montant", key="m7")

with tabs[1]: full_sec("2. Triangulaire", "TR", "tri")
with tabs[2]: full_sec("5. Algérie Télécom", "AT", "atl")
with tabs[3]: full_sec("6. Recyclage", "RE", "rec")
with tabs[4]: full_sec("7. Tricycle", "TC", "tri")
with tabs[5]: full_sec("8. Auto-entrepreneur", "AE", "aen"); data["AE_T"] = st.number_input("Traités CEF (AE)", key="aet")

with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels")
    data["NE_T"] = st.number_input("NESDA", key="n1")
    data["ST_T"] = st.number_input("Sorties terrain", key="n2")
    r = st.columns(5)
    data["R_27"] = r[0].number_input("R. 27k", key="r1"); data["R_40"] = r[1].number_input("R. 40k", key="r2")
    data["R_100"] = r[2].number_input("R. 100k", key="r3"); data["R_400"] = r[3].number_input("R. 400k", key="r4")
    data["R_1M"] = r[4].number_input("R. 1M", key="r5")

st.markdown("---")
# --- 8. ACTIONS ---
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("💾 ENREGISTRER", type="primary", use_container_width=True):
        try:
            get_gsheet_client().open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM").worksheet("SAISIE_BRUTE").append_row(list(data.values()))
            st.success("✅ Enregistré !")
        except Exception as e: st.error(f"Erreur : {e}")
with b2:
    st.download_button("📥 PDF COMPLET", data=generate_pdf_bytes(data), file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)
with b3:
    df_ex = pd.DataFrame([data])
    io_ex = io.BytesIO()
    with pd.ExcelWriter(io_ex, engine='xlsxwriter') as wr: df_ex.to_excel(wr, index=False)
    st.download_button("📊 EXCEL", data=io_ex.getvalue(), file_name=f"Bilan.xlsx", use_container_width=True)
