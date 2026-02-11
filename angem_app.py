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

# --- 3. GÉNÉRATEUR PDF (TOUTES LES RUBRIQUES) ---
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
    pdf.cell(190, 8, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
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

    # Affichage de TOUTES les rubriques dans le PDF
    draw_section("1.Formule : Achat de matière premières", ["Dép.", "Traités", "Validés", "T. AR", "Financés", "Reçus", "Mnt"], ["MP_D", "MP_T", "MP_V", "MP_AR", "MP_F", "MP_R", "MP_M"])
    draw_section("2.Formule : Triangulaire", ["Dép.", "Val.", "T. Bq", "Notif.", "T. AR", "Fin.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    draw_section("5. Algérie Télécom", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["AT_D", "AT_V", "AT_B", "AT_N", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    draw_section("6. Recyclage", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["RE_D", "RE_V", "RE_B", "RE_N", "RE_1", "RE_9", "RE_E", "RE_D", "RE_R", "RE_M"])
    draw_section("9. NESDA / 10. Rappels", ["NESDA", "Terrain", "R.27k", "R.40k", "R.100k", "R.400k", "R.1M"], ["NE_T", "ST_T", "R_27", "R_40", "R_100", "R_400", "R_1M"])

    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION & LISTE COMPLETE ---
LISTE_ACCOMPAGNATEURS = [
    "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", 
    "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", 
    "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", 
    "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", 
    "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEJDOUB AMEL", 
    "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", 
    "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"
]

if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCÈS ANGEM PRO")
    role = st.radio("Type de compte", ["Accompagnateur", "Administrateur"])
    u = st.selectbox("Utilisateur", LISTE_ACCOMPAGNATEURS if role == "Accompagnateur" else ["admin"])
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if (role == "Administrateur" and p == "admin123") or (role == "Accompagnateur" and p == "1234"):
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, role
            st.rerun()
    st.stop()

# --- 5. ESPACE ADMIN (CORRECTION GSPREAD ERROR) ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration")
    if st.button("🔄 Charger les données"):
        try:
            client = get_gsheet_client()
            sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
            ws = sh.worksheet("SAISIE_BRUTE")
            data_records = ws.get_all_records()
            if not data_records:
                st.warning("La base de données est vide.")
            else:
                st.dataframe(pd.DataFrame(data_records))
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()
    st.stop()

# --- 6. FORMULAIRE (86 CASES) ---
st.title(f"Bilan : {st.session_state.user}")
col1, col2 = st.columns(2)
mois_sel = col1.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = col2.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

def render_section(label, p, kp):
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

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "Rappels/Terrain"])

with tabs[0]:
    st.subheader("1. Matière Première")
    cx = st.columns(5)
    data["MP_D"] = cx[0].number_input("Déposés", key="m1")
    data["MP_T"] = cx[1].number_input("Traités CEF", key="m2")
    data["MP_V"] = cx[2].number_input("Validés CEF", key="m3")
    data["MP_AR"] = cx[3].number_input("Trans. AR", key="m4")
    data["MP_F"] = cx[4].number_input("Financés", key="m5")
    data["MP_R"] = st.number_input("Reçus Remb.", key="m6")
    data["MP_M"] = st.number_input("Montant Remb.", key="m7")

with tabs[1]: render_section("2. Triangulaire", "TR", "tri")
with tabs[2]: render_section("5. Algérie Télécom", "AT", "atl")
with tabs[3]: render_section("6. Recyclage", "RE", "rec")
with tabs[4]: render_section("7. Tricycle", "TC", "tric")
with tabs[5]: render_section("8. Auto-entrepreneur", "AE", "aen")

with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels")
    data["NE_T"] = st.number_input("NESDA", key="n1")
    data["ST_T"] = st.number_input("Sorties terrain", key="n2")
    r = st.columns(5)
    data["R_27"] = r[0].number_input("R. 27k", key="r1"); data["R_40"] = r[1].number_input("R. 40k", key="r2")
    data["R_100"] = r[2].number_input("R. 100k", key="r3"); data["R_400"] = r[3].number_input("R. 400k", key="r4")
    data["R_1M"] = r[4].number_input("R. 1M", key="r5")

st.markdown("---")
# --- 7. ACTIONS (SÉPARÉES) ---
c_save, c_pdf, c_excel = st.columns(3)

with c_save:
    if st.button("💾 ENREGISTRER", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Données sauvegardées !")

with c_pdf:
    st.download_button("📥 PDF", data=generate_pdf_bytes(data), file_name=f"Bilan_{st.session_state.user}.pdf", mime="application/pdf", use_container_width=True)

with c_excel:
    df_ex = pd.DataFrame([data])
    io_ex = io.BytesIO()
    with pd.ExcelWriter(io_ex, engine='xlsxwriter') as wr:
        df_ex.to_excel(wr, index=False)
    st.download_button("📊 EXCEL", data=io_ex.getvalue(), file_name=f"Bilan.xlsx", use_container_width=True)
