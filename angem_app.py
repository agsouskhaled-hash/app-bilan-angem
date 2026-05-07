</div>
                """, unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.9;'>
                    <b>🗓️ Prochaine échéance :</b> {dos.prochaine_ech or '—'}<br>
                    <b>🚦 État de la dette :</b> {dos.etat_dette or '—'}<br>
                    <b>⚡ Anticipation :</b> {dos.anticip or '—'}<br>
                    <b>📊 Échéance anticipation :</b> {dos.ech_anticip or '—'}<br>
                    <b>🏦 Banque :</b> {dos.banque_nom or '—'}<br>
                    <b>🔢 N° Compte :</b> {dos.numero_compte or '—'}
                </div>
                """, unsafe_allow_html=True)
            if dos.observations:
                st.markdown(f"<div style='margin-top:12px; padding:12px; background:#fef3c7; border-radius:8px;'><b>📝 Observations :</b> {dos.observations}</div>", unsafe_allow_html=True)
            taux_local = (dos.montant_rembourse / dos.montant_pnr * 100) if dos.montant_pnr > 0 else 0
            st.progress(min(taux_local/100, 1.0))
            st.caption(f"Progression : **{taux_local:.1f}%** remboursé")

        try:
            champs_dyn = json.loads(dos.champs_dynamiques or '{}')
        except Exception:
            champs_dyn = {}
        if champs_dyn:
            with st.expander(f"📋 Informations complémentaires ({len(champs_dyn)} champs)", expanded=False):
                items = list(champs_dyn.items())
                for i in range(0, len(items), 2):
                    cols = st.columns(2)
                    for j, (k, v) in enumerate(items[i:i+2]):
                        with cols[j]:
                            new_val = st.text_input(k, value=v, key=f"dyn_{dos_id}_{k}")
                            if new_val != v:
                                champs_dyn[k] = new_val
                if st.button("💾 Sauvegarder", key=f"save_dyn_{dos_id}"):
                    dos.champs_dynamiques = json.dumps(champs_dyn, ensure_ascii=False)
                    st.success("Champs mis à jour !")
                    st.rerun()
        col_g, col_d = st.columns([1.5, 1])
        with col_g:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📝 Historique & Observations**")
            if dos.observations:
                st.info(f"**Obs Excel :** {dos.observations}")
            note = st.text_area("Ajouter un compte-rendu :", key=f"n_{dos_id}")
            if st.button("Enregistrer", key=f"bn_{dos_id}"):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                dos.historique_visites = f"🔹 **[{date_str}]** {note}\n" + (dos.historique_visites or "")
                st.rerun()
            hist = (dos.historique_visites or 'Aucun rapport enregistré').replace('\n', '<br>')
            st.markdown(f"<div style='background:#f8fafc; padding:15px; border-radius:8px; height:200px; overflow-y:auto;'>{hist}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_d:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📎 Documents**")
            pdf_data = generer_fiche_promoteur_pdf(dos)
            st.download_button("📄 Fiche PDF", data=pdf_data,
                               file_name=f"ANGEM_{dos.identifiant}.pdf", mime="application/pdf",
                               use_container_width=True)
            with st.expander("📸 Joindre un document"):
                cam     = st.camera_input("Caméra", key=f"c_{dos_id}")
                file_up = st.file_uploader("Fichier", key=f"f_{dos_id}")
                if st.button("☁️ Archiver", key=f"u_{dos_id}"):
                    data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                    if data:
                        try:
                            fname = f"{dos.identifiant}_{int(datetime.now().timestamp())}.jpg"
                            supabase_client.storage.from_("scans_angem").upload(
                                file=data, path=fname, file_options={"content-type": "image/jpeg"})
                            dos.documents = (dos.documents or "") + fname + "|"
                            st.success("Archivé !")
                        except Exception as e:
                            st.error(f"Erreur: {e}")
            if dos.documents:
                for d in [x for x in dos.documents.split('|') if x]:
                    url = supabase_client.storage.from_('scans_angem').get_public_url(d)
                    st.markdown(f"📥 <a href='{url}' target='_blank'>Voir document</a>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# VUE GESTION
# ==========================================

def page_gestion(mode="financement", vue_admin=False):
    env       = st.session_state.user['env']
    role      = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    # ✅ Mode unifié : un dossier apparait s'il est dans Finance OU Recouvrement
    is_unifie = (mode == "unifie")
    if is_unifie:
        badge_filter = "(in_finance='OUI' OR in_recouvrement='OUI')"
    else:
        badge = "in_finance" if mode == "financement" else "in_recouvrement"
        badge_filter = f"{badge}='OUI'"

    if (is_unifie or mode == "financement") and role in ("finance", "admin"):
        st.markdown("<div class='import-rapide-box'>", unsafe_allow_html=True)
        col_imp1, col_imp2 = st.columns([3, 1])
        with col_imp1:
            st.markdown("**📥 Import rapide — Nouveaux dossiers financés**")
            st.caption("Importe et affecte automatiquement les dossiers aux accompagnateurs.")
        with col_imp2:
            if st.button("📂 Importer", key="btn_import_rapide", use_container_width=True):
                st.session_state.import_quick_open = not st.session_state.import_quick_open
        st.markdown("</div>", unsafe_allow_html=True)
        if st.session_state.import_quick_open:
            with st.expander("🚀 Import rapide", expanded=True):
                _widget_import_rapide(env)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(f"SELECT * FROM dossiers WHERE type_dispositif=:env AND {badge_filter} ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    if role == 'agent':
        nvx = len(df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80) & (df['est_nouveau'] == 'OUI')])
        if nvx > 0:
            st.markdown(f"<div class='alerte-nouveau'>🎉 {nvx} nouveau(x) dossier(s) vous ont été affectés !</div>", unsafe_allow_html=True)

        # ✅ STATISTIQUES PERSONNELLES DE L'AGENT
        df_agent_stats = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        try:
            df_agent_stats['montant_pnr']        = pd.to_numeric(df_agent_stats['montant_pnr'], errors='coerce').fillna(0.0)
            df_agent_stats['montant_rembourse']  = pd.to_numeric(df_agent_stats['montant_rembourse'], errors='coerce').fillna(0.0)
            df_agent_stats['reste_rembourser']   = pd.to_numeric(df_agent_stats['reste_rembourser'], errors='coerce').fillna(0.0)
        except Exception:
            pass
        nb_dos     = len(df_agent_stats)
        tot_pnr    = float(df_agent_stats['montant_pnr'].sum()) if 'montant_pnr' in df_agent_stats else 0
        tot_remb   = float(df_agent_stats['montant_rembourse'].sum()) if 'montant_rembourse' in df_agent_stats else 0
        tot_reste  = float(df_agent_stats['reste_rembourser'].sum()) if 'reste_rembourser' in df_agent_stats else 0
        taux_perso = (tot_remb / tot_pnr * 100) if tot_pnr > 0 else 0
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Outfit; font-size:18px; font-weight:700; margin-bottom:14px;'>📊 Mon tableau de bord</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📂</div><div class='stat-val'>{nb_dos}</div><div class='stat-lbl'>Mes Dossiers</div></div>", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>💰</div><div class='stat-val'>{tot_pnr/1_000_000:.1f}M</div><div class='stat-lbl'>PNR Total (DA)</div></div>", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>✅</div><div class='stat-val'>{tot_remb/1_000_000:.1f}M</div><div class='stat-lbl'>Recouvré (DA)</div></div>", unsafe_allow_html=True)
        with sc4:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>⏳</div><div class='stat-val'>{tot_reste/1_000_000:.1f}M</div><div class='stat-lbl'>Reste (DA)</div></div>", unsafe_allow_html=True)
        with sc5:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📈</div><div class='stat-val'>{taux_perso:.1f}%</div><div class='stat-lbl'>Taux Recouvr.</div></div>", unsafe_allow_html=True)
        st.progress(min(taux_perso/100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

        # ✅ STATISTIQUES AGENT
        df_agent    = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        total_dos   = len(df_agent)
        total_pnr   = df_agent['montant_pnr'].astype(float).sum()
        total_remb  = df_agent['montant_rembourse'].astype(float).sum()
        total_reste = df_agent['reste_rembourser'].astype(float).sum()
        taux        = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📂 Mes Dossiers", total_dos)
        c2.metric("💰 PNR Total", f"{total_pnr:,.0f} DA")
        c3.metric("✅ Recouvré", f"{total_remb:,.0f} DA")
        c4.metric("⏳ Reste", f"{total_reste:,.0f} DA")
        c5.metric("📈 Taux", f"{taux:.1f}%")
        st.progress(min(taux / 100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 1, 1])
    tmp_s = c1.text_input("🔍 Recherche rapide...", value=st.session_state.search_query, label_visibility="collapsed")
    if c2.button("Chercher", type="primary", use_container_width=True):
        st.session_state.search_query = tmp_s
        st.rerun()
    if c3.button("❌ Effacer", use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.search_query:
        q = st.session_state.search_query
        df = df[df.apply(lambda x: x.astype(str).str.contains(q, case=False).any(), axis=1)]

    # ✅ FILTRE AGENT — similarité 80%
    if not vue_admin and role == "agent":
        df_filtre = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        if df_filtre.empty and not df.empty:
            with st.expander("⚠️ Aucun dossier trouvé — Diagnostic", expanded=True):
                st.warning(f"Votre nom : **{nom_agent}**")
                noms = [n for n in df['gestionnaire'].dropna().unique().tolist() if str(n).strip() not in ('','NAN')]
                st.info("Noms dans la base :")
                st.write(noms[:30] if noms else "Aucun gestionnaire assigné.")
        df = df_filtre

    df.insert(0, "Ouvrir 📂", False)

    try:
        with engine.connect() as conn:
            df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", conn)
        noms_db = df_agents['nom'].dropna().tolist()
        noms_dossiers = df['gestionnaire'].dropna().tolist()
        liste_agents = [""] + sorted(set(noms_db + noms_dossiers))
    except Exception:
        liste_agents = [""]

    # ✅ ADMIN : édition libre de TOUTES les colonnes
    is_admin = (role == 'admin')

    # ✅ Indicateur visuel : 🟢 complet | 🟡 finance seule | 🔴 recouvrement seul
    def calc_statut_dos(row):
        f = str(row.get('in_finance','NON')).upper() == 'OUI'
        r = str(row.get('in_recouvrement','NON')).upper() == 'OUI'
        if f and r: return "🟢 Complet"
        if f: return "🟡 Finance"
        if r: return "🔴 Recouvr."
        return "⚪"
    df['statut_data'] = df.apply(calc_statut_dos, axis=1)

    if is_unifie:
        if is_admin:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","telephone","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "statut_data": st.column_config.TextColumn("Données", disabled=True, width="small"),
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    elif mode == "financement":
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","agence_bancaire","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    else:
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","montant_pnr","montant_rembourse","reste_rembourser","total_echue","etat_dette","nb_echeance_tombee","prochaine_ech","gestionnaire","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","montant_pnr","montant_rembourse","reste_rembourser","etat_dette","gestionnaire","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "montant_pnr": st.column_config.NumberColumn("Crédit", format="%d DA", disabled=not is_admin),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA", disabled=not is_admin),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA", disabled=not is_admin),
            "total_echue": st.column_config.NumberColumn("Échue", format="%d DA", disabled=not is_admin),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=not is_admin) if is_admin else st.column_config.TextColumn("Agent", disabled=True),
        }

    cols = [c for c in cols if c in df.columns or c == "Ouvrir 📂"]
    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(df[cols], use_container_width=True, hide_index=True, column_config=config, height=500)

    if st.button("💾 Sauvegarder", type="primary"):
        with get_session() as session:
            for _, r in edited.iterrows():
                dos = session.get(Dossier, int(r['id']))
                if dos:
                    if is_admin:
                        # Admin : sauve TOUTES les colonnes affichées
                        for col_name in edited.columns:
                            if col_name in ('Ouvrir 📂', 'id'):
                                continue
                            val = r[col_name]
                            if hasattr(dos, col_name):
                                if col_name in COLONNES_ARGENT:
                                    try:
                                        setattr(dos, col_name, float(val) if val not in (None, '') else 0.0)
                                    except Exception:
                                        pass
                                else:
                                    setattr(dos, col_name, str(val).strip().upper() if val else "")
                    else:
                        if mode == "financement":
                            dos.statut_dossier = r.get('statut_dossier', dos.statut_dossier)
                            if role != 'agent':
                                dos.gestionnaire = str(r.get('gestionnaire','')).strip().upper()
        st.toast("✅ Modifications enregistrées !")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        afficher_profil_complet(dos_id)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# IMPORT RAPIDE
# ==========================================

def _widget_import_rapide(env):
    f = st.file_uploader("📁 Fichier Excel / CSV", type=['xlsx','xls','csv'], key="f_rapide")
    if not f:
        return
    try:
        df_raw = safe_read_dataframe(f)
    except Exception as e:
        st.error(f"Erreur lecture : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(5), use_container_width=True)
    mapping_final = {k: (v if v in excel_cols else "-- Ignorer --") for k, v in mapping_auto.items()}
    with st.expander("🎛️ Ajuster le mapping (optionnel)"):
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        for idx, db_f in enumerate(targets):
            auto_val = mapping_final.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"mr_{db_f}")
    if st.button("🚀 Lancer l'import", type="primary", key="btn_go_rapide"):
        with get_session() as session:
            agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
            with st.status("Import en cours...", expanded=True) as status:
                stats = moteur_import(df, mapping_final, env, 'in_finance', session, agents_db, affectation_auto=True)
            status.update(label="✅ Terminé !", state="complete")
        st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
        if stats['non_assignes'] > 0:
            st.warning(f"⚠️ **{stats['non_assignes']}** sans agent → corbeille.")
        if stats['erreurs']:
            with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                for err in stats['erreurs'][:20]:
                    st.code(err)
        st.session_state.import_quick_open = False
        st.rerun()

# ==========================================
# BILANS & REPORTING
# ==========================================

def page_bilans():
    st.title("📊 Bilans & Reporting")
    env = st.session_state.user['env']

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base est vide.")
        return

    for col in COLONNES_ARGENT:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Filtre date
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📅 Filtres")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        periode = st.selectbox("Période", [
            "Toute la base",
            "Cette semaine",
            "Ce mois",
            "Ce trimestre",
            "Cette année",
            "Personnalisée"
        ])
    date_debut = date_fin = None
    if periode == "Personnalisée":
        with col_f2:
            date_debut = st.date_input("Du", value=date(date.today().year, 1, 1))
        with col_f3:
            date_fin = st.date_input("Au", value=date.today())

    # Appliquer filtre date sur date_financement
    df_filtre = df.copy()
    if periode != "Toute la base" and 'date_financement' in df_filtre.columns:
        today = date.today()
        def parse_date(s):
            for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%m/%d/%Y'):
                try:
                    return datetime.strptime(str(s).strip(), fmt).date()
                except Exception:
                    pass
            return None
        df_filtre['_date'] = df_filtre['date_financement'].apply(parse_date)
        if periode == "Cette semaine":
            lun = today - pd.Timedelta(days=today.weekday())
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d >= lun)]
        elif periode == "Ce mois":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.month == today.month and d.year == today.year)]
        elif periode == "Ce trimestre":
            q = (today.month - 1) // 3
            mois_debut = q * 3 + 1
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year and (d.month-1)//3 == q)]
        elif periode == "Cette année":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year)]
        elif periode == "Personnalisée" and date_debut and date_fin:
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and date_debut <= d <= date_fin)]

    st.caption(f"**{len(df_filtre)}** dossiers sélectionnés sur {len(df)} total")
    st.markdown("</div>", unsafe_allow_html=True)

    # Métriques globales
    st.markdown("### 💰 Vue Globale")
    c1, c2, c3, c4 = st.columns(4)
    total_pnr  = df_filtre['montant_pnr'].sum()
    total_remb = df_filtre['montant_rembourse'].sum()
    total_rest = df_filtre['reste_rembourser'].sum()
    taux_global = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
    c1.metric("Total Dossiers", len(df_filtre))
    c2.metric("PNR Engagé", f"{total_pnr:,.0f} DA")
    c3.metric("Total Recouvré", f"{total_remb:,.0f} DA")
    c4.metric("Reste", f"{total_rest:,.0f} DA")
    st.progress(min(taux_global / 100, 1.0))
    st.caption(f"Taux de recouvrement global : **{taux_global:.1f}%**")

    # Onglets bilans
    tabs = st.tabs(["👥 Par Agent", "🗺️ Par Zone", "🏭 Par Activité", "🏦 Par Banque", "👤 Par Promoteur", "⚠️ Contentieux"])

    # --- PAR AGENT ---
    with tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        if 'gestionnaire' in df_filtre.columns:
            df_agent = df_filtre.groupby('gestionnaire').agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_agent = df_agent[df_agent['gestionnaire'].str.strip() != ""]
            df_agent['Taux %'] = (df_agent['Recouvre'] / df_agent['PNR'] * 100).fillna(0).round(1)
            df_agent = df_agent.sort_values('Dossiers', ascending=False)
            st.dataframe(df_agent, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_agent.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name="bilan_agents.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ZONE ---
    with tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        zone_col = st.selectbox("Regrouper par", ["daira", "commune", "wilaya", "zone", "adresse"], key="zone_col")
        if zone_col in df_filtre.columns:
            df_zone = df_filtre.groupby(zone_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_zone = df_zone[df_zone[zone_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_zone['Taux %'] = (df_zone['Recouvre'] / df_zone['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_zone, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_zone.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{zone_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ACTIVITÉ ---
    with tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        act_col = st.selectbox("Regrouper par", ["secteur", "activite", "code_activite"], key="act_col")
        if act_col in df_filtre.columns:
            df_act = df_filtre.groupby(act_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_act = df_act[df_act[act_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_act['Taux %'] = (df_act['Recouvre'] / df_act['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_act, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_act.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{act_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR BANQUE ---
    with tabs[3]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        banque_col = st.selectbox("Regrouper par", ["banque_nom", "agence_bancaire"], key="banque_col")
        if banque_col in df_filtre.columns:
            df_banque = df_filtre.groupby(banque_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_banque = df_banque[df_banque[banque_col].str.strip() != ""].sort_values('PNR', ascending=False)
            df_banque['Taux %'] = (df_banque['Recouvre'] / df_banque['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_banque, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_banque.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{banque_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR PROMOTEUR ---
    with tabs[4]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        promo_col = st.selectbox("Regrouper par", ["genre", "niveau_instruction", "statut_dossier"], key="promo_col")
        if promo_col in df_filtre.columns:
            df_promo = df_filtre.groupby(promo_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
            ).reset_index()
            df_promo = df_promo[df_promo[promo_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            st.dataframe(df_promo, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                })
            buf = io.BytesIO()
            df_promo.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{promo_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- CONTENTIEUX ---
    with tabs[5]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        df_cont = df_filtre[
            (df_filtre['etat_dette'].str.upper().str.contains('CONTENTIEUX|RETARD', na=False)) |
            (df_filtre['statut_dossier'] == 'Contentieux / Retard')
        ].copy()
        st.metric("Dossiers en contentieux", len(df_cont))
        if not df_cont.empty:
            st.metric("Montant en souffrance", f"{df_cont['reste_rembourser'].sum():,.0f} DA")
            cols_aff = [c for c in ["identifiant","nom","prenom","gestionnaire","daira","commune","montant_pnr","reste_rembourser","etat_dette","nb_echeance_tombee"] if c in df_cont.columns]
            st.dataframe(df_cont[cols_aff], use_container_width=True, hide_index=True)
            buf = io.BytesIO()
            df_cont[cols_aff].to_excel(buf, index=False)
            st.download_button("📥 Export Contentieux Excel", data=buf.getvalue(), file_name="contentieux.xlsx", use_container_width=True)
            st.download_button("📄 Export Contentieux PDF", data=_generer_contentieux_pdf(df_cont),
                               file_name="Contentieux_ANGEM.pdf", mime="application/pdf", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Export global
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📤 Export Global")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📊 Bilan Global PDF", data=generer_rapport_global_pdf(df_filtre),
                           file_name="Bilan_ANGEM.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        df_exp = df_filtre.copy()
        try:
            dyn = df_exp['champs_dynamiques'].apply(lambda x: json.loads(x) if x and x != '{}' else {})
            df_exp = pd.concat([df_exp.drop(columns=['champs_dynamiques']), pd.json_normalize(dyn)], axis=1)
        except Exception:
            pass
        df_exp.to_excel(buf, index=False)
        st.download_button("🟢 Export Excel Complet", data=buf.getvalue(),
                           file_name="Backup_ANGEM.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _generer_contentieux_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 15, "DOSSIERS EN CONTENTIEUX - ANGEM", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        texte = f"ID:{clean_pdf_text(row.get('identifiant',''))} | {clean_pdf_text(row.get('nom',''))} {clean_pdf_text(row.get('prenom',''))} | Reste:{float(row.get('reste_rembourser',0)):,.0f} DA | Agent:{clean_pdf_text(row.get('gestionnaire',''))}"
        pdf.cell(0, 7, texte, ln=True, border='B')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data

# ==========================================
# ADMINISTRATION
# ==========================================

def page_integration_admin():
    env  = st.session_state.user['env']
    role = st.session_state.user['role']
    st.title("⚙️ Administration")

    if role == "finance":
        tabs = st.tabs(["💰 Import Finance"])
        t1, t2, t3, t4, t5, t6 = tabs[0], None, None, None, None, None
    else:
        t1, t2, t3, t4, t5, t6 = st.tabs(["💰 Import Finance", "📈 Import Recouvrement", "👥 Gestionnaires", "🧹 Maintenance", "🔐 Équipes", "🔄 Gestion Agents"])

    with t1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx','xls','csv'], key="ff")
        if f_fin:
            _onglet_import_generique(f_fin, env, 'in_finance', "form_fin", "Finance")
        st.markdown("</div>", unsafe_allow_html=True)

    if t2:
        with t2:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx','xls','csv'], key="fr")
            if f_rec:
                _onglet_import_generique(f_rec, env, 'in_recouvrement', "form_rec", "Recouvrement")
            st.markdown("</div>", unsafe_allow_html=True)

    if t3:
        with t3:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            f_gest = st.file_uploader("Fichier Gestionnaires", type=['xlsx','xls','csv'], key="fgest")
            if f_gest:
                _onglet_import_generique(f_gest, env, 'gestionnaire_only', "form_gest", "Gestionnaires")
            st.markdown("</div>", unsafe_allow_html=True)

    if t4:
        with t4:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            # ✅ Bouton réparation daïras
            if st.button("🔧 Réparer daïras manquantes", type="primary", key="btn_repair_daira"):
                env_r = st.session_state.user['env']
                with get_session() as session:
                    dossiers = session.query(Dossier).filter(Dossier.type_dispositif == env_r).all()
                    c_repare = 0
                    for d in dossiers:
                        if (not d.daira or d.daira.strip() == "") and d.commune:
                            d_deduite = deduire_daira_de_commune(d.commune)
                            if d_deduite:
                                d.daira = d_deduite
                                c_repare += 1
                if c_repare > 0:
                    st.success(f"✅ {c_repare} daïra(s) reconstituée(s) à partir des communes.")
                else:
                    st.info("Aucune daïra à réparer.")
            st.markdown("---")
            if st.button("🧹 Nettoyer Doublons", type="primary"):
                with get_session() as session:
                    dossiers = session.query(Dossier).all()
                    seen = {}
                    ids_del = []
                    for d in dossiers:
                        key = (str(d.identifiant).strip(), d.type_dispositif, d.in_finance, d.in_recouvrement)
                        if key in seen:
                            ids_del.append(d.id)
                        else:
                            seen[key] = d.id
                    if ids_del:
                        session.query(Dossier).filter(Dossier.id.in_(ids_del)).delete(synchronize_session=False)
                        st.success(f"{len(ids_del)} doublons supprimés.")
                    else:
                        st.info("Aucun doublon détecté.")
            st.markdown("---")
            st.error("⚠️ Zone de danger")
            if st.button("🗑️ VIDER TOUTE LA BASE"):
                with get_session() as session:
                    session.query(Dossier).delete()
                st.success("Base vidée.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t5:
        with t5:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            try:
                with engine.connect() as conn:
                    df_u = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", conn)
            except Exception:
                df_u = pd.DataFrame()
            if not df_u.empty:
                ed_u = st.data_editor(df_u, use_container_width=True, hide_index=True,
                    column_config={"id": None,
                                   "identifiant": st.column_config.TextColumn(disabled=True),
                                   "nom": st.column_config.TextColumn(disabled=True),
                                   "daira": st.column_config.SelectboxColumn(options=LISTE_DAIRAS)})
                if st.button("💾 Sauvegarder équipe", type="primary"):
                    with get_session() as session:
                        for _, r in ed_u.iterrows():
                            u = session.get(UtilisateurAuth, int(r['id']))
                            if u:
                                u.mot_de_passe = r['mot_de_passe']
                                u.daira = r['daira']
                    st.success("Équipe mise à jour.")

            st.markdown("---")
            with st.form("ajout_agent"):
                c1, c2, c3 = st.columns([1,1.5,1])
                n_id  = c1.text_input("Identifiant")
                n_nom = c2.text_input("Nom complet")
                n_dai = c3.selectbox("Daïra", LISTE_DAIRAS)
                if st.form_submit_button("Créer le compte") and n_id and n_nom:
                    with get_session() as session:
                        # ✅ Anti-doublon par similarité 80%
                        agents_exist = session.query(UtilisateurAuth).filter_by(role='agent').all()
                        doublon = next((a for a in agents_exist if similarite(a.nom, n_nom) >= 0.80), None)
                        if doublon:
                            st.warning(f"⚠️ Compte similaire existant : **{doublon.nom}**. Vérifiez avant de créer.")
                        elif session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first():
                            st.error("Cet identifiant existe déjà.")
                        else:
                            session.add(UtilisateurAuth(identifiant=n_id.lower(), nom=n_nom.strip().upper(),
                                                        daira=n_dai, mot_de_passe="angem2026", role="agent"))
                            st.success(f"Compte {n_nom} créé !")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t6:
        with t6:
            _outil_gestion_agents()

def _outil_gestion_agents():
    """3 outils : fusion doublons, passation, réécriture noms."""
    st.markdown("### 🔄 Gestion des Agents & Dossiers")

    sous_tabs = st.tabs(["🔁 Fusion Doublons", "📦 Passation de Dossiers", "✏️ Réécriture des Noms"])

    # ==========================================
    # OUTIL 1 — FUSION DOUBLONS AGENTS
    # ==========================================
    with sous_tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Détecte automatiquement les comptes similaires et les fusionne en un seul.")

        with get_session() as session:
            agents = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_data = [(a.id, a.nom, a.daira, a.mot_de_passe) for a in agents]

        # Détecter les groupes similaires
        groupes = []
        traites = set()
        for i, (id1, nom1, d1, pwd1) in enumerate(agents_data):
            if id1 in traites:
                continue
            groupe = [(id1, nom1, d1, pwd1)]
            for j, (id2, nom2, d2, pwd2) in enumerate(agents_data):
                if i != j and id2 not in traites:
                    if similarite(nom1, nom2) >= 0.80:
                        groupe.append((id2, nom2, d2, pwd2))
                        traites.add(id2)
            if len(groupe) > 1:
                traites.add(id1)
                groupes.append(groupe)

        if not groupes:
            st.success("✅ Aucun doublon détecté. Tous les comptes sont uniques.")
        else:
            st.warning(f"⚠️ **{len(groupes)}** groupe(s) de doublons détectés :")
            for g_idx, groupe in enumerate(groupes):
                st.markdown(f"**Groupe {g_idx+1} :**")
                noms_groupe = [f"{nom} ({daira or '—'})" for _, nom, daira, _ in groupe]
                choix = st.selectbox(
                    "Compte à garder :",
                    options=[n[1] for n in groupe],
                    key=f"fusion_keep_{g_idx}"
                )
                st.caption(f"Comptes détectés : {', '.join(noms_groupe)}")

                if st.button(f"🔁 Fusionner ce groupe", key=f"btn_fusion_{g_idx}", type="primary"):
                    id_garde = next(n[0] for n in groupe if n[1] == choix)
                    ids_suppr = [n[0] for n in groupe if n[0] != id_garde]
                    noms_suppr = [n[1] for n in groupe if n[0] != id_garde]

                    with get_session() as session:
                        # Réaffecter tous les dossiers des comptes supprimés vers le compte gardé
                        c_reaffect = 0
                        for nom_s in noms_suppr:
                            dossiers = session.query(Dossier).filter(
                                Dossier.gestionnaire.ilike(f"%{nom_s.split()[0]}%")
                            ).all()
                            for d in dossiers:
                                if similarite(d.gestionnaire, nom_s) >= 0.75:
                                    d.gestionnaire = choix
                                    c_reaffect += 1
                        # Supprimer les comptes doublons
                        for id_s in ids_suppr:
                            u = session.get(UtilisateurAuth, id_s)
                            if u:
                                session.delete(u)

                    st.success(f"✅ Comptes fusionnés. {c_reaffect} dossiers réaffectés vers **{choix}**.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 2 — PASSATION DE DOSSIERS
    # ==========================================
    with sous_tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Transfère tous les dossiers d'un agent vers un autre (changement de poste, départ, etc.)")

        with get_session() as session:
            agents_noms = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()]

        if len(agents_noms) < 2:
            st.warning("Il faut au moins 2 agents.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                agent_source = st.selectbox("👤 Agent qui PART (source)", agents_noms, key="pass_source")
            with col2:
                agents_dest = [a for a in agents_noms if a != agent_source]
                agent_dest  = st.selectbox("👤 Agent qui REPREND (destination)", agents_dest, key="pass_dest")

            env_pass = st.session_state.user['env']

            # Récupérer toutes les communes existantes
            try:
                with engine.connect() as conn:
                    df_temp = pd.read_sql_query(
                        text("SELECT DISTINCT commune FROM dossiers WHERE type_dispositif=:env AND commune != ''"),
                        conn, params={"env": env_pass}
                    )
                liste_communes = [""] + sorted(df_temp['commune'].dropna().tolist())
            except Exception:
                liste_communes = [""]

            col_filtre1, col_filtre2 = st.columns(2)
            with col_filtre1:
                filtre_daira = st.checkbox("🏛️ Filtrer par Daïra", key="pass_filtre_d")
                daira_choisie = ""
                if filtre_daira:
                    daira_choisie = st.selectbox("Daïra", LISTE_DAIRAS, key="pass_daira")
            with col_filtre2:
                filtre_commune = st.checkbox("🏘️ Filtrer par Commune", key="pass_filtre_c")
                commune_choisie = ""
                if filtre_commune:
                    commune_choisie = st.selectbox("Commune", liste_communes, key="pass_commune")

            motif = st.text_input("Motif de la passation (optionnel)", placeholder="Ex: Mutation vers Chéraga")

            # Aperçu
            try:
                with engine.connect() as conn:
                    df_pass = pd.read_sql_query(
                        text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_pass}
                    ).fillna('')
                mask = df_pass['gestionnaire'].apply(lambda x: similarite(x, agent_source) >= 0.80)
                if daira_choisie:
                    # ✅ Filtre intelligent : daïra OU communes de la daïra
                    communes_daira = communes_de_daira(daira_choisie)
                    def match_zone(row):
                        d = str(row.get('daira','')).strip().upper()
                        c = str(row.get('commune','')).strip().upper()
                        if daira_choisie.upper() in d:
                            return True
                        for com in communes_daira:
                            com_n = unicodedata.normalize('NFKD', com.upper()).encode('ascii','ignore').decode('ascii')
                            if com_n in unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii'):
                                return True
                        return False
                    mask = mask & df_pass.apply(match_zone, axis=1)
                if commune_choisie:
                    mask = mask & df_pass['commune'].str.contains(commune_choisie, case=False, na=False)
                df_concernes = df_pass[mask]
                st.metric("Dossiers concernés", len(df_concernes))
                if not df_concernes.empty:
                    st.dataframe(df_concernes[['identifiant','nom','prenom','daira','commune']].head(10), use_container_width=True)
            except Exception:
                df_concernes = pd.DataFrame()

            if st.button("📦 Confirmer la passation", type="primary", key="btn_passation",
                         disabled=df_concernes.empty if not df_concernes.empty else True):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                note = f"🔄 **[Passation {date_str}]** Transféré de {agent_source} vers {agent_dest}"
                if motif:
                    note += f" — Motif : {motif}"
                with get_session() as session:
                    c = 0
                    for _, row in df_concernes.iterrows():
                        d = session.get(Dossier, int(row['id']))
                        if d:
                            d.gestionnaire = agent_dest.strip().upper()
                            d.historique_visites = note + "\n" + (d.historique_visites or "")
                            c += 1
                st.success(f"✅ {c} dossiers transférés de **{agent_source}** vers **{agent_dest}**.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 3 — RÉÉCRITURE DES NOMS
    # ==========================================
    with sous_tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Scanne toute la base et corrige les noms de gestionnaires mal écrits pour les aligner sur les comptes officiels.")

        with get_session() as session:
            agents_officiels = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]

        env_ree = st.session_state.user['env']

        if st.button("🔍 Analyser la base", key="btn_analyse_noms"):
            try:
                with engine.connect() as conn:
                    df_all = pd.read_sql_query(
                        text("SELECT id, gestionnaire FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_ree}
                    ).fillna('')
            except Exception:
                df_all = pd.DataFrame()

            corrections = []
            for _, row in df_all.iterrows():
                gest = str(row['gestionnaire']).strip()
                if not gest or gest.upper() in ('NAN','NONE',''):
                    continue
                meilleur = max(agents_officiels, key=lambda a: similarite(gest, a), default=None)
                if meilleur and similarite(gest, meilleur) >= 0.80 and gest != meilleur:
                    corrections.append({'id': row['id'], 'avant': gest, 'apres': meilleur})

            if not corrections:
                st.success("✅ Tous les noms sont déjà corrects.")
            else:
                df_corr = pd.DataFrame(corrections)
                st.warning(f"**{len(df_corr)}** corrections à appliquer :")
                st.dataframe(df_corr[['avant','apres']], use_container_width=True, hide_index=True)
                if st.button(f"✏️ Appliquer {len(df_corr)} corrections", type="primary", key="btn_appliquer_noms"):
                    with get_session() as session:
                        for corr in corrections:
                            d = session.get(Dossier, corr['id'])
                            if d:
                                d.gestionnaire = corr['apres']
                    st.success(f"✅ {len(corrections)} noms corrigés dans la base.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def _onglet_import_generique(file_obj, env, badge, form_key, label):
    try:
        df_raw = safe_read_dataframe(file_obj)
    except Exception as e:
        st.error(f"Erreur : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(3), use_container_width=True)
    with st.form(form_key):
        st.write(f"### 🎛️ Mapping — {label}")
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        mapping_final = {}
        for idx, db_f in enumerate(targets):
            auto_val = mapping_auto.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"{form_key}_{db_f}")
        sub = st.form_submit_button(f"🚀 Importer {label}", type="primary")
    if sub:
        if badge == 'gestionnaire_only':
            _import_gestionnaires(df, mapping_final, env)
        else:
            with get_session() as session:
                agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
                with st.status("Import en cours...", expanded=True) as status:
                    stats = moteur_import(df, mapping_final, env, badge, session, agents_db)
                status.update(label="✅ Terminé !", state="complete")
            st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
            if stats['erreurs']:
                with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                    for e in stats['erreurs'][:20]:
                        st.code(e)

def _import_gestionnaires(df, mapping, env):
    with get_session() as session:
        agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
        c_affect = 0
        for _, row in df.iterrows():
            xl_id   = mapping.get('identifiant', '-- Ignorer --')
            xl_gest = mapping.get('gestionnaire', '-- Ignorer --')
            if xl_id == '-- Ignorer --' or xl_gest == '-- Ignorer --':
                continue
            ident = clean_identifiant(row.get(xl_id, ''))
            gest  = trouver_agent_intelligent(row.get(xl_gest, ''), agents_db)
            if not ident or not gest:
                continue
            dossiers = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).all()
            for d in dossiers:
                d.gestionnaire = gest
                c_affect += 1
    st.success(f"✅ {c_affect} fiches affectées.")

# ==========================================
# CORBEILLE
# ==========================================

def page_corbeille():
    env   = st.session_state.user['env']
    agent = st.session_state.user['nom']
    daira = st.session_state.user.get('daira', '').strip()
    st.title("🗑️ Corbeille — Dossiers non assignés")

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("La base est vide.")
        return

    def est_non_assigne(val):
        return str(val).strip().upper() in ('', 'NAN', 'NONE', 'NON', '-', 'N/A')

    df_non_assignes = df[df['gestionnaire'].apply(est_non_assigne)].copy()
    if df_non_assignes.empty:
        st.success("✅ Tous les dossiers sont assignés.")
        return

    if daira:
        # ✅ Détection intelligente : daïra → communes → adresse
        ma_daira = daira.strip()
        ma_daira_norm = unicodedata.normalize('NFKD', ma_daira.upper()).encode('ascii','ignore').decode('ascii')
        communes_ma_daira = communes_de_daira(ma_daira)
        communes_norm = [unicodedata.normalize('NFKD', c.upper()).encode('ascii','ignore').decode('ascii') for c in communes_ma_daira]
        def ma_zone(row):
            d = str(row.get('daira','')).strip().upper()
            c = str(row.get('commune','')).strip().upper()
            a = str(row.get('adresse','')).strip().upper()
            d_n = unicodedata.normalize('NFKD', d).encode('ascii','ignore').decode('ascii')
            c_n = unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii')
            a_n = unicodedata.normalize('NFKD', a).encode('ascii','ignore').decode('ascii')
            # 1. Daïra match
            if ma_daira_norm in d_n:
                return True
            # 2. Commune match
            for com_n in communes_norm:
                if com_n and com_n in c_n:
                    return True
            # 3. Adresse match
            for com_n in communes_norm:
                if com_n and com_n in a_n:
                    return True
            if ma_daira_norm in a_n:
                return True
            # 4. Aucune zone définie → visible pour tous
            if not d_n and not c_n and not a_n:
                return True
            return False
        orphans = df_non_assignes[df_non_assignes.apply(ma_zone, axis=1)].copy()
    else:
        st.warning("⚠️ Pas de Daïra assignée — vous voyez tous les dossiers non assignés.")
        orphans = df_non_assignes.copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total non assignés", len(df_non_assignes))
    c2.metric(f"Dans votre zone ({daira or 'toutes'})", len(orphans))
    nb_sans_zone = len(df_non_assignes[df_non_assignes.apply(
        lambda r: not str(r.get('daira','')).strip() and not str(r.get('commune','')).strip(), axis=1)])
    c3.metric("Sans zone définie", nb_sans_zone)

    if orphans.empty:
        st.success(f"✅ Aucun dossier orphelin dans votre secteur.")
        return

    rech = st.text_input("🔍 Filtrer...", placeholder="Nom, ID, commune...")
    if rech:
        orphans = orphans[orphans.apply(lambda x: x.astype(str).str.contains(rech, case=False).any(), axis=1)]

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    orphans_aff = orphans.copy()
    orphans_aff["✅ C'est le mien !"] = False
    cols_aff = [c for c in ["✅ C'est le mien !","identifiant","nom","prenom","activite","commune","daira","montant_pnr","id"]
                if c in orphans_aff.columns or c == "✅ C'est le mien !"]
    ed = st.data_editor(orphans_aff[cols_aff], hide_index=True, use_container_width=True, height=500,
        column_config={
            "id": None,
            "✅ C'est le mien !": st.column_config.CheckboxColumn("Prendre", default=False),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
        })
    ids_sel = ed[ed["✅ C'est le mien !"] == True]['id'].tolist()
    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        if ids_sel:
            st.info(f"**{len(ids_sel)} dossier(s) sélectionné(s)**")
        else:
            st.caption("Cochez les dossiers à prendre en charge.")
    with col_b2:
        if st.button(f"📥 M'attribuer {len(ids_sel)} dossier(s)", type="primary",
                     use_container_width=True, disabled=(len(ids_sel) == 0)):
            with get_session() as session:
                session.query(Dossier).filter(Dossier.id.in_(ids_sel)).update(
                    {"gestionnaire": agent.strip().upper(), "est_nouveau": "NON"},
                    synchronize_session=False)
            st.success(f"✅ {len(ids_sel)} dossier(s) attribués à {agent}.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if "Administration" in page or "Import" in page:
        page_integration_admin()
    elif "Bilans" in page:
        page_bilans()
    elif "Corbeille" in page:
        page_corbeille()
    elif "Mes Dossiers" in page:
        page_gestion(mode="unifie", vue_admin=("admin" == st.session_state.user['role']))
       </div>
                """, unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""
                <div style='font-size:13px; line-height:1.9;'>
                    <b>🗓️ Prochaine échéance :</b> {dos.prochaine_ech or '—'}<br>
                    <b>🚦 État de la dette :</b> {dos.etat_dette or '—'}<br>
                    <b>⚡ Anticipation :</b> {dos.anticip or '—'}<br>
                    <b>📊 Échéance anticipation :</b> {dos.ech_anticip or '—'}<br>
                    <b>🏦 Banque :</b> {dos.banque_nom or '—'}<br>
                    <b>🔢 N° Compte :</b> {dos.numero_compte or '—'}
                </div>
                """, unsafe_allow_html=True)
            if dos.observations:
                st.markdown(f"<div style='margin-top:12px; padding:12px; background:#fef3c7; border-radius:8px;'><b>📝 Observations :</b> {dos.observations}</div>", unsafe_allow_html=True)
            taux_local = (dos.montant_rembourse / dos.montant_pnr * 100) if dos.montant_pnr > 0 else 0
            st.progress(min(taux_local/100, 1.0))
            st.caption(f"Progression : **{taux_local:.1f}%** remboursé")

        try:
            champs_dyn = json.loads(dos.champs_dynamiques or '{}')
        except Exception:
            champs_dyn = {}
        if champs_dyn:
            with st.expander(f"📋 Informations complémentaires ({len(champs_dyn)} champs)", expanded=False):
                items = list(champs_dyn.items())
                for i in range(0, len(items), 2):
                    cols = st.columns(2)
                    for j, (k, v) in enumerate(items[i:i+2]):
                        with cols[j]:
                            new_val = st.text_input(k, value=v, key=f"dyn_{dos_id}_{k}")
                            if new_val != v:
                                champs_dyn[k] = new_val
                if st.button("💾 Sauvegarder", key=f"save_dyn_{dos_id}"):
                    dos.champs_dynamiques = json.dumps(champs_dyn, ensure_ascii=False)
                    st.success("Champs mis à jour !")
                    st.rerun()
        col_g, col_d = st.columns([1.5, 1])
        with col_g:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📝 Historique & Observations**")
            if dos.observations:
                st.info(f"**Obs Excel :** {dos.observations}")
            note = st.text_area("Ajouter un compte-rendu :", key=f"n_{dos_id}")
            if st.button("Enregistrer", key=f"bn_{dos_id}"):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                dos.historique_visites = f"🔹 **[{date_str}]** {note}\n" + (dos.historique_visites or "")
                st.rerun()
            hist = (dos.historique_visites or 'Aucun rapport enregistré').replace('\n', '<br>')
            st.markdown(f"<div style='background:#f8fafc; padding:15px; border-radius:8px; height:200px; overflow-y:auto;'>{hist}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_d:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("**📎 Documents**")
            pdf_data = generer_fiche_promoteur_pdf(dos)
            st.download_button("📄 Fiche PDF", data=pdf_data,
                               file_name=f"ANGEM_{dos.identifiant}.pdf", mime="application/pdf",
                               use_container_width=True)
            with st.expander("📸 Joindre un document"):
                cam     = st.camera_input("Caméra", key=f"c_{dos_id}")
                file_up = st.file_uploader("Fichier", key=f"f_{dos_id}")
                if st.button("☁️ Archiver", key=f"u_{dos_id}"):
                    data = cam.getvalue() if cam else (file_up.getvalue() if file_up else None)
                    if data:
                        try:
                            fname = f"{dos.identifiant}_{int(datetime.now().timestamp())}.jpg"
                            supabase_client.storage.from_("scans_angem").upload(
                                file=data, path=fname, file_options={"content-type": "image/jpeg"})
                            dos.documents = (dos.documents or "") + fname + "|"
                            st.success("Archivé !")
                        except Exception as e:
                            st.error(f"Erreur: {e}")
            if dos.documents:
                for d in [x for x in dos.documents.split('|') if x]:
                    url = supabase_client.storage.from_('scans_angem').get_public_url(d)
                    st.markdown(f"📥 <a href='{url}' target='_blank'>Voir document</a>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# VUE GESTION
# ==========================================

def page_gestion(mode="financement", vue_admin=False):
    env       = st.session_state.user['env']
    role      = st.session_state.user['role']
    nom_agent = st.session_state.user['nom'].upper()
    # ✅ Mode unifié : un dossier apparait s'il est dans Finance OU Recouvrement
    is_unifie = (mode == "unifie")
    if is_unifie:
        badge_filter = "(in_finance='OUI' OR in_recouvrement='OUI')"
    else:
        badge = "in_finance" if mode == "financement" else "in_recouvrement"
        badge_filter = f"{badge}='OUI'"

    if (is_unifie or mode == "financement") and role in ("finance", "admin"):
        st.markdown("<div class='import-rapide-box'>", unsafe_allow_html=True)
        col_imp1, col_imp2 = st.columns([3, 1])
        with col_imp1:
            st.markdown("**📥 Import rapide — Nouveaux dossiers financés**")
            st.caption("Importe et affecte automatiquement les dossiers aux accompagnateurs.")
        with col_imp2:
            if st.button("📂 Importer", key="btn_import_rapide", use_container_width=True):
                st.session_state.import_quick_open = not st.session_state.import_quick_open
        st.markdown("</div>", unsafe_allow_html=True)
        if st.session_state.import_quick_open:
            with st.expander("🚀 Import rapide", expanded=True):
                _widget_import_rapide(env)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(f"SELECT * FROM dossiers WHERE type_dispositif=:env AND {badge_filter} ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("Base vide ou aucun dossier dans cette rubrique.")
        return

    if role == 'agent':
        nvx = len(df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80) & (df['est_nouveau'] == 'OUI')])
        if nvx > 0:
            st.markdown(f"<div class='alerte-nouveau'>🎉 {nvx} nouveau(x) dossier(s) vous ont été affectés !</div>", unsafe_allow_html=True)

        # ✅ STATISTIQUES PERSONNELLES DE L'AGENT
        df_agent_stats = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        try:
            df_agent_stats['montant_pnr']        = pd.to_numeric(df_agent_stats['montant_pnr'], errors='coerce').fillna(0.0)
            df_agent_stats['montant_rembourse']  = pd.to_numeric(df_agent_stats['montant_rembourse'], errors='coerce').fillna(0.0)
            df_agent_stats['reste_rembourser']   = pd.to_numeric(df_agent_stats['reste_rembourser'], errors='coerce').fillna(0.0)
        except Exception:
            pass
        nb_dos     = len(df_agent_stats)
        tot_pnr    = float(df_agent_stats['montant_pnr'].sum()) if 'montant_pnr' in df_agent_stats else 0
        tot_remb   = float(df_agent_stats['montant_rembourse'].sum()) if 'montant_rembourse' in df_agent_stats else 0
        tot_reste  = float(df_agent_stats['reste_rembourser'].sum()) if 'reste_rembourser' in df_agent_stats else 0
        taux_perso = (tot_remb / tot_pnr * 100) if tot_pnr > 0 else 0
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Outfit; font-size:18px; font-weight:700; margin-bottom:14px;'>📊 Mon tableau de bord</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📂</div><div class='stat-val'>{nb_dos}</div><div class='stat-lbl'>Mes Dossiers</div></div>", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>💰</div><div class='stat-val'>{tot_pnr/1_000_000:.1f}M</div><div class='stat-lbl'>PNR Total (DA)</div></div>", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>✅</div><div class='stat-val'>{tot_remb/1_000_000:.1f}M</div><div class='stat-lbl'>Recouvré (DA)</div></div>", unsafe_allow_html=True)
        with sc4:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>⏳</div><div class='stat-val'>{tot_reste/1_000_000:.1f}M</div><div class='stat-lbl'>Reste (DA)</div></div>", unsafe_allow_html=True)
        with sc5:
            st.markdown(f"<div class='stat-agent-card'><div class='stat-icon'>📈</div><div class='stat-val'>{taux_perso:.1f}%</div><div class='stat-lbl'>Taux Recouvr.</div></div>", unsafe_allow_html=True)
        st.progress(min(taux_perso/100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

        # ✅ STATISTIQUES AGENT
        df_agent    = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        total_dos   = len(df_agent)
        total_pnr   = df_agent['montant_pnr'].astype(float).sum()
        total_remb  = df_agent['montant_rembourse'].astype(float).sum()
        total_reste = df_agent['reste_rembourser'].astype(float).sum()
        taux        = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📂 Mes Dossiers", total_dos)
        c2.metric("💰 PNR Total", f"{total_pnr:,.0f} DA")
        c3.metric("✅ Recouvré", f"{total_remb:,.0f} DA")
        c4.metric("⏳ Reste", f"{total_reste:,.0f} DA")
        c5.metric("📈 Taux", f"{taux:.1f}%")
        st.progress(min(taux / 100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 1, 1])
    tmp_s = c1.text_input("🔍 Recherche rapide...", value=st.session_state.search_query, label_visibility="collapsed")
    if c2.button("Chercher", type="primary", use_container_width=True):
        st.session_state.search_query = tmp_s
        st.rerun()
    if c3.button("❌ Effacer", use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.search_query:
        q = st.session_state.search_query
        df = df[df.apply(lambda x: x.astype(str).str.contains(q, case=False).any(), axis=1)]

    # ✅ FILTRE AGENT — similarité 80%
    if not vue_admin and role == "agent":
        df_filtre = df[df['gestionnaire'].apply(lambda x: similarite(x, nom_agent) >= 0.80)]
        if df_filtre.empty and not df.empty:
            with st.expander("⚠️ Aucun dossier trouvé — Diagnostic", expanded=True):
                st.warning(f"Votre nom : **{nom_agent}**")
                noms = [n for n in df['gestionnaire'].dropna().unique().tolist() if str(n).strip() not in ('','NAN')]
                st.info("Noms dans la base :")
                st.write(noms[:30] if noms else "Aucun gestionnaire assigné.")
        df = df_filtre

    df.insert(0, "Ouvrir 📂", False)

    try:
        with engine.connect() as conn:
            df_agents = pd.read_sql_query("SELECT nom FROM utilisateurs_auth WHERE role='agent'", conn)
        noms_db = df_agents['nom'].dropna().tolist()
        noms_dossiers = df['gestionnaire'].dropna().tolist()
        liste_agents = [""] + sorted(set(noms_db + noms_dossiers))
    except Exception:
        liste_agents = [""]

    # ✅ ADMIN : édition libre de TOUTES les colonnes
    is_admin = (role == 'admin')

    # ✅ Indicateur visuel : 🟢 complet | 🟡 finance seule | 🔴 recouvrement seul
    def calc_statut_dos(row):
        f = str(row.get('in_finance','NON')).upper() == 'OUI'
        r = str(row.get('in_recouvrement','NON')).upper() == 'OUI'
        if f and r: return "🟢 Complet"
        if f: return "🟡 Finance"
        if r: return "🔴 Recouvr."
        return "⚪"
    df['statut_data'] = df.apply(calc_statut_dos, axis=1)

    if is_unifie:
        if is_admin:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","telephone","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","statut_data","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","montant_rembourse","reste_rembourser","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "statut_data": st.column_config.TextColumn("Données", disabled=True, width="small"),
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA"),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    elif mode == "financement":
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","agence_bancaire","date_financement","est_nouveau","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","statut_dossier","gestionnaire","montant_pnr","num_ordre_versement","banque_nom","date_financement","est_nouveau","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "est_nouveau": st.column_config.TextColumn("Nouveau", disabled=not is_admin),
            "statut_dossier": st.column_config.SelectboxColumn("Étape", options=LISTE_STATUTS, width="medium"),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=(role=='agent')),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
            "identifiant": st.column_config.TextColumn(disabled=not is_admin),
            "nom": st.column_config.TextColumn(disabled=not is_admin),
            "prenom": st.column_config.TextColumn(disabled=not is_admin),
        }
    else:
        if is_admin:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","adresse","commune","daira","activite","montant_pnr","montant_rembourse","reste_rembourser","total_echue","etat_dette","nb_echeance_tombee","prochaine_ech","gestionnaire","id"]
        else:
            cols = ["Ouvrir 📂","identifiant","nom","prenom","telephone","montant_pnr","montant_rembourse","reste_rembourser","etat_dette","gestionnaire","id"]
        config = {
            "Ouvrir 📂": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "montant_pnr": st.column_config.NumberColumn("Crédit", format="%d DA", disabled=not is_admin),
            "montant_rembourse": st.column_config.NumberColumn("Remboursé", format="%d DA", disabled=not is_admin),
            "reste_rembourser": st.column_config.NumberColumn("Reste", format="%d DA", disabled=not is_admin),
            "total_echue": st.column_config.NumberColumn("Échue", format="%d DA", disabled=not is_admin),
            "gestionnaire": st.column_config.SelectboxColumn("Agent", options=liste_agents, disabled=not is_admin) if is_admin else st.column_config.TextColumn("Agent", disabled=True),
        }

    cols = [c for c in cols if c in df.columns or c == "Ouvrir 📂"]
    st.markdown("<div class='modern-card' style='padding:10px;'>", unsafe_allow_html=True)
    edited = st.data_editor(df[cols], use_container_width=True, hide_index=True, column_config=config, height=500)

    if st.button("💾 Sauvegarder", type="primary"):
        with get_session() as session:
            for _, r in edited.iterrows():
                dos = session.get(Dossier, int(r['id']))
                if dos:
                    if is_admin:
                        # Admin : sauve TOUTES les colonnes affichées
                        for col_name in edited.columns:
                            if col_name in ('Ouvrir 📂', 'id'):
                                continue
                            val = r[col_name]
                            if hasattr(dos, col_name):
                                if col_name in COLONNES_ARGENT:
                                    try:
                                        setattr(dos, col_name, float(val) if val not in (None, '') else 0.0)
                                    except Exception:
                                        pass
                                else:
                                    setattr(dos, col_name, str(val).strip().upper() if val else "")
                    else:
                        if mode == "financement":
                            dos.statut_dossier = r.get('statut_dossier', dos.statut_dossier)
                            if role != 'agent':
                                dos.gestionnaire = str(r.get('gestionnaire','')).strip().upper()
        st.toast("✅ Modifications enregistrées !")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    sel = edited[edited["Ouvrir 📂"] == True]
    if not sel.empty:
        dos_id = int(sel.iloc[0]['id'])
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        afficher_profil_complet(dos_id)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# IMPORT RAPIDE
# ==========================================

def _widget_import_rapide(env):
    f = st.file_uploader("📁 Fichier Excel / CSV", type=['xlsx','xls','csv'], key="f_rapide")
    if not f:
        return
    try:
        df_raw = safe_read_dataframe(f)
    except Exception as e:
        st.error(f"Erreur lecture : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(5), use_container_width=True)
    mapping_final = {k: (v if v in excel_cols else "-- Ignorer --") for k, v in mapping_auto.items()}
    with st.expander("🎛️ Ajuster le mapping (optionnel)"):
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        for idx, db_f in enumerate(targets):
            auto_val = mapping_final.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"mr_{db_f}")
    if st.button("🚀 Lancer l'import", type="primary", key="btn_go_rapide"):
        with get_session() as session:
            agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
            with st.status("Import en cours...", expanded=True) as status:
                stats = moteur_import(df, mapping_final, env, 'in_finance', session, agents_db, affectation_auto=True)
            status.update(label="✅ Terminé !", state="complete")
        st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
        if stats['non_assignes'] > 0:
            st.warning(f"⚠️ **{stats['non_assignes']}** sans agent → corbeille.")
        if stats['erreurs']:
            with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                for err in stats['erreurs'][:20]:
                    st.code(err)
        st.session_state.import_quick_open = False
        st.rerun()

# ==========================================
# BILANS & REPORTING
# ==========================================

def page_bilans():
    st.title("📊 Bilans & Reporting")
    env = st.session_state.user['env']

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.warning("La base est vide.")
        return

    for col in COLONNES_ARGENT:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Filtre date
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📅 Filtres")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        periode = st.selectbox("Période", [
            "Toute la base",
            "Cette semaine",
            "Ce mois",
            "Ce trimestre",
            "Cette année",
            "Personnalisée"
        ])
    date_debut = date_fin = None
    if periode == "Personnalisée":
        with col_f2:
            date_debut = st.date_input("Du", value=date(date.today().year, 1, 1))
        with col_f3:
            date_fin = st.date_input("Au", value=date.today())

    # Appliquer filtre date sur date_financement
    df_filtre = df.copy()
    if periode != "Toute la base" and 'date_financement' in df_filtre.columns:
        today = date.today()
        def parse_date(s):
            for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%m/%d/%Y'):
                try:
                    return datetime.strptime(str(s).strip(), fmt).date()
                except Exception:
                    pass
            return None
        df_filtre['_date'] = df_filtre['date_financement'].apply(parse_date)
        if periode == "Cette semaine":
            lun = today - pd.Timedelta(days=today.weekday())
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d >= lun)]
        elif periode == "Ce mois":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.month == today.month and d.year == today.year)]
        elif periode == "Ce trimestre":
            q = (today.month - 1) // 3
            mois_debut = q * 3 + 1
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year and (d.month-1)//3 == q)]
        elif periode == "Cette année":
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and d.year == today.year)]
        elif periode == "Personnalisée" and date_debut and date_fin:
            df_filtre = df_filtre[df_filtre['_date'].apply(lambda d: d is not None and date_debut <= d <= date_fin)]

    st.caption(f"**{len(df_filtre)}** dossiers sélectionnés sur {len(df)} total")
    st.markdown("</div>", unsafe_allow_html=True)

    # Métriques globales
    st.markdown("### 💰 Vue Globale")
    c1, c2, c3, c4 = st.columns(4)
    total_pnr  = df_filtre['montant_pnr'].sum()
    total_remb = df_filtre['montant_rembourse'].sum()
    total_rest = df_filtre['reste_rembourser'].sum()
    taux_global = (total_remb / total_pnr * 100) if total_pnr > 0 else 0
    c1.metric("Total Dossiers", len(df_filtre))
    c2.metric("PNR Engagé", f"{total_pnr:,.0f} DA")
    c3.metric("Total Recouvré", f"{total_remb:,.0f} DA")
    c4.metric("Reste", f"{total_rest:,.0f} DA")
    st.progress(min(taux_global / 100, 1.0))
    st.caption(f"Taux de recouvrement global : **{taux_global:.1f}%**")

    # Onglets bilans
    tabs = st.tabs(["👥 Par Agent", "🗺️ Par Zone", "🏭 Par Activité", "🏦 Par Banque", "👤 Par Promoteur", "⚠️ Contentieux"])

    # --- PAR AGENT ---
    with tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        if 'gestionnaire' in df_filtre.columns:
            df_agent = df_filtre.groupby('gestionnaire').agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_agent = df_agent[df_agent['gestionnaire'].str.strip() != ""]
            df_agent['Taux %'] = (df_agent['Recouvre'] / df_agent['PNR'] * 100).fillna(0).round(1)
            df_agent = df_agent.sort_values('Dossiers', ascending=False)
            st.dataframe(df_agent, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_agent.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name="bilan_agents.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ZONE ---
    with tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        zone_col = st.selectbox("Regrouper par", ["daira", "commune", "wilaya", "zone", "adresse"], key="zone_col")
        if zone_col in df_filtre.columns:
            df_zone = df_filtre.groupby(zone_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_zone = df_zone[df_zone[zone_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_zone['Taux %'] = (df_zone['Recouvre'] / df_zone['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_zone, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_zone.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{zone_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR ACTIVITÉ ---
    with tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        act_col = st.selectbox("Regrouper par", ["secteur", "activite", "code_activite"], key="act_col")
        if act_col in df_filtre.columns:
            df_act = df_filtre.groupby(act_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_act = df_act[df_act[act_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            df_act['Taux %'] = (df_act['Recouvre'] / df_act['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_act, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_act.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{act_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR BANQUE ---
    with tabs[3]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        banque_col = st.selectbox("Regrouper par", ["banque_nom", "agence_bancaire"], key="banque_col")
        if banque_col in df_filtre.columns:
            df_banque = df_filtre.groupby(banque_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
                Reste=('reste_rembourser','sum')
            ).reset_index()
            df_banque = df_banque[df_banque[banque_col].str.strip() != ""].sort_values('PNR', ascending=False)
            df_banque['Taux %'] = (df_banque['Recouvre'] / df_banque['PNR'] * 100).fillna(0).round(1)
            st.dataframe(df_banque, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                    "Reste": st.column_config.NumberColumn(format="%d DA"),
                    "Taux %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                })
            buf = io.BytesIO()
            df_banque.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{banque_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PAR PROMOTEUR ---
    with tabs[4]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        promo_col = st.selectbox("Regrouper par", ["genre", "niveau_instruction", "statut_dossier"], key="promo_col")
        if promo_col in df_filtre.columns:
            df_promo = df_filtre.groupby(promo_col).agg(
                Dossiers=('id','count'),
                PNR=('montant_pnr','sum'),
                Recouvre=('montant_rembourse','sum'),
            ).reset_index()
            df_promo = df_promo[df_promo[promo_col].str.strip() != ""].sort_values('Dossiers', ascending=False)
            st.dataframe(df_promo, use_container_width=True, hide_index=True,
                column_config={
                    "PNR": st.column_config.NumberColumn(format="%d DA"),
                    "Recouvre": st.column_config.NumberColumn(format="%d DA"),
                })
            buf = io.BytesIO()
            df_promo.to_excel(buf, index=False)
            st.download_button("📥 Export Excel", data=buf.getvalue(), file_name=f"bilan_{promo_col}.xlsx", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- CONTENTIEUX ---
    with tabs[5]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        df_cont = df_filtre[
            (df_filtre['etat_dette'].str.upper().str.contains('CONTENTIEUX|RETARD', na=False)) |
            (df_filtre['statut_dossier'] == 'Contentieux / Retard')
        ].copy()
        st.metric("Dossiers en contentieux", len(df_cont))
        if not df_cont.empty:
            st.metric("Montant en souffrance", f"{df_cont['reste_rembourser'].sum():,.0f} DA")
            cols_aff = [c for c in ["identifiant","nom","prenom","gestionnaire","daira","commune","montant_pnr","reste_rembourser","etat_dette","nb_echeance_tombee"] if c in df_cont.columns]
            st.dataframe(df_cont[cols_aff], use_container_width=True, hide_index=True)
            buf = io.BytesIO()
            df_cont[cols_aff].to_excel(buf, index=False)
            st.download_button("📥 Export Contentieux Excel", data=buf.getvalue(), file_name="contentieux.xlsx", use_container_width=True)
            st.download_button("📄 Export Contentieux PDF", data=_generer_contentieux_pdf(df_cont),
                               file_name="Contentieux_ANGEM.pdf", mime="application/pdf", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Export global
    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    st.markdown("### 📤 Export Global")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📊 Bilan Global PDF", data=generer_rapport_global_pdf(df_filtre),
                           file_name="Bilan_ANGEM.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        df_exp = df_filtre.copy()
        try:
            dyn = df_exp['champs_dynamiques'].apply(lambda x: json.loads(x) if x and x != '{}' else {})
            df_exp = pd.concat([df_exp.drop(columns=['champs_dynamiques']), pd.json_normalize(dyn)], axis=1)
        except Exception:
            pass
        df_exp.to_excel(buf, index=False)
        st.download_button("🟢 Export Excel Complet", data=buf.getvalue(),
                           file_name="Backup_ANGEM.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def _generer_contentieux_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 15, "DOSSIERS EN CONTENTIEUX - ANGEM", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        texte = f"ID:{clean_pdf_text(row.get('identifiant',''))} | {clean_pdf_text(row.get('nom',''))} {clean_pdf_text(row.get('prenom',''))} | Reste:{float(row.get('reste_rembourser',0)):,.0f} DA | Agent:{clean_pdf_text(row.get('gestionnaire',''))}"
        pdf.cell(0, 7, texte, ln=True, border='B')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            data = f.read()
    os.unlink(tmp.name)
    return data

# ==========================================
# ADMINISTRATION
# ==========================================

def page_integration_admin():
    env  = st.session_state.user['env']
    role = st.session_state.user['role']
    st.title("⚙️ Administration")

    if role == "finance":
        tabs = st.tabs(["💰 Import Finance"])
        t1, t2, t3, t4, t5, t6 = tabs[0], None, None, None, None, None
    else:
        t1, t2, t3, t4, t5, t6 = st.tabs(["💰 Import Finance", "📈 Import Recouvrement", "👥 Gestionnaires", "🧹 Maintenance", "🔐 Équipes", "🔄 Gestion Agents"])

    with t1:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        f_fin = st.file_uploader("Fichier Finance", type=['xlsx','xls','csv'], key="ff")
        if f_fin:
            _onglet_import_generique(f_fin, env, 'in_finance', "form_fin", "Finance")
        st.markdown("</div>", unsafe_allow_html=True)

    if t2:
        with t2:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            f_rec = st.file_uploader("Fichier Recouvrement", type=['xlsx','xls','csv'], key="fr")
            if f_rec:
                _onglet_import_generique(f_rec, env, 'in_recouvrement', "form_rec", "Recouvrement")
            st.markdown("</div>", unsafe_allow_html=True)

    if t3:
        with t3:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            f_gest = st.file_uploader("Fichier Gestionnaires", type=['xlsx','xls','csv'], key="fgest")
            if f_gest:
                _onglet_import_generique(f_gest, env, 'gestionnaire_only', "form_gest", "Gestionnaires")
            st.markdown("</div>", unsafe_allow_html=True)

    if t4:
        with t4:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            # ✅ Bouton réparation daïras
            if st.button("🔧 Réparer daïras manquantes", type="primary", key="btn_repair_daira"):
                env_r = st.session_state.user['env']
                with get_session() as session:
                    dossiers = session.query(Dossier).filter(Dossier.type_dispositif == env_r).all()
                    c_repare = 0
                    for d in dossiers:
                        if (not d.daira or d.daira.strip() == "") and d.commune:
                            d_deduite = deduire_daira_de_commune(d.commune)
                            if d_deduite:
                                d.daira = d_deduite
                                c_repare += 1
                if c_repare > 0:
                    st.success(f"✅ {c_repare} daïra(s) reconstituée(s) à partir des communes.")
                else:
                    st.info("Aucune daïra à réparer.")
            st.markdown("---")
            if st.button("🧹 Nettoyer Doublons", type="primary"):
                with get_session() as session:
                    dossiers = session.query(Dossier).all()
                    seen = {}
                    ids_del = []
                    for d in dossiers:
                        key = (str(d.identifiant).strip(), d.type_dispositif, d.in_finance, d.in_recouvrement)
                        if key in seen:
                            ids_del.append(d.id)
                        else:
                            seen[key] = d.id
                    if ids_del:
                        session.query(Dossier).filter(Dossier.id.in_(ids_del)).delete(synchronize_session=False)
                        st.success(f"{len(ids_del)} doublons supprimés.")
                    else:
                        st.info("Aucun doublon détecté.")
            st.markdown("---")
            st.error("⚠️ Zone de danger")
            if st.button("🗑️ VIDER TOUTE LA BASE"):
                with get_session() as session:
                    session.query(Dossier).delete()
                st.success("Base vidée.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t5:
        with t5:
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            try:
                with engine.connect() as conn:
                    df_u = pd.read_sql_query("SELECT id, identifiant, nom, daira, mot_de_passe FROM utilisateurs_auth WHERE role='agent'", conn)
            except Exception:
                df_u = pd.DataFrame()
            if not df_u.empty:
                ed_u = st.data_editor(df_u, use_container_width=True, hide_index=True,
                    column_config={"id": None,
                                   "identifiant": st.column_config.TextColumn(disabled=True),
                                   "nom": st.column_config.TextColumn(disabled=True),
                                   "daira": st.column_config.SelectboxColumn(options=LISTE_DAIRAS)})
                if st.button("💾 Sauvegarder équipe", type="primary"):
                    with get_session() as session:
                        for _, r in ed_u.iterrows():
                            u = session.get(UtilisateurAuth, int(r['id']))
                            if u:
                                u.mot_de_passe = r['mot_de_passe']
                                u.daira = r['daira']
                    st.success("Équipe mise à jour.")

            st.markdown("---")
            with st.form("ajout_agent"):
                c1, c2, c3 = st.columns([1,1.5,1])
                n_id  = c1.text_input("Identifiant")
                n_nom = c2.text_input("Nom complet")
                n_dai = c3.selectbox("Daïra", LISTE_DAIRAS)
                if st.form_submit_button("Créer le compte") and n_id and n_nom:
                    with get_session() as session:
                        # ✅ Anti-doublon par similarité 80%
                        agents_exist = session.query(UtilisateurAuth).filter_by(role='agent').all()
                        doublon = next((a for a in agents_exist if similarite(a.nom, n_nom) >= 0.80), None)
                        if doublon:
                            st.warning(f"⚠️ Compte similaire existant : **{doublon.nom}**. Vérifiez avant de créer.")
                        elif session.query(UtilisateurAuth).filter_by(identifiant=n_id.lower()).first():
                            st.error("Cet identifiant existe déjà.")
                        else:
                            session.add(UtilisateurAuth(identifiant=n_id.lower(), nom=n_nom.strip().upper(),
                                                        daira=n_dai, mot_de_passe="angem2026", role="agent"))
                            st.success(f"Compte {n_nom} créé !")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if t6:
        with t6:
            _outil_gestion_agents()

def _outil_gestion_agents():
    """3 outils : fusion doublons, passation, réécriture noms."""
    st.markdown("### 🔄 Gestion des Agents & Dossiers")

    sous_tabs = st.tabs(["🔁 Fusion Doublons", "📦 Passation de Dossiers", "✏️ Réécriture des Noms"])

    # ==========================================
    # OUTIL 1 — FUSION DOUBLONS AGENTS
    # ==========================================
    with sous_tabs[0]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Détecte automatiquement les comptes similaires et les fusionne en un seul.")

        with get_session() as session:
            agents = session.query(UtilisateurAuth).filter_by(role='agent').all()
            agents_data = [(a.id, a.nom, a.daira, a.mot_de_passe) for a in agents]

        # Détecter les groupes similaires
        groupes = []
        traites = set()
        for i, (id1, nom1, d1, pwd1) in enumerate(agents_data):
            if id1 in traites:
                continue
            groupe = [(id1, nom1, d1, pwd1)]
            for j, (id2, nom2, d2, pwd2) in enumerate(agents_data):
                if i != j and id2 not in traites:
                    if similarite(nom1, nom2) >= 0.80:
                        groupe.append((id2, nom2, d2, pwd2))
                        traites.add(id2)
            if len(groupe) > 1:
                traites.add(id1)
                groupes.append(groupe)

        if not groupes:
            st.success("✅ Aucun doublon détecté. Tous les comptes sont uniques.")
        else:
            st.warning(f"⚠️ **{len(groupes)}** groupe(s) de doublons détectés :")
            for g_idx, groupe in enumerate(groupes):
                st.markdown(f"**Groupe {g_idx+1} :**")
                noms_groupe = [f"{nom} ({daira or '—'})" for _, nom, daira, _ in groupe]
                choix = st.selectbox(
                    "Compte à garder :",
                    options=[n[1] for n in groupe],
                    key=f"fusion_keep_{g_idx}"
                )
                st.caption(f"Comptes détectés : {', '.join(noms_groupe)}")

                if st.button(f"🔁 Fusionner ce groupe", key=f"btn_fusion_{g_idx}", type="primary"):
                    id_garde = next(n[0] for n in groupe if n[1] == choix)
                    ids_suppr = [n[0] for n in groupe if n[0] != id_garde]
                    noms_suppr = [n[1] for n in groupe if n[0] != id_garde]

                    with get_session() as session:
                        # Réaffecter tous les dossiers des comptes supprimés vers le compte gardé
                        c_reaffect = 0
                        for nom_s in noms_suppr:
                            dossiers = session.query(Dossier).filter(
                                Dossier.gestionnaire.ilike(f"%{nom_s.split()[0]}%")
                            ).all()
                            for d in dossiers:
                                if similarite(d.gestionnaire, nom_s) >= 0.75:
                                    d.gestionnaire = choix
                                    c_reaffect += 1
                        # Supprimer les comptes doublons
                        for id_s in ids_suppr:
                            u = session.get(UtilisateurAuth, id_s)
                            if u:
                                session.delete(u)

                    st.success(f"✅ Comptes fusionnés. {c_reaffect} dossiers réaffectés vers **{choix}**.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 2 — PASSATION DE DOSSIERS
    # ==========================================
    with sous_tabs[1]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Transfère tous les dossiers d'un agent vers un autre (changement de poste, départ, etc.)")

        with get_session() as session:
            agents_noms = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').order_by(UtilisateurAuth.nom).all()]

        if len(agents_noms) < 2:
            st.warning("Il faut au moins 2 agents.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                agent_source = st.selectbox("👤 Agent qui PART (source)", agents_noms, key="pass_source")
            with col2:
                agents_dest = [a for a in agents_noms if a != agent_source]
                agent_dest  = st.selectbox("👤 Agent qui REPREND (destination)", agents_dest, key="pass_dest")

            env_pass = st.session_state.user['env']

            # Récupérer toutes les communes existantes
            try:
                with engine.connect() as conn:
                    df_temp = pd.read_sql_query(
                        text("SELECT DISTINCT commune FROM dossiers WHERE type_dispositif=:env AND commune != ''"),
                        conn, params={"env": env_pass}
                    )
                liste_communes = [""] + sorted(df_temp['commune'].dropna().tolist())
            except Exception:
                liste_communes = [""]

            col_filtre1, col_filtre2 = st.columns(2)
            with col_filtre1:
                filtre_daira = st.checkbox("🏛️ Filtrer par Daïra", key="pass_filtre_d")
                daira_choisie = ""
                if filtre_daira:
                    daira_choisie = st.selectbox("Daïra", LISTE_DAIRAS, key="pass_daira")
            with col_filtre2:
                filtre_commune = st.checkbox("🏘️ Filtrer par Commune", key="pass_filtre_c")
                commune_choisie = ""
                if filtre_commune:
                    commune_choisie = st.selectbox("Commune", liste_communes, key="pass_commune")

            motif = st.text_input("Motif de la passation (optionnel)", placeholder="Ex: Mutation vers Chéraga")

            # Aperçu
            try:
                with engine.connect() as conn:
                    df_pass = pd.read_sql_query(
                        text("SELECT * FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_pass}
                    ).fillna('')
                mask = df_pass['gestionnaire'].apply(lambda x: similarite(x, agent_source) >= 0.80)
                if daira_choisie:
                    # ✅ Filtre intelligent : daïra OU communes de la daïra
                    communes_daira = communes_de_daira(daira_choisie)
                    def match_zone(row):
                        d = str(row.get('daira','')).strip().upper()
                        c = str(row.get('commune','')).strip().upper()
                        if daira_choisie.upper() in d:
                            return True
                        for com in communes_daira:
                            com_n = unicodedata.normalize('NFKD', com.upper()).encode('ascii','ignore').decode('ascii')
                            if com_n in unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii'):
                                return True
                        return False
                    mask = mask & df_pass.apply(match_zone, axis=1)
                if commune_choisie:
                    mask = mask & df_pass['commune'].str.contains(commune_choisie, case=False, na=False)
                df_concernes = df_pass[mask]
                st.metric("Dossiers concernés", len(df_concernes))
                if not df_concernes.empty:
                    st.dataframe(df_concernes[['identifiant','nom','prenom','daira','commune']].head(10), use_container_width=True)
            except Exception:
                df_concernes = pd.DataFrame()

            if st.button("📦 Confirmer la passation", type="primary", key="btn_passation",
                         disabled=df_concernes.empty if not df_concernes.empty else True):
                date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                note = f"🔄 **[Passation {date_str}]** Transféré de {agent_source} vers {agent_dest}"
                if motif:
                    note += f" — Motif : {motif}"
                with get_session() as session:
                    c = 0
                    for _, row in df_concernes.iterrows():
                        d = session.get(Dossier, int(row['id']))
                        if d:
                            d.gestionnaire = agent_dest.strip().upper()
                            d.historique_visites = note + "\n" + (d.historique_visites or "")
                            c += 1
                st.success(f"✅ {c} dossiers transférés de **{agent_source}** vers **{agent_dest}**.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # OUTIL 3 — RÉÉCRITURE DES NOMS
    # ==========================================
    with sous_tabs[2]:
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        st.info("Scanne toute la base et corrige les noms de gestionnaires mal écrits pour les aligner sur les comptes officiels.")

        with get_session() as session:
            agents_officiels = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]

        env_ree = st.session_state.user['env']

        if st.button("🔍 Analyser la base", key="btn_analyse_noms"):
            try:
                with engine.connect() as conn:
                    df_all = pd.read_sql_query(
                        text("SELECT id, gestionnaire FROM dossiers WHERE type_dispositif=:env"),
                        conn, params={"env": env_ree}
                    ).fillna('')
            except Exception:
                df_all = pd.DataFrame()

            corrections = []
            for _, row in df_all.iterrows():
                gest = str(row['gestionnaire']).strip()
                if not gest or gest.upper() in ('NAN','NONE',''):
                    continue
                meilleur = max(agents_officiels, key=lambda a: similarite(gest, a), default=None)
                if meilleur and similarite(gest, meilleur) >= 0.80 and gest != meilleur:
                    corrections.append({'id': row['id'], 'avant': gest, 'apres': meilleur})

            if not corrections:
                st.success("✅ Tous les noms sont déjà corrects.")
            else:
                df_corr = pd.DataFrame(corrections)
                st.warning(f"**{len(df_corr)}** corrections à appliquer :")
                st.dataframe(df_corr[['avant','apres']], use_container_width=True, hide_index=True)
                if st.button(f"✏️ Appliquer {len(df_corr)} corrections", type="primary", key="btn_appliquer_noms"):
                    with get_session() as session:
                        for corr in corrections:
                            d = session.get(Dossier, corr['id'])
                            if d:
                                d.gestionnaire = corr['apres']
                    st.success(f"✅ {len(corrections)} noms corrigés dans la base.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def _onglet_import_generique(file_obj, env, badge, form_key, label):
    try:
        df_raw = safe_read_dataframe(file_obj)
    except Exception as e:
        st.error(f"Erreur : {e}")
        return
    df_raw = df_raw.fillna('')
    header_idx = get_header_row(df_raw)
    df = df_raw.iloc[header_idx:].copy()
    df.columns = df.iloc[0].astype(str).tolist()
    df = df.iloc[1:].reset_index(drop=True)
    mapping_auto = auto_mapper(list(df.columns))
    excel_cols = ["-- Ignorer --"] + list(df.columns)
    st.success(f"✅ {len(mapping_auto)} colonnes détectées sur {len(df.columns)}")
    st.dataframe(df.head(3), use_container_width=True)
    with st.form(form_key):
        st.write(f"### 🎛️ Mapping — {label}")
        targets = list(MAPPING_CONFIG_KEYWORDS.keys())
        c1, c2, c3 = st.columns(3)
        mapping_final = {}
        for idx, db_f in enumerate(targets):
            auto_val = mapping_auto.get(db_f, "-- Ignorer --")
            auto_idx = excel_cols.index(auto_val) if auto_val in excel_cols else 0
            col = c1 if idx % 3 == 0 else c2 if idx % 3 == 1 else c3
            with col:
                mapping_final[db_f] = st.selectbox(f"`{db_f}`", excel_cols, index=auto_idx, key=f"{form_key}_{db_f}")
        sub = st.form_submit_button(f"🚀 Importer {label}", type="primary")
    if sub:
        if badge == 'gestionnaire_only':
            _import_gestionnaires(df, mapping_final, env)
        else:
            with get_session() as session:
                agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
                with st.status("Import en cours...", expanded=True) as status:
                    stats = moteur_import(df, mapping_final, env, badge, session, agents_db)
                status.update(label="✅ Terminé !", state="complete")
            st.success(f"**{stats['crees']}** créés | **{stats['mis_a_jour']}** mis à jour | **{stats['ignores']}** ignorés")
            if stats['erreurs']:
                with st.expander(f"🔴 {len(stats['erreurs'])} erreurs"):
                    for e in stats['erreurs'][:20]:
                        st.code(e)

def _import_gestionnaires(df, mapping, env):
    with get_session() as session:
        agents_db = [a.nom for a in session.query(UtilisateurAuth).filter_by(role='agent').all()]
        c_affect = 0
        for _, row in df.iterrows():
            xl_id   = mapping.get('identifiant', '-- Ignorer --')
            xl_gest = mapping.get('gestionnaire', '-- Ignorer --')
            if xl_id == '-- Ignorer --' or xl_gest == '-- Ignorer --':
                continue
            ident = clean_identifiant(row.get(xl_id, ''))
            gest  = trouver_agent_intelligent(row.get(xl_gest, ''), agents_db)
            if not ident or not gest:
                continue
            dossiers = session.query(Dossier).filter_by(identifiant=ident, type_dispositif=env).all()
            for d in dossiers:
                d.gestionnaire = gest
                c_affect += 1
    st.success(f"✅ {c_affect} fiches affectées.")

# ==========================================
# CORBEILLE
# ==========================================

def page_corbeille():
    env   = st.session_state.user['env']
    agent = st.session_state.user['nom']
    daira = st.session_state.user.get('daira', '').strip()
    st.title("🗑️ Corbeille — Dossiers non assignés")

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM dossiers WHERE type_dispositif=:env ORDER BY id DESC"),
                conn, params={"env": env}
            ).fillna('')
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("La base est vide.")
        return

    def est_non_assigne(val):
        return str(val).strip().upper() in ('', 'NAN', 'NONE', 'NON', '-', 'N/A')

    df_non_assignes = df[df['gestionnaire'].apply(est_non_assigne)].copy()
    if df_non_assignes.empty:
        st.success("✅ Tous les dossiers sont assignés.")
        return

    if daira:
        # ✅ Détection intelligente : daïra → communes → adresse
        ma_daira = daira.strip()
        ma_daira_norm = unicodedata.normalize('NFKD', ma_daira.upper()).encode('ascii','ignore').decode('ascii')
        communes_ma_daira = communes_de_daira(ma_daira)
        communes_norm = [unicodedata.normalize('NFKD', c.upper()).encode('ascii','ignore').decode('ascii') for c in communes_ma_daira]
        def ma_zone(row):
            d = str(row.get('daira','')).strip().upper()
            c = str(row.get('commune','')).strip().upper()
            a = str(row.get('adresse','')).strip().upper()
            d_n = unicodedata.normalize('NFKD', d).encode('ascii','ignore').decode('ascii')
            c_n = unicodedata.normalize('NFKD', c).encode('ascii','ignore').decode('ascii')
            a_n = unicodedata.normalize('NFKD', a).encode('ascii','ignore').decode('ascii')
            # 1. Daïra match
            if ma_daira_norm in d_n:
                return True
            # 2. Commune match
            for com_n in communes_norm:
                if com_n and com_n in c_n:
                    return True
            # 3. Adresse match
            for com_n in communes_norm:
                if com_n and com_n in a_n:
                    return True
            if ma_daira_norm in a_n:
                return True
            # 4. Aucune zone définie → visible pour tous
            if not d_n and not c_n and not a_n:
                return True
            return False
        orphans = df_non_assignes[df_non_assignes.apply(ma_zone, axis=1)].copy()
    else:
        st.warning("⚠️ Pas de Daïra assignée — vous voyez tous les dossiers non assignés.")
        orphans = df_non_assignes.copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total non assignés", len(df_non_assignes))
    c2.metric(f"Dans votre zone ({daira or 'toutes'})", len(orphans))
    nb_sans_zone = len(df_non_assignes[df_non_assignes.apply(
        lambda r: not str(r.get('daira','')).strip() and not str(r.get('commune','')).strip(), axis=1)])
    c3.metric("Sans zone définie", nb_sans_zone)

    if orphans.empty:
        st.success(f"✅ Aucun dossier orphelin dans votre secteur.")
        return

    rech = st.text_input("🔍 Filtrer...", placeholder="Nom, ID, commune...")
    if rech:
        orphans = orphans[orphans.apply(lambda x: x.astype(str).str.contains(rech, case=False).any(), axis=1)]

    st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
    orphans_aff = orphans.copy()
    orphans_aff["✅ C'est le mien !"] = False
    cols_aff = [c for c in ["✅ C'est le mien !","identifiant","nom","prenom","activite","commune","daira","montant_pnr","id"]
                if c in orphans_aff.columns or c == "✅ C'est le mien !"]
    ed = st.data_editor(orphans_aff[cols_aff], hide_index=True, use_container_width=True, height=500,
        column_config={
            "id": None,
            "✅ C'est le mien !": st.column_config.CheckboxColumn("Prendre", default=False),
            "montant_pnr": st.column_config.NumberColumn("PNR (DA)", format="%d DA"),
        })
    ids_sel = ed[ed["✅ C'est le mien !"] == True]['id'].tolist()
    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        if ids_sel:
            st.info(f"**{len(ids_sel)} dossier(s) sélectionné(s)**")
        else:
            st.caption("Cochez les dossiers à prendre en charge.")
    with col_b2:
        if st.button(f"📥 M'attribuer {len(ids_sel)} dossier(s)", type="primary",
                     use_container_width=True, disabled=(len(ids_sel) == 0)):
            with get_session() as session:
                session.query(Dossier).filter(Dossier.id.in_(ids_sel)).update(
                    {"gestionnaire": agent.strip().upper(), "est_nouveau": "NON"},
                    synchronize_session=False)
            st.success(f"✅ {len(ids_sel)} dossier(s) attribués à {agent}.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# ROUTEUR PRINCIPAL
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    page = sidebar_menu()
    if "Administration" in page or "Import" in page:
        page_integration_admin()
    elif "Bilans" in page:
        page_bilans()
    elif "Corbeille" in page:
        page_corbeille()
    elif "Mes Dossiers" in page:
        page_gestion(mode="unifie", vue_admin=("admin" == st.session_state.user['role'])) 
