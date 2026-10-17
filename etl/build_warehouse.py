import os
import sys
import time
import duckdb

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet")
DB_PATH = os.path.join(BASE_DIR, "data", "instacart_dw.duckdb")
SQL_SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "01_schema_duckdb.sql")

def build_duckdb_warehouse():
    print("=" * 70)
    print("🚀 BẮT ĐẦU XÂY DỰNG KHO DỮ LIỆU INSTACART TRÊN DUCKDB (STAR SCHEMA)")
    print("=" * 70)
    
    total_start = time.time()
    
    # 1. Kết nối CSDL DuckDB
    print(f"📦 Đang kết nối CSDL DuckDB: {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    
    # 2. Khởi tạo cấu trúc bảng Star Schema
    print("🛠️ Đang thực thi DDL tạo các bảng Fact & Dimension...")
    with open(SQL_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    con.execute(schema_sql)
    print("✔ Đã tạo thành công cấu trúc bảng Star Schema.")
    
    # 3. Nạp Bảng Chiều Thời Gian (Dim_Time: 168 trạng thái)
    print("\n[1/5] Nạp bảng Dim_Time...")
    con.execute("""
        DELETE FROM dim_time;
        INSERT INTO dim_time
        SELECT
            (dow.d * 100 + hr.h) AS time_id,
            dow.d AS order_dow,
            hr.h AS order_hour_of_day,
            CASE dow.d
                WHEN 0 THEN 'Chủ Nhật'
                WHEN 1 THEN 'Thứ Hai'
                WHEN 2 THEN 'Thứ Ba'
                WHEN 3 THEN 'Thứ Tư'
                WHEN 4 THEN 'Thứ Năm'
                WHEN 5 THEN 'Thứ Sáu'
                WHEN 6 THEN 'Thứ Bảy'
            END AS dow_name,
            CASE
                WHEN hr.h BETWEEN 0 AND 5 THEN 'Đêm (0-5h)'
                WHEN hr.h BETWEEN 6 AND 11 THEN 'Sáng (6-11h)'
                WHEN hr.h BETWEEN 12 AND 17 THEN 'Chiều (12-17h)'
                ELSE 'Tối (18-23h)'
            END AS hour_range,
            CASE WHEN dow.d IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
        FROM (SELECT unnest(range(0, 7)) AS d) dow
        CROSS JOIN (SELECT unnest(range(0, 24)) AS h) hr;
    """)
    cnt = con.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0]
    print(f"✔ Đã nạp {cnt} khung thời gian vào dim_time.")
    
    # 4. Nạp Bảng Chiều Ngành Hàng & Kệ Hàng
    dept_p = os.path.join(PARQUET_DIR, "departments.parquet").replace("\\", "/")
    aisle_p = os.path.join(PARQUET_DIR, "aisles.parquet").replace("\\", "/")
    prod_p = os.path.join(PARQUET_DIR, "products.parquet").replace("\\", "/")
    
    print("\n[2/5] Nạp bảng Dim_Departments và Dim_Aisles...")
    con.execute(f"""
        DELETE FROM dim_departments;
        INSERT INTO dim_departments SELECT department_id, department AS department_name FROM read_parquet('{dept_p}');
        
        DELETE FROM dim_aisles;
        INSERT INTO dim_aisles SELECT aisle_id, aisle AS aisle_name FROM read_parquet('{aisle_p}');
    """)
    cnt_d = con.execute("SELECT COUNT(*) FROM dim_departments").fetchone()[0]
    cnt_a = con.execute("SELECT COUNT(*) FROM dim_aisles").fetchone()[0]
    print(f"✔ Đã nạp {cnt_d} ngành hàng vào dim_departments và {cnt_a} kệ hàng vào dim_aisles.")
    
    # 5. Nạp Bảng Chiều Sản Phẩm Chuẩn Star Schema (Denormalized)
    print("\n[3/5] Nạp bảng Dim_Products (Denormalized Star Schema)...")
    con.execute(f"""
        DELETE FROM dim_products;
        INSERT INTO dim_products
        SELECT 
            p.product_id,
            p.product_name,
            p.aisle_id,
            p.department_id,
            a.aisle AS aisle_name,
            d.department AS department_name
        FROM read_parquet('{prod_p}') p
        JOIN read_parquet('{aisle_p}') a ON p.aisle_id = a.aisle_id
        JOIN read_parquet('{dept_p}') d ON p.department_id = d.department_id;
    """)
    cnt_p = con.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
    print(f"✔ Đã nạp {cnt_p:,} sản phẩm vào dim_products.")
    
    # 6. Nạp Bảng Dữ Kiện Đơn Hàng (Fact_Orders)
    orders_p = os.path.join(PARQUET_DIR, "orders.parquet").replace("\\", "/")
    print(f"\n[4/5] Nạp bảng Fact_Orders từ orders.parquet...")
    t_start = time.time()
    con.execute(f"""
        DELETE FROM fact_orders;
        INSERT INTO fact_orders (order_id, user_id, time_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order)
        SELECT 
            order_id,
            user_id,
            (order_dow * 100 + order_hour_of_day) AS time_id,
            eval_set,
            order_number,
            order_dow,
            order_hour_of_day,
            days_since_prior_order
        FROM read_parquet('{orders_p}');
    """)
    cnt_o = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    print(f"✔ Đã nạp {cnt_o:,} đơn hàng vào fact_orders ({time.time() - t_start:.2f}s).")
    
    # 7. Nạp Bảng Dữ Kiện Chi Tiết Đơn Hàng (Fact_Order_Items - 33.8 triệu dòng)
    prior_p = os.path.join(PARQUET_DIR, "order_products__prior.parquet").replace("\\", "/")
    train_p = os.path.join(PARQUET_DIR, "order_products__train.parquet").replace("\\", "/")
    print(f"\n[5/5] Nạp bảng Fact_Order_Items (33+ triệu dòng chi tiết giỏ hàng)...")
    t_start = time.time()
    con.execute(f"""
        DELETE FROM fact_order_items;
        INSERT INTO fact_order_items
        SELECT order_id, product_id, add_to_cart_order, reordered
        FROM read_parquet('{prior_p}')
        UNION ALL
        SELECT order_id, product_id, add_to_cart_order, reordered
        FROM read_parquet('{train_p}');
    """)
    cnt_items = con.execute("SELECT COUNT(*) FROM fact_order_items").fetchone()[0]
    print(f"✔ Đã nạp thành công {cnt_items:,} dòng vào fact_order_items ({time.time() - t_start:.2f}s).")
    
    # 8. Cập nhật chỉ số Dẫn xuất (Derived Metrics) & Phân khúc Khách hàng (Dim_Users)
    print("\n⚡ Đang tính toán các chỉ số Dẫn xuất & Phân khúc Khách hàng (Dim_Users)...")
    t_start = time.time()
    con.execute("""
        DELETE FROM dim_users;
        INSERT INTO dim_users
        WITH order_stats AS (
            SELECT 
                user_id,
                COUNT(*) AS total_orders,
                AVG(days_since_prior_order) AS avg_days_between_orders
            FROM fact_orders
            GROUP BY user_id
        ),
        user_item_stats AS (
            SELECT
                o.user_id,
                COUNT(i.product_id) AS total_items,
                AVG(CAST(i.reordered AS DOUBLE)) AS avg_reorder_ratio
            FROM fact_orders o
            JOIN fact_order_items i ON o.order_id = i.order_id
            GROUP BY o.user_id
        )
        SELECT 
            os.user_id,
            CASE 
                WHEN os.total_orders >= 50 THEN 'VIP'
                WHEN os.total_orders >= 20 THEN 'Frequent'
                WHEN os.total_orders >= 10 THEN 'Regular'
                ELSE 'New'
            END AS user_segment,
            os.total_orders,
            COALESCE(uis.total_items, 0) AS total_items,
            ROUND(COALESCE(uis.total_items, 0) * 1.0 / os.total_orders, 2) AS avg_basket_size,
            ROUND(COALESCE(uis.avg_reorder_ratio, 0.0), 4) AS avg_reorder_ratio,
            ROUND(os.avg_days_between_orders, 2) AS avg_days_between_orders
        FROM order_stats os
        LEFT JOIN user_item_stats uis ON os.user_id = uis.user_id;
    """)
    cnt_u = con.execute("SELECT COUNT(*) FROM dim_users").fetchone()[0]
    print(f"✔ Đã nạp {cnt_u:,} khách hàng phân khúc vào dim_users ({time.time() - t_start:.2f}s).")
    
    # 9. Cập nhật chỉ số Fact_Orders (total_items, reorder_ratio)
    print("⚡ Đang cập nhật chỉ số tổng hợp cho fact_orders...")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE tmp_order_metrics AS
        SELECT 
            order_id,
            COUNT(*) AS total_items,
            AVG(CAST(reordered AS DOUBLE)) AS reorder_ratio
        FROM fact_order_items
        GROUP BY order_id;

        UPDATE fact_orders
        SET total_items = tmp.total_items,
            reorder_ratio = tmp.reorder_ratio
        FROM tmp_order_metrics tmp
        WHERE fact_orders.order_id = tmp.order_id;
    """)
    print("✔ Đã cập nhật metrics cho fact_orders thành công.")

    # Đóng kết nối
    con.close()
    
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    total_elapsed = time.time() - total_start
    print("\n" + "=" * 70)
    print(f"🎉 HOÀN THÀNH XÂY DỰNG KHO DỮ LIỆU DUCKDB TRONG {total_elapsed:.2f} GIÂY!")
    print(f"📊 Kích thước file CSDL DuckDB: {db_size:.2f} MB")
    print(f"📦 Bảng dim_time:        {cnt:,} dòng")
    print(f"📦 Bảng dim_departments: {cnt_d:,} dòng")
    print(f"📦 Bảng dim_aisles:      {cnt_a:,} dòng")
    print(f"📦 Bảng dim_products:    {cnt_p:,} dòng")
    print(f"📦 Bảng dim_users:       {cnt_u:,} dòng")
    print(f"📦 Bảng fact_orders:     {cnt_o:,} dòng")
    print(f"📦 Bảng fact_order_items:{cnt_items:,} dòng")
    print("=" * 70)

if __name__ == "__main__":
    build_duckdb_warehouse()
