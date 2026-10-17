"""Executive overview page (Bilingual: Tiếng Việt & English)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components import (
    download_frame,
    format_compact_number,
    format_decimal,
    format_percent,
    insight_card,
    load_repository_data,
    page_header,
    plotly_chart,
    require_columns,
)
from dashboard.data import AnalyticsRepository
from dashboard.i18n import t, get_current_lang
from dashboard.styles import COLORS, SEQUENTIAL_SCALE, style_figure


def _condense_departments(frame: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    ordered = frame.sort_values("market_share_pct", ascending=False).reset_index(drop=True)
    leaders = ordered.head(top_n).copy()
    remainder = ordered.iloc[top_n:]
    if not remainder.empty:
        other_label = "Ngành hàng khác" if get_current_lang() == "vi" else "All other departments"
        leaders.loc[len(leaders)] = {
            "department_name": other_label,
            "orders": remainder["orders"].sum(),
            "total_items": remainder["total_items"].sum(),
            "reorder_rate_pct": (
                (remainder["reorder_rate_pct"] * remainder["total_items"]).sum()
                / remainder["total_items"].sum()
            ),
            "unique_products": remainder["unique_products"].sum(),
            "market_share_pct": remainder["market_share_pct"].sum(),
        }
    return leaders.sort_values("market_share_pct", ascending=True)


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("ov_title"),
        t("ov_summary"),
        eyebrow=t("ov_eyebrow"),
    )

    kpis = load_repository_data(
        repository,
        "overview_kpis",
        loading_label="Loading snapshot KPIs…",
    )
    if not require_columns(
        kpis,
        (
            "total_orders",
            "total_users",
            "total_products",
            "avg_basket_size",
            "avg_reorder_rate_pct",
        ),
        context="Overview KPI",
    ):
        return

    row = kpis.iloc[0]
    st.subheader("Key Performance Indicators (KPIs)")
    first, second = st.columns(2)
    with first:
        orders, customers = st.columns(2)
        orders.metric(t("kpi_orders"), format_compact_number(row["total_orders"]))
        customers.metric(t("kpi_users"), format_compact_number(row["total_users"]))
    with second:
        basket, reorder = st.columns(2)
        basket.metric(t("kpi_basket"), format_decimal(row["avg_basket_size"]))
        reorder.metric(
            t("kpi_reorder"),
            format_percent(row["avg_reorder_rate_pct"]),
        )
    
    cap_text = (
        f"Quy mô danh mục: {format_compact_number(row['total_products'])} sản phẩm · "
        f"{format_compact_number(row.get('total_departments'))} ngành hàng · "
        f"{format_compact_number(row.get('total_aisles'))} kệ hàng."
        if get_current_lang() == "vi"
        else f"Catalogue coverage: {format_compact_number(row['total_products'])} products · "
        f"{format_compact_number(row.get('total_departments'))} departments · "
        f"{format_compact_number(row.get('total_aisles'))} aisles."
    )
    st.caption(cap_text)

    day = load_repository_data(
        repository,
        "day_trends",
        loading_label="Loading day-of-week distribution…",
    )
    hour = load_repository_data(
        repository,
        "hour_trends",
        loading_label="Loading hourly distribution…",
    )
    departments = load_repository_data(
        repository,
        "departments",
        loading_label="Loading department mix…",
    )

    st.subheader(t("sec_weekly"))
    day_ok = require_columns(day, ("dow_name", "orders", "share_pct"), context="Daily trend")
    hour_ok = require_columns(
        hour,
        ("order_hour", "orders", "share_pct"),
        context="Hourly trend",
    )
    left, right = st.columns(2)
    if day_ok:
        with left:
            day_chart = px.bar(
                day,
                x="dow_name",
                y="orders",
                labels={"dow_name": t("chart_dow"), "orders": t("chart_orders")},
            )
            day_chart.update_traces(marker_color=COLORS["primary"])
            style_figure(day_chart)
            plotly_chart(day_chart, key="overview-day-distribution")
    if hour_ok:
        with right:
            hour_chart = px.area(
                hour,
                x="order_hour",
                y="orders",
                labels={"order_hour": t("chart_hour"), "orders": t("chart_orders")},
            )
            hour_chart.update_traces(
                line_color=COLORS["blue"],
                fillcolor="rgba(47, 107, 255, 0.15)",
            )
            style_figure(hour_chart)
            hour_chart.update_xaxes(dtick=2)
            plotly_chart(hour_chart, key="overview-hour-distribution")

    st.subheader(t("sec_dept_share"))
    if require_columns(
        departments,
        ("department_name", "total_items", "market_share_pct"),
        context="Department mix",
    ):
        condensed = _condense_departments(departments)
        dept_chart = px.bar(
            condensed,
            x="market_share_pct",
            y="department_name",
            orientation="h",
            labels={
                "department_name": "Department",
                "market_share_pct": "Market share (%)",
            },
            color="market_share_pct",
            color_continuous_scale=SEQUENTIAL_SCALE,
        )
        style_figure(dept_chart)
        dept_chart.update_coloraxes(showscale=False)
        plotly_chart(dept_chart, key="overview-department-share")

    btn_label = "Tải xuống dữ liệu tổng hợp KPI (CSV)" if get_current_lang() == "vi" else "Download snapshot summary (CSV)"
    download_frame(
        kpis,
        filename="instacart_overview_kpis.csv",
        label=btn_label,
        key="download-overview-kpis",
    )
