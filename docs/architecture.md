# 🏛️ Kiến Trúc Hệ Thống Kho Dữ Liệu Instacart & Báo Cáo Phân Tích OLAP

## 1. Tổng quan Kiến trúc (Modern Data Stack)
Hệ thống Kho dữ liệu **Instacart Data Warehouse** được xây dựng theo kiến trúc Modern Analytics Stack nhúng, tối ưu hóa cho bài toán phân tích quy mô lớn (33.8+ triệu bản ghi) ngay trên máy cục bộ mà không cần cài đặt Docker hay hệ quản trị CSDL cồng kềnh.

```
+---------------------+       +-----------------------+       +-------------------------+
|   6 File CSV Thô    | ----> |   Polars ETL Engine   | ----> |  Apache Parquet Storage |
|  (~680 MB - Kaggle) |       |  (Đa luồng cực nhanh) |       |   (~156 MB - Nén 77%)   |
+---------------------+       +-----------------------+       +-------------------------+
                                                                           |
                                                                           v
+---------------------+       +-----------------------+       +-------------------------+
| Streamlit Dashboard | <---- |   6 Truy vấn OLAP     | <---- |     DuckDB Embedded     |
| (Giao diện song ngữ)|       | (Rollup, Cube, Window)|       |   (Kimball Star Schema) |
+---------------------+       +-----------------------+       +-------------------------+
```

---

## 2. Thiết kế Mô hình Star Schema (Kimball Methodology)
Kho dữ liệu tuân thủ nghiêm ngặt phương pháp luận **Ralph Kimball**:

### 🎯 Các Bảng Sự Thật (Fact Tables)
* `fact_orders`: Mức hạt (grain) theo từng đơn hàng đặt (3,421,083 dòng). Lưu các số đo: tổng số lượng mặt hàng (`total_items`), tỷ lệ mua lại (`reorder_ratio`), thời gian đặt hàng (`order_dow`, `order_hour_of_day`), số ngày từ đơn trước.
* `fact_order_items`: Mức hạt theo từng dòng mặt hàng trong đơn (33,819,106 dòng). Khóa chính kết hợp `(order_id, product_id)`.

### 🧭 Các Bảng Chiều (Dimension Tables)
* `dim_time`: Chiều thời gian mua sắm (168 khung giờ = 7 ngày x 24 giờ). Phân loại cuối tuần / ngày thường, tên thứ, khoảng giờ.
* `dim_users`: Chiều khách hàng (206,209 người dùng). Lưu phân khúc trung thành tính bằng SQL rule: `VIP` (≥50 đơn), `Frequent` (20-49 đơn), `Regular` (10-19 đơn), `New` (<10 đơn).
* `dim_products`: Chiều sản phẩm (49,688 sản phẩm) được chuẩn hóa phẳng (denormalized) gộp sẵn thông tin ngành hàng (`department_name`) và kệ hàng (`aisle_name`) nhằm giảm chi phí `JOIN`.
* `dim_departments`: 21 ngành hàng thực phẩm & bách hóa.
* `dim_aisles`: 134 kệ hàng phân loại chuyên sâu.

---

## 3. Cấu trúc Thư mục Chuẩn (Project Directory Structure)
```
DataWarehouse/
├── .streamlit/             # Cấu hình giao diện Streamlit (Light Mode)
│   └── config.toml
├── dashboard/              # Ứng dụng Báo cáo Dashboard Đa Ngôn Ngữ
│   ├── pages/              # 6 màn hình phân tích điều hành chuyên sâu
│   ├── app.py              # File chạy chính của Dashboard Streamlit
│   ├── components.py       # Thành phần UI tái sử dụng (KPI card, badge status)
│   ├── data.py             # Kho truy xuất DuckDB an toàn (Read-Only thread-safe)
│   ├── i18n.py             # Từ điển song ngữ (Tiếng Việt & English)
│   └── styles.py           # Thiết kế bảng màu và định dạng biểu đồ Plotly
├── data/                   # Thư mục chứa CSDL DuckDB và file nén Parquet
│   ├── parquet/            # Dữ liệu dạng cột nén Apache Parquet
│   ├── instacart_dw.duckdb # CSDL kho dữ liệu nhúng DuckDB (1.78 GB)
│   └── .gitkeep
├── docs/                   # Tài liệu kiến trúc hệ thống
│   └── architecture.md
├── etl/                    # Kịch bản đường ống ETL
│   ├── convert_to_parquet.py # Chuyển đổi CSV thô sang Parquet qua Polars
│   └── build_warehouse.py   # Xây dựng Star Schema và nạp dữ liệu vào DuckDB
├── scripts/                # Kịch bản công cụ bổ trợ
│   └── eda_preview.py      # Khảo sát nhanh cấu trúc dữ liệu thô
├── sql/                    # Mã nguồn DDL và Truy vấn OLAP chuẩn ANSI SQL
│   ├── 01_star_schema.sql  # DDL định nghĩa Star Schema (Fact & Dimension)
│   └── 02_olap_queries.sql # 6 câu truy vấn OLAP nâng cao (Rollup, Cube...)
├── tests/                  # Bộ kiểm thử chất lượng dữ liệu tự động
│   └── test_etl.py         # Kiểm thử 100% tính toàn vẹn và mức hạt Fact/Dim
├── README.md               # Báo cáo đồ án giữa kỳ hoàn chỉnh & Bộ câu hỏi vấn đáp
├── requirements.txt        # Danh mục thư viện Python phụ thuộc
└── run_dashboard.py        # Kịch bản khởi chạy Dashboard chỉ với 1 click
```
