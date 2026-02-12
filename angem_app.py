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

# --- 3. GÉNÉRATEUR PDF (ALIGNEMENT PARFAIT) ---
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
        
        pdf.set_font('Arial', 'B', 5.5)
        w = 190 / len(headers)
        
        # On mémorise la position Y de départ pour la ligne des titres
        y_start = pdf.get_y()
        max_h = 0
        
        # 1. On dessine les titres et on cherche la hauteur max
        for h in headers:
            curr_y = pdf.get_y()
            pdf.multi_cell(w, 3.5, h, 1, 'C')
            max_h = max(max_h, pdf.get_y() - y_start)
            pdf.set_xy(pdf.get_x() + w, y_start)
        
        # 2. On dessine les données avec un alignement parfait sous les titres
        pdf.set_xy(10, y_start + max_h)
        pdf.set_font('Arial', '', 7)
        for k in keys:
            pdf.cell(w, 7, str(data.get(k, 0)), 1, 0, 'C')
        pdf.ln(12)

    # Sections avec noms complets
    draw_section("1. Formule : Achat de matière premières", 
                 ["Dossiers déposés", "Traités par CEF", "Validés par CEF", "Transmis AR", "Dossiers Financés", "Reçus", "Montant"], 
                 ["MP_D", "MP_T", "MP_V", "MP_A", "MP_F", "MP_R", "MP_M"])

    h_std = ["Déposés", "Validés", "Trans. Bq", "Notif. Bq", "Trans. AR", "Financés", "OE 10%", "OE 90%", "PV Exist", "PV Dém", "Reçus", "Montant"]
    draw_section("2. Formule : Triangulaire", h_std, ["TR_D", "TR_V", "TR_B", "TR_N", "TR_A", "TR_F", "TR_1", "TR_9", "TR_E", "TR_D", "TR_R", "TR_M"])
    draw_section("5. Algérie Télécom", h_std, ["AT_D", "AT_V", "AT_B", "AT_N", "AT_A", "AT_F", "AT_1", "AT_9", "AT_E", "AT_D", "AT_R", "AT_M"])
    draw_section("6. Recyclage", h_std, ["RE_D", "RE_V", "RE_B", "RE_N", "RE_A", "RE_F", "RE_1", "RE_9", "RE_E", "RE_D", "RE_R", "RE_M"])
    draw_section("7. Tricycle", h_std, ["TC_D", "TC_V", "TC_B", "TC_N", "TC_A", "TC_F", "TC_1", "TC_9", "TC_E", "TC_D", "TC_R", "TC_M"])
    draw_section("8. Auto-entrepreneur", h_std, ["AE_D", "AE_V", "AE_B", "AE_N", "AE_A", "AE_F", "AE_1", "AE_9", "AE_E", "AE_D", "AE_R", "AE_M"])
    
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

# --- 5. ESPACE ADMIN (VERSION AVEC SUPPRESSION) ---
if st.session_state.role == "Administrateur":
    st.title("📊 Administration Centrale")
    t1, t2, t3 = st.tabs(["Base de Données", "Téléchargements PDF", "Codes"])
    
    client = get_gsheet_client()
    sh = client.open_by_key("1ktTYrR1U3xxk5QjamVb1kqdHSTjZe9APoLXg_XzYJNM")
    ws = sh.worksheet("SAISIE_BRUTE")
    all_v = ws.get_all_values()
    
    if len(all_v) > 1:
        headers = [h if h != "" else f"VIDE_{i}" for i, h in enumerate(all_v[0])]
        df = pd.DataFrame(all_v[1:], columns=headers)
    else: df = pd.DataFrame()

    with t1:
        st.dataframe(df)
        if not df.empty:
            st.subheader("🗑️ Supprimer un enregistrement")
            del_idx = st.selectbox("Ligne à supprimer", df.index, format_func=lambda x: f"Ligne {x+2}: {df.loc[x,'Accompagnateur']} ({df.loc[x,'Mois']})")
            if st.button("❌ CONFIRMER LA SUPPRESSION", type="secondary"):
                ws.delete_rows(del_idx + 2) # +2 car Sheets commence à 1 et la ligne 1 est le header
                st.success("Enregistrement supprimé. Veuillez rafraîchir la page.")
                st.rerun()

    with t2:
        if not df.empty:
            idx = st.selectbox("Choisir une saisie pour PDF", df.index, format_func=lambda x: f"{df.loc[x, 'Accompagnateur']} - {df.loc[x, 'Mois']}")
            st.download_button(f"📥 PDF de {df.loc[idx, 'Accompagnateur']}", generate_pdf(df.loc[idx].to_dict()), f"Bilan_{df.loc[idx, 'Accompagnateur']}.pdf")
            st.markdown("---")
            m_sel = st.selectbox("Mois pour cumul", df['Mois'].unique() if not df.empty else [""])
            if st.button("Calculer le Total Agence"):
                df_f = df[df['Mois'] == m_sel].copy()
                for col in df_f.columns:
                    if col not in ["Accompagnateur", "Mois", "Annee", "Date"]:
                        df_f[col] = pd.to_numeric(df_f[col], errors='coerce').fillna(0)
                total_data = df_f.sum(numeric_only=True).to_dict()
                total_data.update({'Accompagnateur': "TOTAL", 'Mois': m_sel, 'Annee': 2026})
                st.download_button("📥 TÉLÉCHARGER LE CUMUL GLOBAL", generate_pdf(total_data, "TOTAL"), f"Total_{m_sel}.pdf")
    
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
    data[f"{p}_D"] = c1.number_input(f"Dossiers déposés", key=f"{kp}1")
    data[f"{p}_V"] = c2.number_input(f"Validés CEF", key=f"{kp}2")
    data[f"{p}_B"] = c3.number_input(f"Trans. Banque", key=f"{kp}3")
    data[f"{p}_N"] = c4.number_input(f"Notif. Bq", key=f"{kp}4")
    data[f"{p}_A"] = c5.number_input(f"Transmis AR", key=f"{kp}5")
    c6, c7, c8, c9 = st.columns(4)
    data[f"{p}_F"] = c6.number_input(f"Financés", key=f"{kp}6")
    data[f"{p}_1"] = c7.number_input(f"OE 10%", key=f"{kp}7")
    data[f"{p}_9"] = c8.number_input(f"OE 90%", key=f"{kp}8")
    data[f"{p}_E"] = c9.number_input(f"PV Exist.", key=f"{kp}9")
    c10, c11, c12 = st.columns(3)
    data[f"{p}_D"] = c10.number_input(f"PV Dém.", key=f"{kp}10")
    data[f"{p}_R"] = c11.number_input(f"Reçus", key=f"{kp}11")
    data[f"{p}_M"] = c12.number_input(f"Montant", key=f"{kp}12")

tabs = st.tabs(["MP", "Triangulaire", "Télécom", "Recyclage", "Tricycle", "AE", "Rappels"])
with tabs[0]:
    st.subheader("1. Matière Première")
    cx = st.columns(5)
    data["MP_D"]=cx[0].number_input("Dép.", key="m1"); data["MP_T"]=cx[1].number_input("Tra.", key="m2"); data["MP_V"]=cx[2].number_input("Val.", key="m3"); data["MP_A"]=cx[3].number_input("AR", key="m4"); data["MP_F"]=cx[4].number_input("Fin.", key="m5")
    data["MP_R"]=st.number_input("Reçus", key="m6"); data["MP_M"]=st.number_input("Montant", key="m7")

with tabs[1]: ui_sec("2. Triangulaire", "TR", "tri")
with tabs[2]: ui_sec("5. Algérie Télécom", "AT", "atl")
with tabs[3]: ui_sec("6. Recyclage", "RE", "rec")
with tabs[4]: ui_sec("7. Tricycle", "TC", "trc")
with tabs[5]: ui_sec("8. Auto-entrepreneur", "AE", "aen")
with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels")
    data["NE_T"]=st.number_input("NESDA", key="n1"); data["ST_T"]=st.number_input("Terrain", key="n2")
    r=st.columns(5); data["R_27"]=r[0].number_input("27k", key="r1"); data["R_40"]=r[1].number_input("40k", key="r2"); data["R_100"]=r[2].number_input("100k", key="r3"); data["R_400"]=r[3].number_input("400k", key="r4"); data["R_1M"]=r[4].number_input("1M", key="r5")

st.markdown("---")
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
