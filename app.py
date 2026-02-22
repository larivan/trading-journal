import streamlit as st
from db import init_db
from config import PAGES
from utils.auth import render_login_form, require_auth, get_current_user_id, logout
from utils.backup import create_backup

init_db()

try:
    create_backup()
except Exception:
    pass


def _login_page() -> None:
    """Страница входа / регистрации — показывается неаутентифицированным пользователям."""
    st.set_page_config(
        page_title="Trade Journal — Sign in",
        page_icon=":material/lock:",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("Trade Journal")
    logged_in = render_login_form()
    if logged_in:
        st.rerun()


if not require_auth():
    # Регистрируем ТОЛЬКО страницу входа — другие страницы недоступны.
    # position="hidden" убирает боковое меню навигации.
    pg = st.navigation(
        [st.Page(_login_page, title="Sign in", url_path="login", default=True)],
        position="hidden",
    )
    pg.run()
else:
    # Logout в sidebar
    with st.sidebar:
        user_id = get_current_user_id()
        from db import get_user_by_id
        user = get_user_by_id(user_id) if user_id else None
        if user:
            st.write(f"👤 {user['username']}")
        if st.button("Logout", key="sidebar_logout"):
            logout()
            st.rerun()

    pages = []
    for name, options in PAGES.items():
        pages.append(
            st.Page(
                f"pages/{name}.py",
                title=options["title"],
                icon=options["icon"],
                url_path=name,
                default=options["default"],
            )
        )

    st.navigation(pages).run()
