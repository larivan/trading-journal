import streamlit as st
from db import init_db
from config import PAGES

init_db()

# Определение страниц
nav_pages = []
for page in PAGES.items():
    name, options = page
    nav_pages.append(
        st.Page(
            f"pages/{name}.py",
            title=options['title'],
            icon=options['icon'],
            url_path=name,
            default=options['default']
        )
    )

# Установка и зауск навигации
st.navigation(nav_pages).run()
