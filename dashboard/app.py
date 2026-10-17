"""Instacart Decision Intelligence Streamlit entry point (Bilingual: Tiếng Việt & English)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Instacart Decision Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "Instacart Decision Intelligence explores a batch-loaded public "
            "market-basket dataset through a reproducible analytics contract."
        )
    },
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components import clear_data_cache, render_source_status
from dashboard.data import AnalyticsRepository, create_repository
from dashboard.i18n import t, get_current_lang
from dashboard.pages import customers, departments, overview, products, tables, time_analysis
from dashboard.styles import inject_global_styles

PageRenderer = Callable[[AnalyticsRepository], None]


@st.cache_resource(show_spinner=False)
def initialize_repository() -> AnalyticsRepository:
    """Create checked DuckDB repository resource for Streamlit."""
    return create_repository()


def render_sidebar(repository: AnalyticsRepository) -> tuple[str, PageRenderer]:
    # 1. Bộ chuyển đổi ngôn ngữ (Language Switcher)
    st.sidebar.markdown("### 🌐 Language / Ngôn ngữ")
    current_lang = get_current_lang()
    selected_lang_name = st.sidebar.radio(
        "Select Language",
        ["🇻🇳 Tiếng Việt", "🇬🇧 English"],
        index=0 if current_lang == "vi" else 1,
        label_visibility="collapsed",
    )
    new_lang = "vi" if "Tiếng Việt" in selected_lang_name else "en"
    if new_lang != current_lang:
        st.session_state["lang"] = new_lang
        st.rerun()

    st.sidebar.divider()
    st.sidebar.title(t("app_title"))
    st.sidebar.caption(t("app_caption"))
    st.sidebar.divider()

    # 2. Danh sách trang hiển thị đa ngôn ngữ
    pages_map = {
        t("page_overview"): overview.show,
        t("page_products"): products.show,
        t("page_rhythm"): time_analysis.show,
        t("page_customers"): customers.show,
        t("page_departments"): departments.show,
        t("page_tables"): tables.show,
    }

    selected_page_label = st.sidebar.radio(
        t("workspace"),
        list(pages_map.keys()),
        index=0,
    )
    st.sidebar.divider()

    metadata = repository.source_metadata
    st.sidebar.markdown(f"**{t('data_source')}**")
    st.sidebar.caption(t("source_status"))
    st.sidebar.caption(t("ready_status"))

    if st.sidebar.button(t("refresh_btn"), use_container_width=True):
        clear_data_cache()
        initialize_repository.clear()
        st.rerun()

    st.sidebar.caption(t("date_note"))
    return selected_page_label, pages_map[selected_page_label]


def main() -> None:
    inject_global_styles()
    try:
        repository = initialize_repository()
    except Exception as exc:
        st.error(f"The analytics source could not be initialized: {exc}")
        st.stop()

    page_label, page_renderer = render_sidebar(repository)
    render_source_status(repository.source_metadata)
    
    # Thực thi trang hiện tại
    page_renderer(repository)
    
    st.divider()
    st.caption(t("footer"))


if __name__ == "__main__":
    main()
