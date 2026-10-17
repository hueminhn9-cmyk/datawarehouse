"""Hệ thống đa ngôn ngữ (Bilingual: Tiếng Việt & English) cho Instacart Dashboard."""

from __future__ import annotations
import streamlit as st

MESSAGES = {
    "vi": {
        "lang_name": "Tiếng Việt",
        "app_title": "Instacart Intelligence",
        "app_caption": "Trung tâm điều hành · Kho dữ liệu siêu thị",
        "workspace": "Không gian phân tích",
        "data_source": "Nguồn dữ liệu",
        "source_status": "Kho dữ liệu DuckDB (Dạng cột nhúng)",
        "ready_status": "Trạng thái: SẴN SÀNG (33.8M dòng)",
        "refresh_btn": "Làm mới dữ liệu",
        "date_note": "Dữ liệu Instacart chứa thông tin theo thứ và giờ, không dùng ngày tháng dương lịch.",
        "footer": "Instacart Decision Intelligence · Hệ thống Kho Dữ Liệu Bán Lẻ & Phân Tích OLAP Đa Chiều.",
        
        # Pages names in sidebar
        "page_overview": "📊 Tổng quan điều hành",
        "page_products": "🛍️ Sản phẩm & Kệ hàng",
        "page_rhythm": "⏰ Nhịp điệu mua sắm",
        "page_customers": "👥 Phân khúc khách hàng",
        "page_departments": "🏢 Hiệu quả ngành hàng",
        "page_tables": "🗄️ Tra cứu kho dữ liệu",

        # Overview page
        "ov_eyebrow": "Kho Dữ Liệu Bán Lẻ Instacart",
        "ov_title": "Tổng quan điều hành (Executive Overview)",
        "ov_summary": "Báo cáo điều hành tổng thể về khối lượng đơn hàng, quy mô khách hàng, kích thước giỏ hàng và cơ cấu thị phần ngành hàng.",
        "kpi_orders": "Tổng số đơn hàng",
        "kpi_users": "Khách hàng hoạt động",
        "kpi_products": "Số lượng sản phẩm",
        "kpi_items": "Mặt hàng đã bán",
        "kpi_basket": "Giỏ hàng trung bình",
        "kpi_reorder": "Tỷ lệ mua lại",
        "sec_weekly": "Xu hướng đặt hàng theo ngày trong tuần",
        "sec_hourly": "Phân bố đơn hàng theo khung giờ trong ngày",
        "sec_dept_share": "Thị phần theo ngành hàng (Department Share)",
        "chart_orders": "Số lượng đơn hàng",
        "chart_dow": "Ngày trong tuần",
        "chart_hour": "Giờ trong ngày (0 - 23h)",
        "chart_items": "Số lượng mặt hàng",
        
        # Products page
        "prod_eyebrow": "Tín hiệu thương mại & tiêu dùng",
        "prod_title": "Sản phẩm & Kệ hàng (Products & Aisles)",
        "prod_summary": "Khảo sát các sản phẩm bán chạy nhất và tỷ lệ mua lại lặp lại theo ngành hàng và kệ hàng cụ thể.",
        "filter_dept": "Lọc theo ngành hàng (Department)",
        "all_depts": "Tất cả ngành hàng",
        "prod_shown": "Số lượng sản phẩm hiển thị",
        "prod_search": "Tìm kiếm sản phẩm trong danh sách top tải về",
        "prod_search_ph": "Ví dụ: banana, milk, organic...",
        "sec_prod_rank": "Bảng xếp hạng sản phẩm",
        "sec_aisle_perf": "Hiệu quả kệ hàng nổi bật (Top Aisles)",
        "sec_aisle_tree": "Phân cấp: Ngành hàng ➔ Kệ hàng (Treemap)",

        # Time analysis page
        "time_eyebrow": "Thời điểm nhu cầu mua sắm",
        "time_title": "Nhịp điệu mua sắm (Shopping Rhythm)",
        "time_summary": "Khảo sát quy luật nhu cầu định kỳ theo ngày trong tuần và khung giờ trong ngày.",
        "sec_dow_pattern": "Quy luật đơn hàng hàng tuần",
        "sec_hour_pattern": "Khung giờ cao điểm trong ngày",
        "sec_weekend_comp": "So sánh chuẩn hóa: Cuối tuần vs Ngày thường",
        "comp_orders_day": "Số đơn trung bình / ngày",
        "comp_basket": "Kích thước giỏ hàng",
        "comp_reorder": "Tỷ lệ mua lại",

        # Customers page
        "cust_eyebrow": "Hành vi khách hàng",
        "cust_title": "Phân khúc khách hàng (Customer Segments)",
        "cust_summary": "So sánh quy mô khách hàng và mức độ đóng góp đơn hàng dựa trên quy tắc phân đoạn của Kho dữ liệu.",
        "cust_info": "Đây là phân khúc dựa trên quy tắc nghiệp vụ SQL của Kho dữ liệu: VIP (≥50 đơn), Frequent (20-49 đơn), Regular (10-19 đơn), New (<10 đơn).",
        "sec_segment_share": "Tỷ trọng người dùng vs Đóng góp đơn hàng",
        "sec_basket_dist": "Phân bố kích thước giỏ hàng (Basket Size Distribution)",
        "sec_segment_table": "Bảng tổng hợp chi tiết phân khúc",

        # Departments page
        "dept_eyebrow": "Phân bổ danh mục sản phẩm",
        "dept_title": "Hiệu quả ngành hàng (Department Performance)",
        "dept_summary": "So sánh mức độ tiếp cận, sản lượng, độ rộng danh mục và tỷ lệ mua lại giữa các ngành hàng.",
        "sec_dept_rank": "Xếp hạng toàn bộ 21 ngành hàng",
        "sec_side_by_side": "So sánh đối đầu giữa 2 ngành hàng (Thang đo 0 - 100)",
        "dept_first": "Ngành hàng thứ nhất",
        "dept_second": "Ngành hàng thứ hai",

        # Tables page
        "tbl_eyebrow": "Cấu trúc dữ liệu kho",
        "tbl_title": "Tra cứu kho dữ liệu (Warehouse Explorer)",
        "tbl_summary": "Tra cứu lược đồ cấu trúc, phân vùng, chỉ mục và xem dữ liệu mẫu của 7 bảng Fact & Dimension.",
        "tbl_select": "Chọn bảng trong kho dữ liệu",
        "tbl_est_rows": "Ước lượng số dòng",
        "tbl_est_size": "Dung lượng ước lượng",
        "tbl_cols": "Số lượng cột",
        "tbl_schema": "Lược đồ cột (Schema)",
        "tbl_indexes": "Chỉ mục (Indexes)",
        "tbl_partitions": "Phân vùng dữ liệu (Partitions)",
        "tbl_sample": "Dữ liệu mẫu (Row Sample)",
        "tbl_load_sample": "Tải mẫu dữ liệu",
    },
    
    "en": {
        "lang_name": "English",
        "app_title": "Instacart Intelligence",
        "app_caption": "Decision cockpit · warehouse snapshot",
        "workspace": "Analysis workspace",
        "data_source": "Data source",
        "source_status": "Live DuckDB warehouse (Columnar)",
        "ready_status": "Source status: READY (33.8M rows)",
        "refresh_btn": "Refresh snapshot",
        "date_note": "Instacart's source data contains day-of-week and hour fields, not calendar dates.",
        "footer": "Instacart Decision Intelligence · aggregate analytics over an anonymized public market-basket dataset.",
        
        # Pages names in sidebar
        "page_overview": "📊 Executive overview",
        "page_products": "🛍️ Products & aisles",
        "page_rhythm": "⏰ Shopping rhythm",
        "page_customers": "👥 Customer segments",
        "page_departments": "🏢 Departments",
        "page_tables": "🗄️ Warehouse explorer",

        # Overview page
        "ov_eyebrow": "Instacart Decision Intelligence",
        "ov_title": "Executive overview",
        "ov_summary": "A decision-focused view of order volume, customer reach, basket behavior, and category mix for the current warehouse snapshot.",
        "kpi_orders": "Total Orders",
        "kpi_users": "Active Customers",
        "kpi_products": "Unique Products",
        "kpi_items": "Line Items",
        "kpi_basket": "Avg Basket Size",
        "kpi_reorder": "Avg Reorder Rate",
        "sec_weekly": "Recurring weekly pattern",
        "sec_hourly": "Hourly order distribution",
        "sec_dept_share": "Department market share",
        "chart_orders": "Orders",
        "chart_dow": "Day of week",
        "chart_hour": "Hour of day (0 - 23h)",
        "chart_items": "Total items",

        # Products page
        "prod_eyebrow": "Merchandising signals",
        "prod_title": "Products & aisles",
        "prod_summary": "Explore high-volume products and repeat-purchase behavior with explicit support thresholds and department filters.",
        "filter_dept": "Department",
        "all_depts": "All departments",
        "prod_shown": "Products shown",
        "prod_search": "Search within loaded top products",
        "prod_search_ph": "Try banana, milk, or organic...",
        "sec_prod_rank": "Product ranking",
        "sec_aisle_perf": "High-support aisle reorder metrics",
        "sec_aisle_tree": "Department & aisle hierarchy (Treemap)",

        # Time analysis page
        "time_eyebrow": "Demand timing",
        "time_title": "Shopping rhythm",
        "time_summary": "Understand recurring day-of-week and hour-of-day demand patterns without calendar dates.",
        "sec_dow_pattern": "Recurring weekly pattern",
        "sec_hour_pattern": "Hourly demand pattern",
        "sec_weekend_comp": "Normalized weekday vs weekend comparison",
        "comp_orders_day": "Avg orders / day",
        "comp_basket": "Avg basket size",
        "comp_reorder": "Avg reorder rate",

        # Customers page
        "cust_eyebrow": "Customer behavior",
        "cust_title": "Customer segments",
        "cust_summary": "Compare customer reach, order contribution, and basket behavior using deterministic warehouse segment rules.",
        "cust_info": "These are rule-based warehouse segments: VIP (≥50 orders), Frequent (20–49), Regular (10–19), New (<10).",
        "sec_segment_share": "User share vs Order share",
        "sec_basket_dist": "Basket size distribution",
        "sec_segment_table": "Detailed segment summary",

        # Departments page
        "dept_eyebrow": "Portfolio allocation",
        "dept_title": "Department performance",
        "dept_summary": "Compare reach, item volume, assortment breadth, and repeat behavior across departments.",
        "sec_dept_rank": "All 21 departments ranking",
        "sec_side_by_side": "Side-by-side comparison (0 - 100 Index)",
        "dept_first": "First department",
        "dept_second": "Second department",

        # Tables page
        "tbl_eyebrow": "Warehouse catalogue",
        "tbl_title": "Warehouse explorer",
        "tbl_summary": "Inspect schemas, column types, partitions, indexes, and sample rows from the 7 Star Schema tables.",
        "tbl_select": "Warehouse table",
        "tbl_est_rows": "Estimated rows",
        "tbl_est_size": "Estimated storage",
        "tbl_cols": "Columns",
        "tbl_schema": "Schema",
        "tbl_indexes": "Indexes",
        "tbl_partitions": "Partitions",
        "tbl_sample": "Row sample",
        "tbl_load_sample": "Load sample rows",
    }
}


def get_current_lang() -> str:
    """Lấy ngôn ngữ hiện tại trong session (mặc định 'vi')."""
    return st.session_state.get("lang", "vi")


def t(key: str) -> str:
    """Truy xuất chuỗi theo ngôn ngữ hiện tại."""
    lang = get_current_lang()
    return MESSAGES.get(lang, MESSAGES["vi"]).get(key, key)
