"""Department performance and fair, normalized comparisons."""

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

COMPARISON_METRICS_EN = {
    "orders": "Order reach",
    "total_items": "Item volume",
    "unique_products": "Product breadth",
    "reorder_rate_pct": "Reorder rate",
}

COMPARISON_METRICS_VI = {
    "orders": "Lượt đặt mua",
    "total_items": "Sản lượng mặt hàng",
    "unique_products": "Độ rộng danh mục",
    "reorder_rate_pct": "Tỷ lệ mua lại",
}


def _normalized_comparison(
    departments: pd.DataFrame,
    selected_names: tuple[str, str],
) -> pd.DataFrame:
    """Express unlike department metrics on a comparable 0-100 index."""
    is_vi = get_current_lang() == "vi"
    metrics_map = COMPARISON_METRICS_VI if is_vi else COMPARISON_METRICS_EN

    selected = departments[departments["department_name"].isin(selected_names)].copy()
    rows: list[dict[str, object]] = []
    for column, label in metrics_map.items():
        metric_ceiling = pd.to_numeric(departments[column], errors="coerce").max()
        for _, department in selected.iterrows():
            actual = pd.to_numeric(pd.Series([department[column]]), errors="coerce").iloc[0]
            score = 0.0
            if pd.notna(actual) and pd.notna(metric_ceiling) and metric_ceiling > 0:
                score = float(actual) / float(metric_ceiling) * 100
            rows.append(
                {
                    "department_name": department["department_name"],
                    "metric": label,
                    "relative_index": score,
                }
            )
    return pd.DataFrame(rows)


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("dept_title"),
        t("dept_summary"),
        eyebrow=t("dept_eyebrow"),
    )

    departments = load_repository_data(
        repository,
        "departments",
        loading_label="Loading department aggregates…",
    )
    required = (
        "department_name",
        "orders",
        "total_items",
        "reorder_rate_pct",
        "unique_products",
        "market_share_pct",
    )
    if not require_columns(departments, required, context="Department performance"):
        return

    is_vi = get_current_lang() == "vi"
    department_frame = departments.copy()
    department_frame["department_name"] = department_frame["department_name"].astype(str)

    st.subheader(t("sec_dept_rank"))
    chart_frame = department_frame.nlargest(12, "total_items").sort_values("total_items")
    port_title = "Các ngành hàng lớn nhất theo sản lượng mặt hàng" if is_vi else "Largest departments by line-item volume"
    port_x = "Số lượng mặt hàng" if is_vi else "Line items"
    port_y = "Ngành hàng" if is_vi else "Department"
    port_color = "Tỷ lệ mua lại (%)" if is_vi else "Reorder rate (%)"

    portfolio_chart = px.bar(
        chart_frame,
        x="total_items",
        y="department_name",
        orientation="h",
        color="reorder_rate_pct",
        color_continuous_scale=SEQUENTIAL_SCALE,
        title=port_title,
        labels={
            "total_items": port_x,
            "department_name": port_y,
            "reorder_rate_pct": port_color,
        },
        hover_data={"orders": ":,.0f", "market_share_pct": ":.1f"},
    )
    portfolio_chart.update_traces(
        hovertemplate=(
            "%{y}<br>%{x:,.0f} " + port_x + "<br>" + port_color + ": %{marker.color:.1f}%<extra></extra>"
        )
    )
    plotly_chart(
        style_figure(
            portfolio_chart,
            height=max(460, 34 * len(chart_frame) + 170),
        ),
        key="departments-portfolio",
    )

    insight_left, insight_right = st.columns(2)
    volume_leader = department_frame.loc[department_frame["total_items"].idxmax()]
    reorder_leader = department_frame.loc[department_frame["reorder_rate_pct"].idxmax()]
    with insight_left:
        lead_vol_title = "Dẫn đầu về sản lượng" if is_vi else "Volume leader"
        lead_vol_desc = (
            f"Ngành hàng <b>{volume_leader['department_name']}</b> chiếm "
            f"<b>{format_percent(volume_leader['market_share_pct'])}</b> tổng số mặt hàng bán ra."
            if is_vi
            else f"{volume_leader['department_name']} represents "
            f"{format_percent(volume_leader['market_share_pct'])} of line items in this snapshot."
        )
        insight_card(lead_vol_title, lead_vol_desc)
    with insight_right:
        lead_re_title = "Độ trung thành cao nhất" if is_vi else "Repeat leader"
        lead_re_desc = (
            f"Ngành hàng <b>{reorder_leader['department_name']}</b> có tỷ lệ mua lại cao nhất đạt "
            f"<b>{format_percent(reorder_leader['reorder_rate_pct'])}</b>."
            if is_vi
            else f"{reorder_leader['department_name']} has the highest department "
            f"reorder rate at {format_percent(reorder_leader['reorder_rate_pct'])}."
        )
        insight_card(lead_re_title, lead_re_desc)

    st.subheader(t("sec_side_by_side"))
    department_names = sorted(department_frame["department_name"].unique())
    if len(department_names) < 2:
        st.info("Cần ít nhất 2 ngành hàng để so sánh." if is_vi else "At least two departments are required for a comparison.")
    else:
        selector_left, selector_right = st.columns(2)
        with selector_left:
            first_name = st.selectbox(
                t("dept_first"),
                department_names,
                index=0,
                key="department-compare-first",
            )
        second_options = [name for name in department_names if name != first_name]
        with selector_right:
            second_name = st.selectbox(
                t("dept_second"),
                second_options,
                index=0,
                key="department-compare-second",
            )

        normalized = _normalized_comparison(
            department_frame,
            (first_name, second_name),
        )
        comp_title = "Chỉ số hiệu quả tương đối theo ngành hàng" if is_vi else "Relative performance index by metric"
        comp_y = "Điểm chuẩn hóa (Ngành cao nhất = 100)" if is_vi else "Index (best department = 100)"
        comp_x = "Chỉ tiêu so sánh" if is_vi else "Metric"
        comp_color = "Ngành hàng" if is_vi else "Department"

        comparison_chart = px.bar(
            normalized,
            x="metric",
            y="relative_index",
            color="department_name",
            barmode="group",
            color_discrete_sequence=CATEGORICAL_PALETTE,
            title=comp_title,
            labels={
                "metric": comp_x,
                "relative_index": comp_y,
                "department_name": comp_color,
            },
        )
        comparison_chart.update_yaxes(range=[0, 105], ticksuffix="")
        comparison_chart.update_traces(
            hovertemplate=("%{x}<br>" + comp_y + ": %{y:.1f}<br>%{fullData.name}<extra></extra>")
        )
        plotly_chart(
            style_figure(
                comparison_chart,
                height=440,
                legend=True,
                horizontal_legend=True,
            ),
            key="departments-comparison",
        )
        norm_cap = (
            "Mỗi điểm số là giá trị của ngành hàng chia cho giá trị cao nhất của chỉ tiêu đó trên toàn bộ 21 ngành hàng. "
            "Bảng bên dưới hiển thị số liệu thực tế."
            if is_vi
            else "Each score is the department value divided by the highest value for that metric across all departments in this snapshot. The table below retains the original units."
        )
        st.caption(norm_cap)

        actual = department_frame[
            department_frame["department_name"].isin((first_name, second_name))
        ][list(("department_name", *COMPARISON_METRICS_EN))]
        st.dataframe(
            actual,
            width="stretch",
            hide_index=True,
            column_config={
                "department_name": "Ngành hàng" if is_vi else "Department",
                "orders": st.column_config.NumberColumn(
                    "Số đơn đặt" if is_vi else "Distinct orders",
                    format="%d",
                ),
                "total_items": st.column_config.NumberColumn(
                    "Sản lượng mặt hàng" if is_vi else "Line items",
                    format="%d",
                ),
                "unique_products": st.column_config.NumberColumn(
                    "Số sản phẩm khác nhau" if is_vi else "Unique products",
                    format="%d",
                ),
                "reorder_rate_pct": st.column_config.NumberColumn(
                    "Tỷ lệ mua lại" if is_vi else "Reorder rate",
                    format="%.1f%%",
                ),
            },
        )
        first_row = actual[actual["department_name"] == first_name].iloc[0]
        second_row = actual[actual["department_name"] == second_name].iloc[0]
        item_difference = int(first_row["total_items"] - second_row["total_items"])
        higher_name = first_name if item_difference >= 0 else second_name
        readout_title = "Nhận định so sánh" if is_vi else "Comparison readout"
        readout_desc = (
            f"Ngành hàng <b>{higher_name}</b> có quy mô mặt hàng lớn hơn; chênh lệch tuyệt đối là "
            f"<b>{format_integer(abs(item_difference))} mặt hàng</b>. Tỷ lệ mua lại nên được đánh giá riêng để đo lường độ trung thành của khách hàng."
            if is_vi
            else f"{higher_name} has the larger item footprint; the absolute gap is "
            f"{format_integer(abs(item_difference))} line items. Use reorder "
            "rate separately to judge repeat behavior."
        )
        insight_card(readout_title, readout_desc)

    exp_label = "Xem & tải dữ liệu toàn bộ ngành hàng" if is_vi else "Department data and download"
    with st.expander(exp_label):
        st.dataframe(
            department_frame,
            width="stretch",
            hide_index=True,
            column_config={
                "department_name": "Ngành hàng" if is_vi else "Department",
                "orders": st.column_config.NumberColumn("Số đơn" if is_vi else "Orders", format="%d"),
                "total_items": st.column_config.NumberColumn("Số mặt hàng" if is_vi else "Line items", format="%d"),
                "unique_products": st.column_config.NumberColumn("Số sản phẩm" if is_vi else "Unique products", format="%d"),
                "reorder_rate_pct": st.column_config.NumberColumn("Tỷ lệ mua lại" if is_vi else "Reorder rate", format="%.1f%%"),
                "market_share_pct": st.column_config.NumberColumn("Thị phần" if is_vi else "Market share", format="%.1f%%"),
            },
        )
        dl_dept_label = "Tải xuống dữ liệu ngành hàng (CSV)" if is_vi else "Download department aggregates"
        download_frame(
            department_frame,
            label=dl_dept_label,
            filename="instacart-departments.csv",
            key="departments-download",
        )
