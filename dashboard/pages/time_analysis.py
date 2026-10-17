"""Shopping rhythm analysis page (Bilingual: Tiếng Việt & English)."""

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
from dashboard.styles import CATEGORICAL_PALETTE, COLORS, style_figure


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("time_title"),
        t("time_summary"),
        eyebrow=t("time_eyebrow"),
    )

    day = load_repository_data(
        repository,
        "day_trends",
        loading_label="Loading day-of-week aggregates…",
    )
    hour = load_repository_data(
        repository,
        "hour_trends",
        loading_label="Loading hour aggregates…",
    )
    comparison = load_repository_data(
        repository,
        "weekend_comparison",
        loading_label="Loading normalized weekday comparison…",
    )

    day_ok = require_columns(
        day,
        ("order_dow", "dow_name", "orders", "share_pct"),
        context="Day-of-week",
    )
    hour_ok = require_columns(
        hour,
        ("order_hour", "orders", "share_pct"),
        context="Hour-of-day",
    )

    st.subheader(t("sec_dow_pattern"))
    left, right = st.columns(2)
    if day_ok:
        with left:
            chart_dow_title = "Tỷ trọng đơn hàng theo ngày" if get_current_lang() == "vi" else "Share of orders by day"
            day_chart = px.bar(
                day.sort_values("order_dow"),
                x="dow_name",
                y="share_pct",
                title=chart_dow_title,
                labels={"dow_name": t("chart_dow"), "share_pct": "Tỷ trọng (%)" if get_current_lang() == "vi" else "Order share (%)"},
                color_discrete_sequence=[COLORS["blue"]],
            )
            day_chart.update_traces(hovertemplate="%{x}<br>%{y:.1f}% tổng đơn<extra></extra>")
            plotly_chart(style_figure(day_chart), key="time-day-share")
    if hour_ok:
        with right:
            chart_hour_title = "Tỷ trọng đơn hàng theo giờ" if get_current_lang() == "vi" else "Share of orders by hour"
            hour_chart = px.line(
                hour.sort_values("order_hour"),
                x="order_hour",
                y="share_pct",
                markers=True,
                title=chart_hour_title,
                labels={"order_hour": t("chart_hour"), "share_pct": "Tỷ trọng (%)" if get_current_lang() == "vi" else "Order share (%)"},
                color_discrete_sequence=[COLORS["primary"]],
            )
            hour_chart.update_traces(
                line={"width": 3},
                marker={"size": 6},
                hovertemplate="%{x}:00<br>%{y:.1f}% tổng đơn<extra></extra>",
            )
            hour_chart.update_xaxes(tickmode="linear", tick0=0, dtick=3)
            plotly_chart(style_figure(hour_chart), key="time-hour-share")

    if day_ok and hour_ok:
        peak_day = day.loc[day["orders"].idxmax()]
        quiet_day = day.loc[day["orders"].idxmin()]
        peak_hour = hour.loc[hour["orders"].idxmax()]
        insight_left, insight_right = st.columns(2)
        with insight_left:
            card_dow_title = "Mức độ tập trung theo tuần" if get_current_lang() == "vi" else "Weekly concentration"
            card_dow_desc = (
                f"Ngày <b>{peak_day['dow_name']}</b> chiếm tỷ trọng cao nhất ({peak_day['share_pct']:.1f}% đơn hàng); "
                f"ngày <b>{quiet_day['dow_name']}</b> là thời điểm thấp điểm nhất."
                if get_current_lang() == "vi"
                else f"{peak_day['dow_name']} is highest at {peak_day['share_pct']:.1f}% "
                f"of orders; {quiet_day['dow_name']} is lowest."
            )
            insight_card(card_dow_title, card_dow_desc)
        with insight_right:
            card_hr_title = "Khung giờ cao điểm nhất" if get_current_lang() == "vi" else "Daily peak"
            card_hr_desc = (
                f"Khung giờ bận rộn nhất trong ngày là <b>{int(peak_hour['order_hour']):02d}:00</b> "
                f"với {format_integer(peak_hour['orders'])} đơn hàng."
                if get_current_lang() == "vi"
                else f"The busiest recurring hour is {int(peak_hour['order_hour']):02d}:00 with "
                f"{format_integer(peak_hour['orders'])} orders."
            )
            insight_card(card_hr_title, card_hr_desc)

    st.subheader(t("sec_weekend_comp"))
    comp_caption = (
        "Cuối tuần gồm 2 ngày (T7 & CN), ngày thường gồm 5 ngày (T2 - T6). "
        "Chỉ số so sánh công bằng được chuẩn hóa bằng số đơn trung bình trên mỗi ngày đại diện."
        if get_current_lang() == "vi"
        else "Weekend covers two day categories and weekday covers five. "
        "The primary comparison therefore uses average orders per day category, while raw totals remain visible."
    )
    st.caption(comp_caption)
    
    comparison_ok = require_columns(
        comparison,
        (
            "day_type",
            "orders",
            "days_in_group",
            "avg_orders_per_day",
            "avg_basket_size",
            "avg_reorder_rate_pct",
        ),
        context="Weekend comparison",
    )
    if comparison_ok:
        comp_title = "Số đơn đặt trung bình / ngày" if get_current_lang() == "vi" else "Average orders per represented day"
        normalized_chart = px.bar(
            comparison,
            x="day_type",
            y="avg_orders_per_day",
            color="day_type",
            color_discrete_sequence=CATEGORICAL_PALETTE[:2],
            title=comp_title,
            labels={"day_type": "Thời điểm", "avg_orders_per_day": t("comp_orders_day")},
            text_auto=",.0f",
        )
        normalized_chart.update_layout(showlegend=False)
        normalized_chart.update_traces(
            hovertemplate="%{x}<br>%{y:,.0f} " + t("comp_orders_day") + "<extra></extra>"
        )
        plotly_chart(
            style_figure(normalized_chart, height=390),
            key="time-weekend-normalized",
        )

        st.dataframe(
            comparison,
            width="stretch",
            hide_index=True,
            column_config={
                "orders": st.column_config.NumberColumn(format="%d"),
                "avg_orders_per_day": st.column_config.NumberColumn(format="%.1f"),
                "avg_basket_size": st.column_config.NumberColumn(format="%.2f"),
                "avg_reorder_rate_pct": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        download_frame(
            comparison,
            label="Tải xuống dữ liệu so sánh (CSV)" if get_current_lang() == "vi" else "Download rhythm comparison",
            filename="instacart-rhythm-comparison.csv",
            key="time-download",
        )
