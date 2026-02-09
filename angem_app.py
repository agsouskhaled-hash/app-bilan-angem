import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Bilan Officiel", layout="wide", page_icon="🇩🇿")

# --- CONNEXION SÉCURISÉE ---
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

# --- FONCTION GÉNÉRATION PDF OFFICIEL ---
def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # En-tête officiel
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "MINISTERE DE LA SOLIDARITE NATIONALE", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "AGENCE NATIONALE DE GESTION DU MICRO-CREDIT (ANGEM)", ln=True, align="C")
    pdf.cell(190, 10, "AGENCE ALGER OUEST", ln=True, align="C")
    pdf.ln(10)
    
    # Titre du Bilan
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 12, f"BILAN MENSUEL : {data['Mois']} {data['Annee']}", ln=True, align="C", fill=True)
    pdf.ln(5)

    # Infos Accompagnateur
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 10, f"Accompagnateur : {data['Accompagnateur']}", ln=True)
    pdf.cell(190, 10, f"Agence : {data['Agence']}", ln=True)
    pdf.ln(5)

    # Tableau des rubriques
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(80, 10, "Rubriques", 1, 0, "C", True)
    pdf.cell(30, 10, "Deposes", 1, 0, "C", True)
    pdf.cell(30, 10, "Finances", 1, 0, "C", True)
    pdf.cell(50, 10, "Remboursement (DA)", 1, 1, "C", True)

    pdf.set_font("Arial", "", 10)
    # Ligne Matière Première
    pdf.cell(80, 10, "Achat de Matiere Premiere", 1)
    pdf.cell(30, 10, str(data['Matiere_Premiere_Deposes']), 1, 0, "C")
    pdf.cell(30, 10, str(data['Matiere_Premiere_Finances']), 1, 0, "C")
    pdf.cell(50, 10, f"{data['Matiere_Premiere_Montant_Remboursement']}", 1, 1, "C")

    # Ligne Triangulaire
    pdf.cell(80, 10, "Formule Triangulaire", 1)
    pdf.cell(30, 10, str(data['Triangulaire_Deposes']), 1, 0, "C")
    pdf.cell(30, 10, str(data['Triangulaire_Finances']), 1, 0, "C")
    pdf.cell(50, 10, f"{data['Triangulaire_Montant_Remboursement']}", 1, 1, "C")

    # Footer
    pdf.ln(20)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(190, 10, f"Edite le {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="R")
    
    return pdf.output()

# --- INTERFACE ---
LISTE_NOMS = ["Mme GUESSMIA ZAHIRA", "M. BOULAHLIB REDOUANE", "Mme DJAOUDI SARAH", "Mme BEN SAHNOUN LILA", "Mme NASRI RIM", "Mme MECHALIKHE FATMA", "Mlle SALMI NOUR EL HOUDA", "M. BERRABEH DOUADI", "Mme BELAID FAZIA", "M. METMAR OMAR", "Mme AIT OUARAB AMINA", "Mme MILOUDI AMEL", "Mme BERROUANE SAMIRA", "M. MAHREZ MOHAMED", "Mlle FELFOUL SAMIRA", "Mlle MEDJHOUM RAOUIA", "Mme SAHNOUNE IMENE", "Mme KHERIF FADILA", "Mme MERAKEB FAIZA", "Mme MEDJDOUB AMEL", "Mme BEN AICHE MOUNIRA", "Mme SEKAT MANEL FATIMA", "Mme KADRI SIHEM", "Mme TOUAKNI SARAH", "Mme MAASSOUM EPS LAKHDARI SAIDA", "M. TALAMALI IMAD", "Mme BOUCHAREB MOUNIA"]

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 ANGEM PRO - Connexion")
    u = st.selectbox("Utilisateur", [""] + LISTE_NOMS + ["admin"])
    p = st.text_input("Code", type="password")
    if st.button("Se connecter"):
        if p == "1234":
            st.session_state.auth, st.session_state.user = True, u
            st.rerun()
    st.stop()

# --- FORMULAIRE ---
st.title(f"Bilan de : {st.session_state.user}")
col_m, col_a = st.columns(2)
mois = col_m.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
annee = col_a.number_input("Année", 2026)

data = {
    "Accompagnateur": st.session_state.user,
    "Mois": mois,
    "Annee": annee,
    "Agence": "Alger Ouest",
    "Matiere_Premiere_Deposes": 0, "Matiere_Premiere_Finances": 0, "Matiere_Premiere_Montant_Remboursement": 0.0,
    "Triangulaire_Deposes": 0, "Triangulaire_Finances": 0, "Triangulaire_Montant_Remboursement": 0.0
}

tab1, tab2 = st.tabs(["1. Matière Première", "2. Formule Triangulaire"])

with tab1:
    data["Matiere_Premiere_Deposes"] = st.number_input("Dossiers Déposés (MP)", 0)
    data["Matiere_Premiere_Finances"] = st.number_input("Dossiers Financés (MP)", 0)
    data["Matiere_Premiere_Montant_Remboursement"] = st.number_input("Montant Remboursé (MP)", 0.0)

with tab2:
    data["Triangulaire_Deposes"] = st.number_input("Dossiers Déposés (Tri)", 0)
    data["Triangulaire_Finances"] = st.number_input("Dossiers Financés (Tri)", 0)
    data["Triangulaire_Montant_Remboursement"] = st.number_input("Montant Remboursé (Tri)", 0.0)

st.markdown("---")

# --- BOUTON ENREGISTRER & PDF ---
if st.button("💾 ENREGISTRER & GÉNÉRER PDF", type="primary", use_container_width=True):
    # Simuler sauvegarde (ajouter ici votre fonction save_to_gsheet si nécessaire)
    st.success("Données traitées avec succès.")
    
    # Création du PDF
    pdf_output = create_pdf(data)
    
    # Bouton de téléchargement
    st.download_button(
        label="📥 TÉLÉCHARGER LE BILAN PDF",
        data=bytes(pdf_output),
        file_name=f"Bilan_{st.session_state.user}_{mois}.pdf",
        mime="application/pdf"
    )
    st.balloons()
