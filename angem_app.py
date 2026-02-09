import streamlit as st
import gspread
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="ANGEM PRO - Rapport Complet", layout="wide")

# --- GÉNÉRATEUR PDF (FIDÈLE AU MODÈLE EXCEL) ---
class ANGEM_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(100, 5, 'Antenne Régionale : Tipaza', 0, 0)
        self.ln(5)
        self.cell(100, 5, 'Agence : Alger Ouest', 0, 0)
        self.ln(10)
        
    def section_title(self, label):
        self.set_fill_color(255, 230, 204)
        self.set_font('Arial', 'BI', 10)
        self.cell(190, 7, label, 1, 1, 'L', True)

def generate_full_pdf(data):
    pdf = ANGEM_PDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, "Rapport d'activités mensuel", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(190, 10, f"Mois : {data['Mois'].upper()}", 0, 1, 'R')
    
    # --- Fonction pour dessiner les tableaux standards ---
    def draw_table(title, prefix, headers):
        pdf.section_title(title)
        pdf.set_font('Arial', '', 7)
        width = 190 / len(headers)
        for h in headers: pdf.cell(width, 7, h, 1, 0, 'C')
        pdf.ln()
        for h in headers:
            key = f"{prefix}_{h.replace(' ', '_').replace('.', '')}"
            pdf.cell(width, 7, str(data.get(key, 0)), 1, 0, 'C')
        pdf.ln(10)

    # 1. Matière Première
    draw_table("1. Formule : Achat de matière premières", "MP", 
               ["Dossiers déposés", "traités CEF", "validés CEF", "transmis AR", "financés", "reçus remb", "Montant remb"])

    # 2. Triangulaire
    draw_table("2. Formule : Triangulaire", "TRI", 
               ["déposés", "traités CEF", "validés CEF", "transmis Banque", "Notif bancaire", "transmis AR", "financés", "BC 10%", "BC 90%", "PV Exist", "PV Dém", "reçus remb", "Montant remb"])

    # 4. CAM
    pdf.section_title("4. L'accueil des citoyens au niveau de la CAM")
    pdf.cell(95, 7, "Nbr. de citoyens reçus", 1, 0, 'C')
    pdf.cell(95, 7, str(data.get("CAM_Recus", 0)), 1, 1, 'C')
    pdf.ln(5)

    # 5, 6, 7 (Télécom, Recyclage, Tricycle) - Structure identique
    for i, name in zip(["5", "6", "7"], ["Algérie télécom", "Recyclage", "Tricycle"]):
        draw_table(f"{i}. Dossiers ({name})", name.replace(" ", ""), 
                   ["déposés", "traités CEF", "validés CEF", "transmis Banque", "Notif bancaire", "financés", "BC 10%", "BC 90%", "PV Exist", "PV Dém", "reçus remb", "Montant remb"])

    # 10. Rappels
    pdf.section_title("10. Lettres de rappel / Sortie sur terrain")
    pdf.cell(60, 7, "Type", 1, 0, 'C')
    pdf.cell(60, 7, "L/R envoyés", 1, 0, 'C')
    pdf.cell(70, 7, "Sorties Terrain", 1, 1, 'C')
    for m in ["27000", "40000", "100000", "400000", "1000000"]:
        pdf.cell(60, 6, f"{m} DA", 1, 0, 'C')
        pdf.cell(60, 6, str(data.get(f"LR_{m}", 0)), 1, 0, 'C')
        pdf.cell(70, 6, str(data.get(f"ST_{m}", 0)), 1, 1, 'C')

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 10, f"L'accompagnateur (trice) : {data['Nom']}", 0, 1, 'R')
    return pdf.output()

# --- INTERFACE ---
st.title(f"Saisie du Rapport Complet")
# (Ici, insérez votre logique de connexion habituelle)

data = {"Nom": st.session_state.get('user', 'Agent'), "Mois": st.selectbox("Mois", ["Janvier", "Février", "..."]), "Annee": 2026}

# Organisation par rubriques pour ne pas surcharger l'écran
with st.expander("1. Matière Première (7 cases)"):
    c1, c2, c3, c4 = st.columns(4)
    data["MP_Dossiers_déposés"] = c1.number_input("Déposés", 0)
    data["MP_traités_CEF"] = c2.number_input("Traités CEF", 0)
    data["MP_validés_CEF"] = c3.number_input("Validés CEF", 0)
    data["MP_Montant_remb"] = c4.number_input("Montant Remboursé", 0.0)
    # ... ajoutez les autres cases MP ici

with st.expander("2. Triangulaire (13 cases)"):
    # (Ajoutez les colonnes c1 à c13 ici pour la rubrique 2)
    pass

with st.expander("5, 6, 7. Dispositifs Spécifiques"):
    # (Ajoutez les champs pour Télécom, Recyclage et Tricycle)
    pass

with st.expander("10. Rappels et Terrain"):
    # (Champs pour les lettres de rappel)
    pass

if st.button("💾 ENREGISTRER ET GÉNÉRER PDF COMPLET"):
    pdf_bytes = generate_full_pdf(data)
    st.download_button("📥 TÉLÉCHARGER LE RAPPORT PDF (84 CASES)", data=pdf_bytes, file_name="Rapport_Complet.pdf")
