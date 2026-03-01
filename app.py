import logging
import streamlit as st
from db import init_db

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
from config import PAGES, SETTINGS_PAGES
from utils.auth import (
    require_auth,
    get_current_user_id,
    logout,
    ensure_user_from_oauth,
)
from utils.backup import maybe_create_daily_backup

init_db()

try:
    maybe_create_daily_backup()
except Exception:
    pass


def _login_page() -> None:
    st.set_page_config(
        page_title="Trading Workspace — Sign in",
        page_icon=":material/lock:",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("Trading Workspace")
    st.button("Sign in with Google", on_click=st.login, args=("google",))


if not st.user.is_logged_in:
    pg = st.navigation(
        [st.Page(_login_page, title="Sign in", url_path="login", default=True)],
        position="hidden",
    )
    pg.run()
else:
    # Загружаем user_id в session_state (один раз за WebSocket-сессию)
    if not require_auth():
        ensure_user_from_oauth()

    main_pages = []
    for name, options in PAGES.items():
        main_pages.append(
            st.Page(
                f"pages/{name}.py",
                title=options["title"],
                icon=options["icon"],
                url_path=name,
                default=options["default"],
            )
        )

    settings_pages = []
    for name, options in SETTINGS_PAGES.items():
        settings_pages.append(
            st.Page(
                f"pages/{name}.py",
                title=options["title"],
                icon=options["icon"],
                url_path=name,
                default=options["default"],
            )
        )

    # Регистрируем навигацию первой — ссылки окажутся вверху сайдбара
    nav = st.navigation({"": main_pages, "Settings": settings_pages})

    # Никнейм и Logout — прижаты к низу через CSS
    with st.sidebar:
        st.markdown(
            """
            <style>
            [data-testid="stSidebarContent"] {
                display: flex !important;
                flex-direction: column !important;
                height: 100% !important;
            }
            [data-testid="stSidebarUserContent"] {
                margin-top: auto !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        user_id = get_current_user_id()
        if "sidebar_user" not in st.session_state:
            from db import get_user_by_id
            st.session_state["sidebar_user"] = get_user_by_id(user_id) if user_id else None
        user = st.session_state["sidebar_user"]
        if user:
            name = user.get("username") or user.get("email", "")
            st.write(f"👤 {name}")
        if st.button("Logout", key="sidebar_logout", width="stretch"):
            logout()
            st.logout()

    nav.run()
