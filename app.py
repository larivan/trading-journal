import sys
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
from utils.backup import maybe_create_daily_backup

init_db()

try:
    maybe_create_daily_backup()
except Exception:
    pass

# Восстанавливаем сессию из cookie при каждом новом подключении
# (F5, рестарт сервера, hot-reload). Должно быть ДО require_auth().
try:
    _dbg_cookies = dict(st.context.cookies)
    _dbg_token = _dbg_cookies.get("tj_session", "<not found>")
    print(f"[AUTH DEBUG] cookies keys: {list(_dbg_cookies.keys())}", file=sys.stderr)
    print(f"[AUTH DEBUG] tj_session present: {'tj_session' in _dbg_cookies}", file=sys.stderr)
    print(f"[AUTH DEBUG] token prefix: {_dbg_token[:20] if _dbg_token != '<not found>' else _dbg_token}", file=sys.stderr)
except Exception as _dbg_e:
    print(f"[AUTH DEBUG] st.context.cookies error: {_dbg_e}", file=sys.stderr)
try:
    _dbg_headers = dict(st.context.headers)
    _dbg_cookie_hdr = _dbg_headers.get("cookie", _dbg_headers.get("Cookie", "<missing>"))
    print(f"[AUTH DEBUG] header Cookie: {_dbg_cookie_hdr[:80] if _dbg_cookie_hdr != '<missing>' else _dbg_cookie_hdr}", file=sys.stderr)
    print(f"[AUTH DEBUG] header Host: {_dbg_headers.get('host', _dbg_headers.get('Host', '<missing>'))}", file=sys.stderr)
except Exception as _dbg_e2:
    print(f"[AUTH DEBUG] st.context.headers error: {_dbg_e2}", file=sys.stderr)

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
