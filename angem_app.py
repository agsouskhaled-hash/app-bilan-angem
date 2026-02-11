import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE GOOGLE SHEETS ---
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

# --- 3. GÉNÉRATEUR PDF (MIROIR INTÉGRAL DE L'EXCEL) ---
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

    # Exportation de TOUTES les rubriques sans exception
    draw_section("1.Formule : Achat de matière premières", ["Dép.", "Traités", "Validés", "T. AR", "Financés", "Reçus", "Montant"], ["MP_Dép", "MP_Tra", "MP_Val", "MP_TAR", "MP_Fin", "MP_Rec", "MP_Mnt"])
    draw_section("2.Formule : Triangulaire", ["Dép.", "Val.", "T. Bq", "Notif.", "T. AR", "Fin.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["TR_Dép", "TR_Val", "TR_TBq", "TR_Not", "TR_TAR", "TR_Fin", "TR_O10", "TR_O90", "TR_PVE", "TR_PVD", "TR_Rec", "TR_Mnt"])
    draw_section("5. Algérie Télécom", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["AT_Dép", "AT_Val", "AT_TBq", "AT_Not", "AT_O10", "AT_O90", "AT_PVE", "AT_PVD", "AT_Rec", "AT_Mnt"])
    draw_section("6. Recyclage", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["RE_Dép", "RE_Val", "RE_TBq", "RE_Not", "RE_O10", "RE_O90", "RE_PVE", "RE_PVD", "RE_Rec", "RE_Mnt"])
    draw_section("7. Tricycle", ["Dép.", "Val.", "T. Bq", "Notif.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["TC_Dép", "TC_Val", "TC_TBq", "TC_Not", "TC_O10", "TC_O90", "TC_PVE", "TC_PVD", "TC_Rec", "TC_Mnt"])
    draw_section("8. Auto-entrepreneur", ["Dép.", "Tra.", "Val.", "T. Bq", "Notif.", "T. AR", "Fin.", "OE10", "OE90", "PV.E", "PV.D", "Reçus", "Mnt"], ["AE_Dép", "AE_Tra", "AE_Val", "AE_TBq", "AE_Not", "AE_TAR", "AE_Fin", "AE_O10", "AE_O90", "AE_PVE", "AE_PVD", "AE_Rec", "AE_Mnt"])
    draw_section("9. NESDA / 10. Rappels", ["NESDA", "Terrain", "R.27k", "R.40k", "R.100k", "R.400k", "R.1M"], ["NE_Tot", "ST_Tot", "R_27", "R_40", "R_100", "R_400", "R_1M"])

    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION (ADMIN + ACCOMPAGNATEURS) ---
LISTE_NOMS = ["Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCÈS ANGEM PRO")
    role = st.radio("Type de compte", ["Accompagnateur", "Administrateur"])
    u = st.selectbox("Utilisateur", LISTE_NOMS if role == "Accompagnateur" else ["admin"])
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if (role == "Administrateur" and p == "admin123") or (role == "Accompagnateur" and p == "1234"):
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, role
            st.rerun()
    st.stop()

# --- 5. ESPACE ADMINISTRATEUR ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration - Vue Globale")
    if st.button("🔄 Charger toutes les données"):
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        df = pd.DataFrame(sh.worksheet("SAISIE_BRUTE").get_all_records())
        st.dataframe(df)
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()
    st.stop()

# --- 6. ESPACE ACCOMPAGNATEUR (86 CASES) ---
st.title(f"Bilan de : {st.session_state.user}")
m, a = st.columns(2)
mois_sel = m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

def render_section(label, p, kp):
    st.subheader(label)
    c = st.columns(5)
    data[f"{p}_Dép"] = c[0].number_input(f"Déposés ({p})", key=f"{kp}1")
    data[f"{p}_Val"] = c[1].number_input(f"Validés CEF ({p})", key=f"{kp}2")
    data[f"{p}_TBq"] = c[2].number_input(f"Transmis Banque ({p})", key=f"{kp}3")
    data[f"{p}_Not"] = c[3].number_input(f"Notif. Banque ({p})", key=f"{kp}4")
    data[f"{p}_TAR"] = c[4].number_input(f"Transmis AR ({p})", key=f"{kp}5")
    c2 = st.columns(4)
    data[f"{p}_Fin"] = c2[0].number_input(f"Financés ({p})", key=f"{kp}6")
    data[f"{p}_O10"] = c2[1].number_input(f"Ordre Enl. 10% ({p})", key=f"{kp}7")
    data[f"{p}_O90"] = c2[2].number_input(f"Ordre Enl. 90% ({p})", key=f"{kp}8")
    data[f"{p}_PVE"] = c2[3].number_input(f"PV Existence ({p})", key=f"{kp}9")
    c3 = st.columns(3)
    data[f"{p}_PVD"] = c3[0].number_input(f"PV Démarrage ({p})", key=f"{kp}10")
    data[f"{p}_Rec"] = c3[1].number_input(f"Nbrs Reçus ({p})", key=f"{kp}11")
    data[f"{p}_Mnt"] = c3[2].number_input(f"Montant Remb. ({p})", key=f"{kp}12")

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "NESDA/Terrain"])

with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    cx = st.columns(5)
    data["MP_Dép"] = cx[0].number_input("Déposés (MP)", key="m1")
    data["MP_Tra"] = cx[1].number_input("Traités CEF (MP)", key="m2")
    data["MP_Val"] = cx[2].number_input("Validés CEF (MP)", key="m3")
    data["MP_TAR"] = cx[3].number_input("Transmis AR (MP)", key="m4")
    data["MP_Fin"] = cx[4].number_input("Financés (MP)", key="m5")
    data["MP_Rec"] = st.number_input("Nbrs Reçus Remb. (MP)", key="m6")
    data["MP_Mnt"] = st.number_input("Montant Remboursé (MP)", key="m7")

with tabs[1]: render_section("2. Triangulaire", "TR", "tri")
with tabs[2]: render_section("5. Algérie Télécom", "AT", "atl")
with tabs[3]: render_section("6. Recyclage", "RE", "rec")
with tabs[4]: render_section("7. Tricycle", "TC", "tric")
with tabs[5]: render_section("8. Auto-entrepreneur", "AE", "aen"); data["AE_Tra"] = st.number_input("Traités CEF (AE)", key="aet")

with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels & Terrain")
    data["NE_Tot"] = st.number_input("NESDA", key="nes")
    data["ST_Tot"] = st.number_input("Sorties terrain", key="st")
    r = st.columns(5)
    data["R_27"] = r[0].number_input("R. 27k", key="r1"); data["R_40"] = r[1].number_input("R. 40k", key="r2")
    data["R_100"] = r[2].number_input("R. 100k", key="r3"); data["R_400"] = r[3].number_input("R. 400k", key="r4")
    data["R_1M"] = r[4].number_input("R. 1M", key="r5")

st.markdown("---")
# --- 7. ACTIONS (BOUTONS SÉPARÉS) ---
col_save, col_pdf, col_excel = st.columns(3)

with col_save:
    if st.button("💾 ENREGISTRER DANS LA BASE", type="primary", use_container_width=True):
        client = get_gsheet_client()
        sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
        sh.worksheet("SAISIE_BRUTE").append_row(list(data.values()))
        st.success("✅ Données sauvegardées !")

with col_pdf:
    pdf_bytes = generate_pdf_bytes(data)
    st.download_button("📥 TÉLÉCHARGER LE PDF COMPLET", data=pdf_bytes, file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)

with col_excel:
    df_x = pd.DataFrame([data])
    io_x = io.BytesIO()
    with pd.ExcelWriter(io_x, engine='xlsxwriter') as wr:
        df_x.to_excel(wr, index=False)
    st.download_button("📊 EXPORTER VERS EXCEL", data=io_x.getvalue(), file_name=f"Bilan.xlsx", use_container_width=True)
