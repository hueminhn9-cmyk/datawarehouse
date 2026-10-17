"""Truthful rule-based customer segmentation page."""

from __future__ import annotations

import pandas as pd
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
from dashboard.styles import CATEGORICAL_PALETTE, SEQUENTIAL_SCALE, style_figure

SEGMENT_ORDER = ["VIP", "Frequent", "Regular", "New"]


def _ordered_segments(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.copy()
    rank = {name: index for index, name in enumerate(SEGMENT_ORDER)}
    ordered["_rank"] = ordered["user_segment"].map(rank).fillna(len(rank))
    return ordered.sort_values(["_rank", "user_segment"]).drop(columns="_rank")


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("cust_title"),
        t("cust_summary"),
        eyebrow=t("cust_eyebrow"),
    )
    st.info(t("cust_info"))

    segments = load_repository_data(
        repository,
        "customer_segments",
        loading_label="Loading customer segments…",
    )
    segment_ok = require_columns(
        segments,
        (
            "user_segment",
            "users",
            "total_orders",
            "avg_orders",
            "avg_basket_size",
            "user_share_pct",
            "order_share_pct",
        ),
        context="Customer segment",
    )
    if segment_ok:
        segments = _ordered_segments(segments)
        share_frame = segments.melt(
            id_vars="user_segment",
            value_vars=["user_share_pct", "order_share_pct"],
            var_name="measure",
            value_name="share_pct",
        )
        is_vi = get_current_lang() == "vi"
        cust_share_label = "Tỷ trọng người dùng" if is_vi else "Customer share"
        order_share_label = "Đóng góp đơn hàng" if is_vi else "Order contribution"
        share_frame["measure"] = share_frame["measure"].map(
            {
                "user_share_pct": cust_share_label,
                "order_share_pct": order_share_label,
            }
        )
        chart_title = "Tỷ trọng khách hàng vs Đóng góp đơn hàng" if is_vi else "Customer share versus order contribution"
        seg_label = "Phân khúc khách hàng" if is_vi else "Rule-based segment"
        measure_label = "Chỉ số" if is_vi else "Measure"
        share_label = "Tỷ trọng (%)" if is_vi else "Share (%)"

        share_chart = px.bar(
            share_frame,
            x="user_segment",
            y="share_pct",
            color="measure",
            barmode="group",
            color_discrete_sequence=CATEGORICAL_PALETTE[:2],
            title=chart_title,
            labels={
                "user_segment": seg_label,
                "share_pct": share_label,
                "measure": measure_label,
            },
        )
        share_chart.update_traces(hovertemplate="%{x}<br>%{y:.1f}%<extra>%{fullData.name}</extra>")
        plotly_chart(
            style_figure(share_chart, horizontal_legend=True, legend=True),
            key="customers-segment-share",
        )

        contribution_gap = segments.assign(
            gap=segments["order_share_pct"] - segments["user_share_pct"]
        )
        strongest = contribution_gap.loc[contribution_gap["gap"].idxmax()]
        detail_left, detail_right = st.columns(2)
        with detail_left:
            card1_title = "Đòn bẩy đóng góp cao nhất" if is_vi else "Highest contribution leverage"
            card1_desc = (
                f"Khách hàng phân khúc <b>{strongest['user_segment']}</b> chiếm "
                f"{format_percent(strongest['user_share_pct'])} lượng người dùng nhưng đóng góp tới "
                f"{format_percent(strongest['order_share_pct'])} tổng số đơn hàng."
                if is_vi
                else f"{strongest['user_segment']} customers represent "
                f"{format_percent(strongest['user_share_pct'])} of customers and "
                f"{format_percent(strongest['order_share_pct'])} of orders."
            )
            insight_card(card1_title, card1_desc)
        with detail_right:
            card2_title = "Độ sâu tiêu dùng phân khúc" if is_vi else "Segment shopping depth"
            card2_desc = (
                f"Phân khúc dẫn đầu có tần suất trung bình "
                f"<b>{strongest['avg_orders']:.1f} đơn</b> và "
                f"<b>{strongest['avg_basket_size']:.1f} mặt hàng / giỏ</b>."
                if is_vi
                else f"The leading contribution segment averages "
                f"{strongest['avg_orders']:.1f} orders and "
                f"{strongest['avg_basket_size']:.1f} items per basket."
            )
            insight_card(card2_title, card2_desc)

        st.dataframe(
            segments,
            width="stretch",
            hide_index=True,
            column_config={
                "user_segment": "Phân khúc" if is_vi else "Segment",
                "users": st.column_config.NumberColumn("Người dùng" if is_vi else "Customers", format="%d"),
                "total_orders": st.column_config.NumberColumn("Tổng đơn" if is_vi else "Orders", format="%d"),
                "avg_orders": st.column_config.NumberColumn("Đơn TB" if is_vi else "Avg orders", format="%.1f"),
                "avg_basket_size": st.column_config.NumberColumn("Giỏ TB" if is_vi else "Avg basket", format="%.1f"),
                "user_share_pct": st.column_config.NumberColumn("% Khách" if is_vi else "User share", format="%.1f%%"),
                "order_share_pct": st.column_config.NumberColumn("% Đơn" if is_vi else "Order share", format="%.1f%%"),
            },
        )
        dl_label = "Tải xuống dữ liệu phân khúc (CSV)" if is_vi else "Download segment aggregate"
        download_frame(
            segments,
            label=dl_label,
            filename="instacart-rule-based-segments.csv",
            key="customers-download-segments",
        )

    st.subheader(t("sec_basket_dist"))
    baskets = load_repository_data(
        repository,
        "basket_distribution",
        loading_label="Loading basket distribution…",
    )
    basket_ok = require_columns(
        baskets,
        (
            "bucket_order",
            "basket_size",
            "orders",
            "avg_reorder_rate_pct",
            "order_share_pct",
        ),
        context="Basket distribution",
    )
    if basket_ok:
        is_vi = get_current_lang() == "vi"
        baskets = baskets.sort_values("bucket_order").copy()
        basket_title = "Số lượng đơn theo kích thước giỏ hàng" if is_vi else "Orders by basket-size band"
        b_x = "Kích thước giỏ (mặt hàng)" if is_vi else "Basket size"
        b_y = "Số lượng đơn" if is_vi else "Orders"
        b_color = "Tỷ lệ mua lại TB (%)" if is_vi else "Mean reorder ratio (%)"

        basket_chart = px.bar(
            baskets,
            x="basket_size",
            y="orders",
            color="avg_reorder_rate_pct",
            color_continuous_scale=SEQUENTIAL_SCALE,
            title=basket_title,
            labels={
                "basket_size": b_x,
                "orders": b_y,
                "avg_reorder_rate_pct": b_color,
            },
        )
        basket_chart.update_traces(
            hovertemplate=(
                "%{x}<br>%{y:,.0f} " + ("đơn" if is_vi else "orders") +
                "<br>" + b_color + ": %{marker.color:.1f}%<extra></extra>"
            )
        )
        plotly_chart(
            style_figure(basket_chart),
            key="customers-basket-distribution",
        )
        common = baskets.loc[baskets["orders"].idxmax()]
        common_title = "Quy mô giỏ hàng phổ biến nhất" if is_vi else "Most common basket band"
        common_desc = (
            f"Nhóm giỏ hàng <b>{common['basket_size']}</b> chiếm "
            f"<b>{format_percent(common['order_share_pct'])}</b> tổng số đơn hàng "
            f"({format_integer(common['orders'])} đơn)."
            if is_vi
            else f"{common['basket_size']} accounts for "
            f"{format_percent(common['order_share_pct'])} of orders "
            f"({format_integer(common['orders'])} orders)."
        )
        insight_card(common_title, common_desc)
        st.dataframe(
            baskets,
            width="stretch",
            hide_index=True,
            column_config={
                "basket_size": "Quy mô giỏ" if is_vi else "Basket size",
                "orders": st.column_config.NumberColumn("Số đơn" if is_vi else "Orders", format="%d"),
                "avg_reorder_rate_pct": st.column_config.NumberColumn("Tỷ lệ mua lại" if is_vi else "Reorder rate", format="%.1f%%"),
                "order_share_pct": st.column_config.NumberColumn("Tỷ trọng đơn" if is_vi else "Order share", format="%.1f%%"),
            },
        )
