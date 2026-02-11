import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Système Officiel", layout="wide", page_icon="🇩🇿")

# --- 2. CONNEXION SÉCURISÉE GOOGLE SHEETS ---
def save_to_gsheet(data_dict):
    try:
        # Utilisation des secrets pour la connexion
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
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
        self.set_font('Arial', 'B', 10)
        self.cell(100, 5, 'Antenne Regionale : Tipaza', 0, 0)
        self.ln(5)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)

def generate_pdf_bytes(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activites mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 10, f"Mois : {data['Mois'].upper()} {data['Annee']}", 0, 1, 'R')
    pdf.ln(5)

    def draw_table(title, headers, keys):
        # Titre de la rubrique avec fond beige
        pdf.set_fill_color(255, 230, 204)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(190, 8, title, 1, 1, 'L', True)
        
        # En-têtes
        pdf.set_font('Arial', 'B', 6)
        width = 190 / len(headers)
        for h in headers:
            pdf.cell(width, 7, h, 1, 0, 'C')
        pdf.ln()
        
        # Données
        pdf.set_font('Arial', '', 8)
        for k in keys:
            val = data.get(k, 0)
            pdf.cell(width, 7, str(val), 1, 0, 'C')
        pdf.ln(10)

    # --- GÉNÉRATION DE TOUS LES TABLEAUX ---
    # 1. Matière Première
    draw_table("1. Formule : Achat de matiere premieres", 
               ["Deposes", "Traites CEF", "Valides CEF", "Trans. AR", "Finances", "Recus Remb", "Montant Remb"],
               ["MP_Dep", "MP_Tra", "MP_Val", "MP_T_AR", "MP_Fin", "MP_Rec", "MP_Mnt"])

    # 2. Triangulaire
    draw_table("2. Formule : Triangulaire", 
               ["Deposes", "Valides", "Trans. Bq", "Notif. Bq", "Trans. AR", "Finances", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"],
               ["TRI_Dep", "TRI_Val", "TRI_T_Bq", "TRI_Not", "TRI_T_AR", "TRI_Fin", "TRI_OE10", "TRI_OE90", "TRI_PV_E", "TRI_PV_D", "TRI_Rec", "TRI_Mnt"])

    # 5. AT
    draw_table("5. Dossiers (Algerie telecom)", 
               ["Deposes", "Valides", "Trans. Bq", "Notif. Bq", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"],
               ["AT_Dep", "AT_Val", "AT_T_Bq", "AT_Not", "AT_OE10", "AT_OE90", "AT_PV_E", "AT_PV_D", "AT_Rec", "AT_Mnt"])

    # 6. Recyclage
    draw_table("6. Dossiers (Recyclage)", 
               ["Deposes", "Valides", "Trans. Bq", "Notif. Bq", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"],
               ["REC_Dep", "REC_Val", "REC_T_Bq", "REC_Not", "REC_OE10", "REC_OE90", "REC_PV_E", "REC_PV_D", "REC_Rec", "REC_Mnt"])

    # 7. Tricycle
    draw_table("7. Dossiers (Tricycle)", 
               ["Deposes", "Valides", "Trans. Bq", "Notif. Bq", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"],
               ["TC_Dep", "TC_Val", "TC_T_Bq", "TC_Not", "TC_OE10", "TC_OE90", "TC_PV_E", "TC_PV_D", "TC_Rec", "TC_Mnt"])

    # 8. Auto-entrepreneur
    draw_table("8. Dossiers (Auto-entrepreneur)", 
               ["Deposes", "Traites", "Valides", "Trans. Bq", "Notif. Bq", "Trans. AR", "Finances", "OE 10%", "OE 90%", "PV Exist", "PV Dem", "Recus", "Montant"],
               ["AE_Dep", "AE_Tra", "AE_Val", "AE_T_Bq", "AE_Not", "AE_T_AR", "AE_Fin", "AE_OE10", "AE_OE90", "AE_PV_E", "AE_PV_D", "AE_Rec", "AE_Mnt"])

    # 9. NESDA / 10. Rappels
    draw_table("9. NESDA / 10. Rappels et Sorties", 
               ["Orientes NESDA", "Sorties Terrain", "Rappel 27k", "Rappel 40k", "Rappel 100k", "Rappel 1M"],
               ["NES_D", "ST_T", "R_27", "R_40", "R_100", "R_1M"])

    return bytes(pdf.output())

# --- 4. AUTHENTIFICATION ---
LISTE_NOMS = ["Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH"]
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ACCES ANGEM PRO")
    u = st.selectbox("Selectionnez votre nom", [""] + LISTE_NOMS)
    p = st.text_input("Code secret", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- 5. FORMULAIRE DEPLIE (84 CASES) ---
st.title(f"Bilan de : {st.session_state.user}")
col_m, col_a = st.columns(2)
mois_sel = col_m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee_sel = col_a.number_input("Année", 2026)

data = {"Accompagnateur": st.session_state.user, "Mois": mois_sel, "Annee": annee_sel, "Date": datetime.now().strftime("%d/%m/%Y")}

tabs = st.tabs(["1. Matière Première", "2. Triangulaire", "3. Algérie Télécom", "4. Recyclage", "5. Tricycle", "6. Auto-Entrepreneur", "7. NESDA / Terrain"])

# Rubrique 1 : MP
with tabs[0]:
    st.subheader("1. Formule : Achat de matière premières")
    c1, c2, c3, c4, c5 = st.columns(5)
    data["MP_Dep"] = c1.number_input("Dossiers déposés (MP)", key="mp1")
    data["MP_Tra"] = c2.number_input("Traités CEF (MP)", key="mp2")
    data["MP_Val"] = c3.number_input("Validés CEF (MP)", key="mp3")
    data["MP_T_AR"] = c4.number_input("Transmis AR (MP)", key="mp4")
    data["MP_Fin"] = c5.number_input("Financés (MP)", key="mp5")
    c6, c7 = st.columns(2)
    data["MP_Rec"] = c6.number_input("Nombre reçus remb. (MP)", key="mp6")
    data["MP_Mnt"] = c7.number_input("Montant remboursé (MP)", key="mp7")

# Fonction pour les rubriques standard (Tri, AT, REC, TC)
def render_full_tab(label, p, key_pref):
    st.subheader(label)
    cols1 = st.columns(5)
    data[f"{p}_Dep"] = cols1[0].number_input(f"Déposés ({p})", key=f"{key_pref}1")
    data[f"{p}_Val"] = cols1[1].number_input(f"Validés CEF ({p})", key=f"{key_pref}2")
    data[f"{p}_T_Bq"] = cols1[2].number_input(f"Transmis Banque ({p})", key=f"{key_pref}3")
    data[f"{p}_Not"] = cols1[3].number_input(f"Notifications Bq ({p})", key=f"{key_pref}4")
    data[f"{p}_T_AR"] = cols1[4].number_input(f"Transmis AR ({p})", key=f"{key_pref}5")
    cols2 = st.columns(4)
    data[f"{p}_Fin"] = cols2[0].number_input(f"Financés ({p})", key=f"{key_pref}6")
    data[f"{p}_OE10"] = cols2[1].number_input(f"OE 10% ({p})", key=f"{key_pref}7")
    data[f"{p}_OE90"] = cols2[2].number_input(f"OE 90% ({p})", key=f"{key_pref}8")
    data[f"{p}_PV_E"] = cols2[3].number_input(f"PV Existence ({p})", key=f"{key_pref}9")
    cols3 = st.columns(3)
    data[f"{p}_PV_D"] = cols3[0].number_input(f"PV Démarrage ({p})", key=f"{key_pref}10")
    data[f"{p}_Rec"] = cols3[1].number_input(f"Nbrs Reçus ({p})", key=f"{key_pref}11")
    data[f"{p}_Mnt"] = cols3[2].number_input(f"Montant Remb. ({p})", key=f"{key_pref}12")

with tabs[1]: render_full_tab("2. Formule : Triangulaire", "TRI", "tr")
with tabs[2]: render_full_tab("5. Dossiers (Algérie télécom)", "AT", "at")
with tabs[3]: render_full_tab("6. Dossiers (Recyclage)", "REC", "re")
with tabs[4]: render_full_tab("7. Dossiers (Tricycle)", "TC", "tc")

# Rubrique 8 : AE
with tabs[5]:
    st.subheader("8. Dossiers (Auto-entrepreneur)")
    render_full_tab("Auto-entrepreneur Détails", "AE", "ae")
    data["AE_Tra"] = st.number_input("Traités CEF (AE)", key="ae_spec")

# Rubrique 9 & 10 : NESDA / Terrain / Rappels
with tabs[6]:
    st.subheader("9. NESDA / 10. Rappels & Terrain")
    n1, n2 = st.columns(2)
    data["NES_D"] = n1.number_input("Dossiers orientés NESDA", key="n1")
    data["ST_T"] = n2.number_input("Sorties sur terrain", key="n2")
    r1, r2, r3, r4 = st.columns(4)
    data["R_27"] = r1.number_input("Rappel 27 000 DA", key="r1")
    data["R_40"] = r2.number_input("Rappel 40 000 DA", key="r2")
    data["R_100"] = r3.number_input("Rappel 100 000 DA", key="r3")
    data["R_1M"] = r4.number_input("Rappel 1 000 000 DA", key="r4")

st.markdown("---")

# --- 6. ACTIONS SEPAREES ---
btn_save, btn_pdf, btn_excel = st.columns(3)

with btn_save:
    if st.button("💾 ENREGISTRER DANS LA BASE", type="primary", use_container_width=True):
        if save_to_gsheet(data): st.success("✅ Données sauvegardées !")

with btn_pdf:
    pdf_out = generate_pdf_bytes(data)
    st.download_button("📥 TELECHARGER LE RAPPORT PDF", data=pdf_out, file_name=f"Bilan_{mois_sel}.pdf", mime="application/pdf", use_container_width=True)

with btn_excel:
    df_export = pd.DataFrame([data])
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False)
    st.download_button("📊 EXPORTER VERS EXCEL", data=excel_io.getvalue(), file_name=f"Bilan_{mois_sel}.xlsx", use_container_width=True)
