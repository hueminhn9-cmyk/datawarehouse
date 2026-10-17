# 🛒 BÁO CÁO ĐỒ ÁN GIỮA KỲ: HỆ THỐNG KHO DỮ LIỆU INSTACART & PHÂN TÍCH OLAP

> **Học phần:** Kho dữ liệu & Kỹ thuật Dữ liệu (Data Warehouse & Data Engineering)  
> **Kiến trúc áp dụng:** Kimball Dimensional Modeling (Mô hình hình sao - Star Schema)  
> **Công nghệ thực thi:** Apache Parquet + DuckDB Embedded OLAP Engine + Streamlit Dashboard  

---

## 📖 1. TỔNG QUAN ĐỀ TÀI & BÀI TOÁN NGHIỆP VỤ

### 1.1. Bối cảnh
**Instacart** là nền tảng giao hàng tạp hóa và siêu thị trực tuyến hàng đầu. Bộ dữ liệu bao gồm hơn **3.4 triệu đơn hàng** với hơn **33.8 triệu dòng chi tiết giỏ hàng** của hơn **206.000 người tiêu dùng** tại Hoa Kỳ.

### 1.2. Mục tiêu của Kho Dữ Liệu
Hệ thống Kho dữ liệu được xây dựng nhằm phục vụ các mục tiêu nghiệp vụ cốt lõi:
1. **Phân tích hành vi đơn hàng:** Đo lường lượng đơn đặt theo từng ngày trong tuần và khung giờ trong ngày để tối ưu nguồn lực nhân sự giao vận.
2. **Quản lý danh mục sản phẩm:** Xác định Top sản phẩm bán chạy nhất và tỷ lệ mua lại (*Reorder Rate*) theo từng ngành hàng.
3. **Phân khúc khách hàng:** Phân loại khách hàng theo tần suất mua hàng (`VIP`, `Frequent`, `Regular`, `New`) để phục vụ các chiến dịch chăm sóc khách hàng mục tiêu.

---

## 🏛️ 2. MÔ HÌNH HÓA DỮ LIỆU (DIMENSIONAL MODELING - STAR SCHEMA)

Hệ thống được thiết kế theo phương pháp luận 4 bước của **Ralph Kimball**:
* **Quy trình nghiệp vụ:** Hoạt động đặt hàng siêu thị trực tuyến (*Grocery Ordering*).
* **Mức hạt (Grain):**
  - `fact_orders`: 1 dòng = 1 đơn hàng được đặt (*Order Grain*).
  - `fact_order_items`: 1 dòng = 1 sản phẩm nằm trong 1 đơn hàng (*Line-item Grain*).

### 2.1. Lược đồ Star Schema (Mermaid Diagram)

```mermaid
erDiagram
    dim_departments ||--o{ dim_products : "phân loại"
    dim_aisles ||--o{ dim_products : "chứa trong"
    dim_time ||--o{ fact_orders : "thời điểm đặt"
    dim_users ||--o{ fact_orders : "người đặt"
    fact_orders ||--|{ fact_order_items : "chi tiết dòng hàng"
    dim_products ||--o{ fact_order_items : "sản phẩm mua"

    fact_orders {
        int order_id PK
        int user_id FK
        int time_id FK
        string eval_set
        int order_number
        int order_dow
        int order_hour_of_day
        float days_since_prior_order
        int total_items
        float reorder_ratio
    }

    fact_order_items {
        int order_id PK, FK
        int product_id PK, FK
        int add_to_cart_order
        boolean reordered
    }

    dim_products {
        int product_id PK
        string product_name
        int aisle_id
        int department_id
        string aisle_name
        string department_name
    }

    dim_time {
        int time_id PK
        int order_dow
        int order_hour_of_day
        string dow_name
        string hour_range
        boolean is_weekend
    }

    dim_users {
        int user_id PK
        string user_segment
        int total_orders
        int total_items
        float avg_basket_size
        float avg_reorder_ratio
        float avg_days_between_orders
    }
```

---

## ⚡ 3. ĐIỂM SÁNG KỸ THUẬT & TỐI ƯU CÔNG NGHỆ

Dự án áp dụng trực tiếp **khuyến nghị trong Slide bài giảng**:

1. **Lưu trữ dạng cột nén Apache Parquet (thay cho CSV thô):**
   - Bộ dữ liệu CSV thô nặng **680.32 MB** (hơn 33.8 triệu dòng).
   - Được chuyển đổi bằng thư viện **Polars** đa luồng sang **Apache Parquet**.
   - Kết quả: Dung lượng đĩa giảm **77%** xuống còn **156.25 MB** (thời gian chuyển đổi chỉ mất **4.33 giây**).

2. **Cơ sở dữ liệu OLAP dạng cột DuckDB (thay cho MySQL/MariaDB truyền thống):**
   - DuckDB là hệ quản trị CSDL OLAP nhúng nhẹ nhàng, không yêu cầu cài đặt Docker hay cấu hình cổng mạng.
   - Toàn bộ Kho dữ liệu Star Schema hơn 33.8 triệu bản ghi được xây dựng thành công trong **107 giây**.
   - Tốc độ truy vấn các phép toán tổng hợp `GROUP BY`, `ROLLUP` chỉ mất từ **0.3 - 1.5 giây** ngay trên laptop cá nhân.

---

## 📁 4. CẤU TRÚC THƯ MỤC DỰ ÁN (PROJECT STRUCTURE)

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

---

## 🚀 5. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY HỆ THỐNG

### Bước 1: Cài đặt môi trường
Yêu cầu Python 3.10 trở lên. Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

### Bước 2: Chạy kiểm thử tự động (Data Quality Tests)
```bash
pytest tests/
```
*(4/4 bài kiểm thử kiểm tra tính toàn vẹn và số lượng bản ghi của Fact & Dimension).*

### Bước 3: Khởi chạy Dashboard Báo cáo (Streamlit)
```bash
python run_dashboard.py
```
Hoặc:
```bash
streamlit run dashboard/app.py
```
Truy cập giao diện tại: `http://localhost:8501`.

---

## 📊 6. DANH MỤC TRUY VẤN OLAP NÂNG CAO (`sql/02_olap_queries.sql`)

Dự án cung cấp sẵn kịch bản 6 câu truy vấn OLAP chuẩn ANSI SQL tại [sql/02_olap_queries.sql](file:///d:/DataWarehouse/DataWarehouse/sql/02_olap_queries.sql):

1. **ROLL-UP:** Tổng hợp doanh số phân cấp `Ngành hàng -> Kệ hàng -> Sản phẩm`.
2. **CUBE:** Phân tích đa chiều ma trận `Ngày trong tuần x Khung giờ`.
3. **WINDOW FUNCTION:** Xếp hạng sản phẩm bán chạy nhất từng ngành (`DENSE_RANK() OVER (...)`).
4. **SLICE & DICE:** So sánh hành vi mua sắm giữa Ngày thường và Cuối tuần.
5. **MARKET SHARE:** Tính tỷ trọng đóng góp của các phân khúc khách hàng (`SUM(...) OVER ()`).
6. **BINNING:** Thống kê phân bố giỏ hàng theo các mức kích cỡ (`CASE WHEN ...`).

---

## 🎯 7. BỘ CÂU HỎI & TRẢ LỜI VẤN ĐÁP GIỮA KỲ (ORAL DEFENSE)

* **Hỏi:** *Tại sao em lại chọn mô hình Star Schema thay vì Snowflake Schema?*
  - **Đáp:** Star Schema chuẩn hóa phẳng bảng `dim_products` (gộp sẵn `department_name` và `aisle_name`), giúp giảm bớt các phép `JOIN` tốn kém khi truy vấn trên tập dữ liệu lớn 33+ triệu dòng, tối ưu tốc độ đọc cho các báo cáo OLAP.

* **Hỏi:** *Làm thế nào em xử lý được tập dữ liệu 33 triệu dòng trên máy cá nhân mà không bị tràn RAM?*
  - **Đáp:** Em đã áp dụng định dạng lưu trữ dạng cột nén **Apache Parquet** và hệ quản trị CSDL dạng cột nhúng **DuckDB** theo đúng khuyến nghị trong slide bài giảng. Nhờ lưu trữ dạng cột, dữ liệu giảm 77% dung lượng và DuckDB chỉ quét đúng các cột cần phân tích thay vì quét toàn bộ dòng.

* **Hỏi:** *Phân khúc khách hàng VIP, Regular trên Dashboard được tính bằng cách nào?*
  - **Đáp:** Được tính toán bằng quy tắc nghiệp vụ SQL `CASE WHEN` tại tầng ETL dựa trên tổng số đơn hàng đã đặt ($\ge 50$ đơn là VIP, $\ge 20$ là Frequent, $\ge 10$ là Regular, còn lại là New).
