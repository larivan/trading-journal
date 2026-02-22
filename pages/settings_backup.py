"""Страница резервного копирования базы данных."""

from datetime import datetime

import streamlit as st

from utils.backup import create_backup, get_backup_bytes, list_backups

st.set_page_config(
    page_title="Backup",
    page_icon=":material/backup:",
    layout="wide",
)

st.title(":material/backup: Backup")

col_create, col_info = st.columns([0.3, 0.7])
with col_create:
    if st.button("Create backup now", type="primary"):
        try:
            path = create_backup()
            st.success(f"Backup created: {path.name}")
            st.rerun()
        except Exception as exc:
            st.error(f"Backup failed: {exc}")

col_list, col_restore = st.columns([0.55, 0.45])

with col_list:
    backups = list_backups()
    if not backups:
        st.info("No backups yet.")
    else:
        st.markdown(f"**{len(backups)} backup(s) stored**")
        for bp in backups:
            size_kb = bp.stat().st_size / 1024
            try:
                ts = datetime.strptime(
                    bp.stem.replace("journal_backup_", ""), "%Y%m%d_%H%M%S"
                )
                label = ts.strftime("%b %d, %Y  %H:%M:%S")
            except ValueError:
                label = bp.stem
            b_col1, b_col2 = st.columns([0.7, 0.3])
            b_col1.text(f"{label}  ({size_kb:.1f} KB)")
            b_col2.download_button(
                label="Download",
                data=get_backup_bytes(bp),
                file_name=bp.name,
                mime="application/octet-stream",
                key=f"download_{bp.name}",
            )

with col_restore:
    st.markdown("##### Restore from file")
    st.warning(
        "Restoring will overwrite the current database. "
        "Make sure to create a backup first."
    )
    uploaded = st.file_uploader(
        "Upload backup file (.db)",
        type=["db"],
        key="restore_uploader",
    )
    if uploaded:
        if st.button("Restore database", type="secondary"):
            from db.connection import DB_PATH
            try:
                with open(DB_PATH, "wb") as f:
                    f.write(uploaded.read())
                st.success("Database restored. Please restart the application.")
            except Exception as exc:
                st.error(f"Restore failed: {exc}")
