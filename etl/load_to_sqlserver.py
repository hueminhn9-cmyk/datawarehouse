"""ETL pipeline to load Instacart Star Schema data into Microsoft SQL Server (DataWarehouse_DB)."""

import os
import sys
import time
import argparse
import pandas as pd
import pyarrow.parquet as pq

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Đường dẫn thư mục
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from etl.db_config import get_pyodbc_connection

def load_dim_time(cursor):
    print("\n[1/5] Nạp bảng Dim_Time...")
    cursor.execute("TRUNCATE TABLE dbo.dim_time;")
    cursor.execute("""
        ;WITH dow AS (
            SELECT 0 AS d UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 
            UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
        ),
        hr AS (
            SELECT 0 AS h UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 
            UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 
            UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
            UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15 
            UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 
            UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23
        )
        INSERT INTO dbo.dim_time (time_id, order_dow, order_hour_of_day, dow_name, hour_range, is_weekend)
        SELECT
            (dow.d * 100 + hr.h) AS time_id,
            dow.d AS order_dow,
            hr.h AS order_hour_of_day,
            CASE dow.d
                WHEN 0 THEN N'Chủ Nhật'
                WHEN 1 THEN N'Thứ Hai'
                WHEN 2 THEN N'Thứ Ba'
                WHEN 3 THEN N'Thứ Tư'
                WHEN 4 THEN N'Thứ Năm'
                WHEN 5 THEN N'Thứ Sáu'
                WHEN 6 THEN N'Thứ Bảy'
            END AS dow_name,
            CASE
                WHEN hr.h BETWEEN 0 AND 5 THEN N'Đêm (0-5h)'
                WHEN hr.h BETWEEN 6 AND 11 THEN N'Sáng (6-11h)'
                WHEN hr.h BETWEEN 12 AND 17 THEN N'Chiều (12-17h)'
                ELSE N'Tối (18-23h)'
            END AS hour_range,
            CASE WHEN dow.d IN (0, 6) THEN 1 ELSE 0 END AS is_weekend
        FROM dow CROSS JOIN hr;
    """)
    cursor.commit()
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_time;")
    cnt = cursor.fetchone()[0]
    print(f"✔ Đã nạp {cnt} khung thời gian vào dim_time.")


def load_dimensions(cursor):
    print("\n[2/5] Nạp bảng Dim_Departments và Dim_Aisles...")
    dept_df = pd.read_parquet(os.path.join(PARQUET_DIR, "departments.parquet"))
    aisle_df = pd.read_parquet(os.path.join(PARQUET_DIR, "aisles.parquet"))
    prod_df = pd.read_parquet(os.path.join(PARQUET_DIR, "products.parquet"))

    # Nạp Departments
    cursor.execute("TRUNCATE TABLE dbo.dim_departments;")
    dept_data = [(int(row['department_id']), str(row['department'])) for _, row in dept_df.iterrows()]
    cursor.executemany("INSERT INTO dbo.dim_departments (department_id, department_name) VALUES (?, ?)", dept_data)
    cursor.commit()
    print(f"✔ Đã nạp {len(dept_data)} ngành hàng vào dim_departments.")

    # Nạp Aisles
    cursor.execute("TRUNCATE TABLE dbo.dim_aisles;")
    aisle_data = [(int(row['aisle_id']), str(row['aisle'])) for _, row in aisle_df.iterrows()]
    cursor.executemany("INSERT INTO dbo.dim_aisles (aisle_id, aisle_name) VALUES (?, ?)", aisle_data)
    cursor.commit()
    print(f"✔ Đã nạp {len(aisle_data)} kệ hàng vào dim_aisles.")

    # Nạp Dim_Products (Denormalized)
    print("\n[3/5] Nạp bảng Dim_Products (Denormalized Star Schema)...")
    merged_prod = prod_df.merge(dept_df, on='department_id').merge(aisle_df, on='aisle_id')
    cursor.execute("TRUNCATE TABLE dbo.dim_products;")
    prod_data = [
        (
            int(r['product_id']),
            str(r['product_name']),
            int(r['aisle_id']),
            int(r['department_id']),
            str(r['aisle']),
            str(r['department'])
        )
        for _, r in merged_prod.iterrows()
    ]
    cursor.executemany(
        "INSERT INTO dbo.dim_products (product_id, product_name, aisle_id, department_id, aisle_name, department_name) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        prod_data
    )
    cursor.commit()
    print(f"✔ Đã nạp {len(prod_data):,} sản phẩm vào dim_products.")


def load_facts(cursor, sample_limit=None):
    print(f"\n[4/5] Nạp bảng Fact_Orders (Sample: {sample_limit if sample_limit else 'FULL'})...")
    orders_df = pd.read_parquet(os.path.join(PARQUET_DIR, "orders.parquet"))
    if sample_limit:
        orders_df = orders_df.head(sample_limit)

    cursor.execute("TRUNCATE TABLE dbo.fact_orders;")
    orders_df['time_id'] = orders_df['order_dow'] * 100 + orders_df['order_hour_of_day']
    orders_df['days_since_prior_order'] = orders_df['days_since_prior_order'].fillna(-1)

    order_records = [
        (
            int(r['order_id']),
            int(r['user_id']),
            int(r['time_id']),
            str(r['eval_set']),
            int(r['order_number']),
            int(r['order_dow']),
            int(r['order_hour_of_day']),
            float(r['days_since_prior_order']) if r['days_since_prior_order'] >= 0 else None,
            0,
            0.0
        )
        for _, r in orders_df.iterrows()
    ]
    
    # Nạp theo batch
    chunk_size = 20000
    for i in range(0, len(order_records), chunk_size):
        chunk = order_records[i:i+chunk_size]
        cursor.executemany(
            "INSERT INTO dbo.fact_orders (order_id, user_id, time_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order, total_items, reorder_ratio) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            chunk
        )
        cursor.commit()
    print(f"✔ Đã nạp {len(order_records):,} đơn hàng vào fact_orders.")

    print(f"\n[5/5] Nạp bảng Fact_Order_Items...")
    prior_path = os.path.join(PARQUET_DIR, "order_products__prior.parquet")
    train_path = os.path.join(PARQUET_DIR, "order_products__train.parquet")
    
    valid_order_ids = set(orders_df['order_id'])
    cursor.execute("TRUNCATE TABLE dbo.fact_order_items;")
    
    for path, name in [(prior_path, "Prior"), (train_path, "Train")]:
        df_items = pd.read_parquet(path)
        if sample_limit:
            df_items = df_items[df_items['order_id'].isin(valid_order_ids)]
        
        item_records = [
            (
                int(r['order_id']),
                int(r['product_id']),
                int(r['add_to_cart_order']),
                1 if r['reordered'] else 0
            )
            for _, r in df_items.iterrows()
        ]
        
        for i in range(0, len(item_records), chunk_size):
            chunk = item_records[i:i+chunk_size]
            cursor.executemany(
                "INSERT INTO dbo.fact_order_items (order_id, product_id, add_to_cart_order, reordered) "
                "VALUES (?, ?, ?, ?)",
                chunk
            )
            cursor.commit()
        print(f"✔ Đã nạp {len(item_records):,} chi tiết mặt hàng ({name}).")


def update_metrics_and_dim_users(cursor):
    print("\n⚡ Cập nhật metrics cho fact_orders và phân khúc khách hàng dim_users...")
    t_start = time.time()
    
    # Cập nhật fact_orders
    cursor.execute("""
        ;WITH OrderAgg AS (
            SELECT 
                order_id, 
                COUNT(*) AS total_items,
                AVG(CAST(reordered AS FLOAT)) AS reorder_ratio
            FROM dbo.fact_order_items
            GROUP BY order_id
        )
        UPDATE fo
        SET 
            fo.total_items = oa.total_items,
            fo.reorder_ratio = oa.reorder_ratio
        FROM dbo.fact_orders fo
        JOIN OrderAgg oa ON fo.order_id = oa.order_id;
    """)
    cursor.commit()
    print(f"✔ Đã cập nhật metrics (total_items, reorder_ratio) cho fact_orders.")

    # Nạp Dim_Users
    cursor.execute("TRUNCATE TABLE dbo.dim_users;")
    cursor.execute("""
        ;WITH order_stats AS (
            SELECT 
                user_id,
                COUNT(*) AS total_orders,
                AVG(days_since_prior_order) AS avg_days_between_orders
            FROM dbo.fact_orders
            GROUP BY user_id
        ),
        user_item_stats AS (
            SELECT
                o.user_id,
                COUNT(i.product_id) AS total_items,
                AVG(CAST(i.reordered AS FLOAT)) AS avg_reorder_ratio
            FROM dbo.fact_orders o
            JOIN dbo.fact_order_items i ON o.order_id = i.order_id
            GROUP BY o.user_id
        )
        INSERT INTO dbo.dim_users (user_id, user_segment, total_orders, total_items, avg_basket_size, avg_reorder_ratio, avg_days_between_orders)
        SELECT 
            os.user_id,
            CASE 
                WHEN os.total_orders >= 50 THEN N'VIP'
                WHEN os.total_orders >= 20 THEN N'Frequent'
                WHEN os.total_orders >= 10 THEN N'Regular'
                ELSE N'New'
            END AS user_segment,
            os.total_orders,
            COALESCE(uis.total_items, 0) AS total_items,
            ROUND(COALESCE(uis.total_items, 0) * 1.0 / os.total_orders, 2) AS avg_basket_size,
            ROUND(COALESCE(uis.avg_reorder_ratio, 0.0), 4) AS avg_reorder_ratio,
            ROUND(os.avg_days_between_orders, 2) AS avg_days_between_orders
        FROM order_stats os
        LEFT JOIN user_item_stats uis ON os.user_id = uis.user_id;
    """)
    cursor.commit()
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_users;")
    cnt_u = cursor.fetchone()[0]
    print(f"✔ Đã nạp {cnt_u:,} khách hàng vào dim_users ({time.time() - t_start:.2f}s).")


def main():
    parser = argparse.ArgumentParser(description="Load Instacart Star Schema into SQL Server")
    parser.add_argument("--sample", type=int, default=50000, help="Số lượng orders nạp mẫu (Mặc định 50,000 để chạy nhanh)")
    parser.add_argument("--full", action="store_true", help="Nạp toàn bộ dữ liệu 3.4M orders")
    args = parser.parse_args()

    sample_limit = None if args.full else args.sample

    print("=" * 70)
    print("🚀 BẮT ĐẦU XÂY DỰNG KHO DỮ LIỆU INSTACART TRÊN SQL SERVER (DataWarehouse_DB)")
    print(f"Chế độ: {'TOÀN BỘ (FULL)' if args.full else f'MẪU ({sample_limit:,} orders)'}")
    print("=" * 70)

    total_start = time.time()
    conn = get_pyodbc_connection()
    cursor = conn.cursor()
    cursor.fast_executemany = True

    try:
        load_dim_time(cursor)
        load_dimensions(cursor)
        load_facts(cursor, sample_limit)
        update_metrics_and_dim_users(cursor)
        
        print("\n" + "=" * 70)
        print(f"🎉 HOÀN TẤT NẠP KHO DỮ LIỆU SQL SERVER TRONG {time.time() - total_start:.2f} GIÂY!")
        print("=" * 70)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
