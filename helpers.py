from config import PAGES


def apply_page_config(page_key: str):
    import streamlit as st
    options = PAGES.get(page_key)
    st.set_page_config(
        page_title=options['title'],
        page_icon=options["icon"],
        layout=options["layout"]
    )
    st.title(f"{options["icon"]} {options['title']}")


def apply_page_config_from_file(file):
    from pathlib import Path
    return apply_page_config(Path(file).stem)
