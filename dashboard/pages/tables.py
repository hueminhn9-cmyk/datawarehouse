"""Lazy, safe warehouse catalogue explorer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import (
    format_decimal,
    format_integer,
    load_repository_data,
    page_header,
    require_columns,
)
from dashboard.data import AnalyticsRepository, TableMetadata
from dashboard.i18n import t, get_current_lang


def _catalog_label(catalog: pd.DataFrame, table_name: str) -> str:
    row = catalog[catalog["table_name"] == table_name].iloc[0]
    return f"{table_name} · {row['kind']}"


def _render_metadata(metadata: TableMetadata) -> None:
    is_vi = get_current_lang() == "vi"
    st.subheader(metadata.name)
    st.caption(f"{metadata.kind} · {metadata.description}")

    metric_left, metric_middle, metric_right = st.columns(3)
    with metric_left:
        st.metric(
            t("tbl_est_rows"),
            format_integer(metadata.row_count_estimate),
            help="Ước tính từ DuckDB; có thể khác số đếm chính xác." if is_vi else "Warehouse statistics estimate; it may differ from an exact count.",
        )
    with metric_middle:
        not_rep = "Chưa xác định" if is_vi else "Not reported"
        size_label = (
            f"{format_decimal(metadata.size_mb, 2)} MB"
            if metadata.size_mb is not None
            else not_rep
        )
        st.metric(t("tbl_est_size"), size_label)
    with metric_right:
        st.metric(t("tbl_cols"), format_integer(len(metadata.columns)))

    st.markdown(f"### {t('tbl_schema')}")
    if metadata.columns.empty:
        st.info("Không có thông tin lược đồ cột cho bảng này." if is_vi else "No column metadata is available for this table.")
    else:
        st.dataframe(
            metadata.columns,
            width="stretch",
            hide_index=True,
            column_config={
                "column_name": "Tên cột" if is_vi else "Column",
                "data_type": "Kiểu dữ liệu" if is_vi else "Data type",
                "nullable": st.column_config.CheckboxColumn("Cho phép rỗng" if is_vi else "Nullable"),
                "default": "Mặc định" if is_vi else "Default",
                "comment": "Ghi chú" if is_vi else "Comment",
            },
        )

    details_left, details_right = st.columns(2)
    with details_left:
        st.markdown(f"### {t('tbl_indexes')}")
        if metadata.indexes.empty:
            st.info("Không có chỉ mục phụ nào." if is_vi else "No secondary indexes are reported for this table.")
        else:
            st.dataframe(
                metadata.indexes,
                width="stretch",
                hide_index=True,
                column_config={
                    "index_name": "Tên chỉ mục" if is_vi else "Index",
                    "columns": "Cột" if is_vi else "Columns",
                    "unique": st.column_config.CheckboxColumn("Duy nhất" if is_vi else "Unique"),
                },
            )
    with details_right:
        st.markdown(f"### {t('tbl_partitions')}")
        if metadata.partitions.empty:
            st.info("Bảng không có phân vùng riêng." if is_vi else "This table has no reported partitions.")
        else:
            st.dataframe(
                metadata.partitions,
                width="stretch",
                hide_index=True,
                column_config={
                    "partition_name": "Tên phân vùng" if is_vi else "Partition",
                    "row_count_estimate": st.column_config.NumberColumn(
                        "Số dòng ước tính" if is_vi else "Estimated rows",
                        format="%d",
                    ),
                    "size_mb": st.column_config.NumberColumn(
                        "Dung lượng (MB)" if is_vi else "Size (MB)",
                        format="%.2f",
                    ),
                    "comment": "Ghi chú" if is_vi else "Comment",
                },
            )


def show(repository: AnalyticsRepository) -> None:
    page_header(
        t("tbl_title"),
        t("tbl_summary"),
        eyebrow=t("tbl_eyebrow"),
    )

    catalog = load_repository_data(
        repository,
        "table_catalog",
        loading_label="Loading warehouse catalogue…",
    )
    if not require_columns(
        catalog,
        ("table_name", "kind", "description", "row_count_estimate"),
        context="Warehouse catalogue",
    ):
        return

    is_vi = get_current_lang() == "vi"
    st.subheader("Chọn bảng trong kho dữ liệu" if is_vi else "Choose a table")
    selected_table = st.selectbox(
        t("tbl_select"),
        catalog["table_name"].astype(str).tolist(),
        format_func=lambda name: _catalog_label(catalog, name),
        help="Chỉ cho phép tra cứu các bảng thuộc Fact & Dimension trong danh mục kho." if is_vi else "Only repository-whitelisted dimension and fact tables are available.",
    )
    metadata = load_repository_data(
        repository,
        "table_metadata",
        loading_label=f"Inspecting {selected_table} metadata…",
        table_name=selected_table,
    )
    if metadata is None:
        return
    _render_metadata(metadata)

    st.markdown(f"### {t('tbl_sample')}")
    sample_rows = st.slider(
        "Số dòng mẫu cần xem" if is_vi else "Rows to load",
        min_value=5,
        max_value=25,
        value=10,
        step=5,
        help="Giới hạn số dòng tải trước khi render lên UI." if is_vi else "This limit is applied by the repository before data reaches the UI.",
    )
    check_label = f"Tải mẫu {sample_rows} dòng từ bảng {selected_table}" if is_vi else f"Load a {sample_rows}-row sample from {selected_table}"
    load_sample = st.checkbox(
        check_label,
        value=False,
        key=f"table-sample-request-{selected_table}",
    )
    if load_sample:
        sample = load_repository_data(
            repository,
            "table_sample",
            loading_label=f"Loading a small sample from {selected_table}…",
            table_name=selected_table,
            limit=sample_rows,
        )
        if sample is not None:
            if sample.empty:
                st.info("Bảng này không có dữ liệu mẫu." if is_vi else "This table returned no sample rows.")
            else:
                st.dataframe(sample, width="stretch", hide_index=True)
    else:
        st.caption("Truy vấn mẫu chỉ được kích hoạt khi chọn checkbox ở trên." if is_vi else "Sample query is paused until the checkbox is selected.")

    exp_title = "Xem danh mục toàn bộ các bảng trong kho dữ liệu" if is_vi else "Full warehouse catalogue"
    with st.expander(exp_title):
        st.caption("Số lượng dòng hiển thị là ước lượng từ catalog của kho dữ liệu." if is_vi else "Row counts in this catalogue are estimates when the source reports them.")
        st.dataframe(
            catalog,
            width="stretch",
            hide_index=True,
            column_config={
                "table_name": "Tên bảng" if is_vi else "Table",
                "kind": "Loại bảng" if is_vi else "Kind",
                "description": "Mô tả / Mục đích" if is_vi else "Purpose",
                "row_count_estimate": st.column_config.NumberColumn(
                    "Số dòng ước tính" if is_vi else "Estimated rows",
                    format="%d",
                ),
            },
        )
