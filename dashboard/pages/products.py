"""Product and aisle analytics page (Bilingual: Tiếng Việt & English)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard.components import (
    download_frame,
    format_integer,
    format_percent,
    insight_card,
    load_repository_data,
    page_header,
    plotly_chart,
    require_columns,
)
from dashboard.data import AnalyticsRepository
from dashboard.i18n import t, get_current_lang
from dashboard.styles import SEQUENTIAL_SCALE, style_figure


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("prod_title"),
        t("prod_summary"),
        eyebrow=t("prod_eyebrow"),
    )

    departments = load_repository_data(
        repository,
        "departments",
        loading_label="Loading department filters…",
    )
    all_label = t("all_depts")
    department_options = [all_label]
    if require_columns(
        departments,
        ("department_name",),
        context="Department filter",
    ):
        department_options.extend(
            sorted(departments["department_name"].dropna().astype(str).unique())
        )

    st.subheader(t("sec_prod_rank"))
    filter_left, filter_right = st.columns(2)
    with filter_left:
        selected_department = st.selectbox(
            t("filter_dept"),
            department_options,
            help="Restricts the warehouse aggregate before ranking products.",
        )
    with filter_right:
        visible_limit = st.slider(
            t("prod_shown"),
            min_value=5,
            max_value=30,
            value=15,
            step=5,
        )

    repository_department = (
        None if selected_department == all_label else selected_department
    )
    products = load_repository_data(
        repository,
        "products",
        loading_label="Loading product ranking…",
        limit=100,
        department=repository_department,
    )
    product_ok = require_columns(
        products,
        (
            "product_name",
            "department_name",
            "aisle_name",
            "orders",
            "total_items",
            "reorder_rate_pct",
        ),
        context="Product ranking",
    )
    if product_ok:
        search_term = st.text_input(
            t("prod_search"),
            placeholder=t("prod_search_ph"),
            help=(
                "This is a client-side search over the ranked result set, not a "
                "full-catalogue database search."
            ),
        ).strip()
        filtered = products
        if search_term:
            filtered = products[
                products["product_name"]
                .astype(str)
                .str.contains(
                    search_term,
                    case=False,
                    regex=False,
                    na=False,
                )
            ]
        visible = filtered.head(visible_limit).copy()
        if visible.empty:
            no_match_text = "Không tìm thấy sản phẩm nào phù hợp với từ khóa này." if get_current_lang() == "vi" else "No loaded top product matches this search. Clear the search to continue."
            st.info(no_match_text)
        else:
            chart_frame = visible.sort_values("orders", ascending=True)
            y_label = "Sản phẩm" if get_current_lang() == "vi" else "Product"
            x_label = "Số lượt đặt mua" if get_current_lang() == "vi" else "Distinct orders"
            reorder_label = "Tỷ lệ mua lại (%)" if get_current_lang() == "vi" else "Reorder rate (%)"
            product_chart = px.bar(
                chart_frame,
                x="orders",
                y="product_name",
                orientation="h",
                color="reorder_rate_pct",
                color_continuous_scale=SEQUENTIAL_SCALE,
                labels={
                    "orders": x_label,
                    "product_name": y_label,
                    "reorder_rate_pct": reorder_label,
                },
                hover_data={"department_name": True, "aisle_name": True},
            )
            product_chart.update_traces(
                hovertemplate=(
                    "%{y}<br>%{x:,.0f} " + x_label + "<br>" + reorder_label + ": %{marker.color:.1f}%<extra></extra>"
                )
            )
            height = max(400, min(720, 34 * len(chart_frame) + 180))
            plotly_chart(
                style_figure(product_chart, height=height),
                key="products-ranking",
            )
            leader = visible.iloc[0]
            leader_title = "Sản phẩm dẫn đầu sản lượng" if get_current_lang() == "vi" else "Highest-volume result"
            leader_desc = (
                f"Sản phẩm <b>{leader['product_name']}</b> xuất hiện trong {format_integer(leader['orders'])} "
                f"đơn hàng với tỷ lệ mua lại {format_percent(leader['reorder_rate_pct'])}."
                if get_current_lang() == "vi"
                else f"{leader['product_name']} appears in {format_integer(leader['orders'])} "
                f"distinct orders with a {format_percent(leader['reorder_rate_pct'])} reorder rate."
            )
            insight_card(leader_title, leader_desc)
            st.dataframe(
                visible,
                width="stretch",
                hide_index=True,
                column_config={
                    "orders": st.column_config.NumberColumn(format="%d"),
                    "total_items": st.column_config.NumberColumn(format="%d"),
                    "reorder_rate_pct": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )
            dl_label = "Tải xuống danh sách sản phẩm lọc (CSV)" if get_current_lang() == "vi" else "Download filtered products"
            download_frame(
                visible,
                label=dl_label,
                filename="instacart-product-ranking.csv",
                key="products-download",
            )

    st.subheader(t("sec_aisle_perf"))
    aisle_left, aisle_right = st.columns(2)
    with aisle_left:
        support_label = "Ngưỡng mặt hàng tối thiểu (Line items)" if get_current_lang() == "vi" else "Minimum line-item support"
        min_items = int(
            st.number_input(
                support_label,
                min_value=0,
                max_value=1_000_000,
                value=10_000,
                step=5_000,
                help="Loại bỏ các kệ hàng quá nhỏ để tỷ lệ mua lại có ý nghĩa thống kê.",
            )
        )
    with aisle_right:
        aisle_limit = st.slider(
            "Số lượng kệ hàng hiển thị" if get_current_lang() == "vi" else "Aisles shown",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
        )
    aisles = load_repository_data(
        repository,
        "aisles",
        loading_label="Loading aisle aggregates…",
        limit=aisle_limit,
        min_items=min_items,
    )
    aisle_ok = require_columns(
        aisles,
        ("aisle_name", "reorder_rate_pct", "items"),
        context="Aisle ranking",
    )
    if aisle_ok:
        aisle_chart_frame = aisles.sort_values("reorder_rate_pct", ascending=True)
        aisle_y = "Kệ hàng" if get_current_lang() == "vi" else "Aisle"
        aisle_x = "Tỷ lệ mua lại (%)" if get_current_lang() == "vi" else "Reorder rate (%)"
        aisle_color = "Số lượng mặt hàng" if get_current_lang() == "vi" else "Line items"
        aisle_chart = px.bar(
            aisle_chart_frame,
            x="reorder_rate_pct",
            y="aisle_name",
            orientation="h",
            color="items",
            color_continuous_scale=SEQUENTIAL_SCALE,
            labels={
                "reorder_rate_pct": aisle_x,
                "aisle_name": aisle_y,
                "items": aisle_color,
            },
        )
        aisle_chart.update_traces(
            hovertemplate=(
                "%{y}<br>" + aisle_x + ": %{x:.1f}%<br>%{marker.color:,.0f} " + aisle_color + "<extra></extra>"
            )
        )
        plotly_chart(
            style_figure(aisle_chart, height=max(420, 32 * len(aisles) + 160)),
            key="products-aisle-ranking",
        )
        best_aisle = aisles.loc[aisles["reorder_rate_pct"].idxmax()]
        best_aisle_title = "Kệ hàng có độ trung thành cao nhất" if get_current_lang() == "vi" else "Strongest repeat signal"
        best_aisle_desc = (
            f"Kệ hàng <b>{str(best_aisle['aisle_name']).title()}</b> dẫn đầu với tỷ lệ mua lại {format_percent(best_aisle['reorder_rate_pct'])}."
            if get_current_lang() == "vi"
            else f"{str(best_aisle['aisle_name']).title()} leads this supported set at {format_percent(best_aisle['reorder_rate_pct'])}."
        )
        insight_card(best_aisle_title, best_aisle_desc)
        st.dataframe(
            aisles,
            width="stretch",
            hide_index=True,
            column_config={
                "reorder_rate_pct": st.column_config.NumberColumn(format="%.1f%%"),
                "items": st.column_config.NumberColumn(format="%d"),
            },
        )
