import streamlit as st
from db import init_db
from config import PAGES, SETTINGS_PAGES
from utils.auth import (
    render_login_form,
    require_auth,
    get_current_user_id,
    logout,
    try_restore_from_cookie,
    set_session_cookie,
    clear_session_cookie,
)
from utils.backup import create_backup

init_db()

try:
    create_backup()
except Exception:
    pass

# Восстанавливаем сессию из cookie при каждом новом подключении
# (F5, рестарт сервера, hot-reload). Должно быть ДО require_auth().
try_restore_from_cookie()


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
    # Устанавливаем/обновляем session cookie один раз за сессию.
    # Делаем это здесь (не в _login_page перед st.rerun()), чтобы JavaScript
    # гарантированно выполнился в браузере — цикл рендеринга не прерывается
    # немедленным rerun.
    if not st.session_state.get("_cookie_set"):
        set_session_cookie()
        st.session_state["_cookie_set"] = True

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
        from db import get_user_by_id
        user = get_user_by_id(user_id) if user_id else None
        if user:
            st.write(f"👤 {user['username']}")
        if st.button("Logout", key="sidebar_logout", width="stretch"):
            logout()
            clear_session_cookie()
            st.rerun()

    nav.run()
