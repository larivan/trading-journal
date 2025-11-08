import streamlit as st
from db import init_db
from config import PAGES

init_db()

# Определение страниц
pages = []
for page in PAGES.items():
    name, options = page
    pages.append(
        st.Page(
            f"pages/{name}.py",
            title=options['title'],
            icon=options['icon'],
            url_path=name,
            default=options['default']
        )
    )


# Регистрация страниц
st.navigation(pages, position="hidden").run()

# Кастомная боковая навигация (показываем только основные страницы)
with st.sidebar:
    st.markdown("## Navigation")
    for page in PAGES.items():
        name, options = page
        if options['in_nav']:
            st.page_link(
                f"pages/{name}.py",
                label=options['title'],
                icon=options['icon']
            )
    st.divider()