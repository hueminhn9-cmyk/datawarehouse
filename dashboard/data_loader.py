import os
import sys
import duckdb
import pandas as pd
import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(ROOT_DIR, "data", "instacart_dw.duckdb")

@st.cache_resource
def get_db_connection():
    """Tạo kết nối tới CSDL DuckDB (Chế độ Read-Only an toàn)"""
    if os.path.exists(DB_PATH):
        try:
            return duckdb.connect(DB_PATH, read_only=True)
        except Exception as e:
            st.error(f"Lỗi kết nối DuckDB: {e}")
            return None
    return None

def check_db_status():
    """Kiểm tra trạng thái kết nối và số lượng bản ghi trong DuckDB"""
    con = get_db_connection()
    if con is None:
        return False, "Chưa tìm thấy file CSDL DuckDB (data/instacart_dw.duckdb)"
    try:
        tables = con.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        required = ["dim_time", "dim_departments", "dim_aisles", "dim_products", "dim_users", "fact_orders", "fact_order_items"]
        if all(r in table_names for r in required):
            total_orders = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
            total_items = con.execute("SELECT COUNT(*) FROM fact_order_items").fetchone()[0]
            return True, f"DuckDB Kho Dữ Liệu Sẵn Sàng (Live: {total_orders:,} đơn, {total_items:,} dòng chi tiết)"
        return False, "CSDL DuckDB thiếu bảng cần thiết."
    except Exception as e:
        return False, f"Lỗi đọc DuckDB: {e}"

@st.cache_data(ttl=3600)
def load_kpis():
    con = get_db_connection()
    if con:
        query = """
            SELECT 
                (SELECT COUNT(*) FROM fact_orders) AS total_orders,
                (SELECT COUNT(*) FROM dim_users) AS total_users,
                (SELECT COUNT(*) FROM dim_products) AS total_products,
                (SELECT COUNT(*) FROM fact_order_items) AS total_items,
                (SELECT ROUND(AVG(reorder_ratio) * 100, 2) FROM fact_orders) AS avg_reorder_rate,
                (SELECT ROUND(AVG(total_items), 2) FROM fact_orders) AS avg_basket_size
        """
        return con.execute(query).fetchdf().iloc[0].to_dict()
    return {
        "total_orders": 3421083, "total_users": 206209, "total_products": 49688,
        "total_items": 33819106, "avg_reorder_rate": 58.97, "avg_basket_size": 10.08
    }

@st.cache_data(ttl=3600)
def load_departments():
    con = get_db_connection()
    if con:
        return con.execute("SELECT * FROM dim_departments ORDER BY department_id").fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_aisles():
    con = get_db_connection()
    if con:
        return con.execute("SELECT * FROM dim_aisles ORDER BY aisle_id").fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_products(limit=50000):
    con = get_db_connection()
    if con:
        return con.execute(f"SELECT * FROM dim_products LIMIT {limit}").fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_top_products(dept_name=None, limit=10):
    con = get_db_connection()
    if con:
        where = f"WHERE p.department_name = '{dept_name}'" if dept_name and dept_name != "Tất cả" else ""
        query = f"""
            SELECT 
                p.product_id,
                p.product_name,
                p.department_name,
                p.aisle_name,
                COUNT(*) AS order_count,
                ROUND(AVG(CAST(foi.reordered AS DOUBLE)) * 100, 1) AS reorder_rate
            FROM fact_order_items foi
            JOIN dim_products p ON foi.product_id = p.product_id
            {where}
            GROUP BY p.product_id, p.product_name, p.department_name, p.aisle_name
            ORDER BY order_count DESC
            LIMIT {limit}
        """
        return con.execute(query).fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_dow_distribution():
    con = get_db_connection()
    if con:
        query = """
            SELECT 
                t.order_dow,
                t.dow_name,
                COUNT(*) AS order_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct
            FROM fact_orders fo
            JOIN dim_time t ON fo.time_id = t.time_id
            GROUP BY t.order_dow, t.dow_name
            ORDER BY t.order_dow
        """
        return con.execute(query).fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_hourly_distribution():
    con = get_db_connection()
    if con:
        query = """
            SELECT 
                t.order_hour_of_day,
                COUNT(*) AS order_count
            FROM fact_orders fo
            JOIN dim_time t ON fo.time_id = t.time_id
            GROUP BY t.order_hour_of_day
            ORDER BY t.order_hour_of_day
        """
        return con.execute(query).fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_customer_segments():
    con = get_db_connection()
    if con:
        query = """
            SELECT 
                user_segment,
                COUNT(*) AS total_customers,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct,
                SUM(total_orders) AS total_orders,
                ROUND(SUM(total_orders) * 100.0 / SUM(SUM(total_orders)) OVER (), 2) AS order_share_pct,
                ROUND(AVG(avg_basket_size), 2) AS avg_basket_size,
                ROUND(AVG(avg_reorder_ratio) * 100, 2) AS avg_reorder_rate_pct
            FROM dim_users
            GROUP BY user_segment
            ORDER BY total_orders DESC
        """
        return con.execute(query).fetchdf()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_table_sample(table_name, limit=100):
    con = get_db_connection()
    if con:
        allowed = ["dim_time", "dim_departments", "dim_aisles", "dim_products", "dim_users", "fact_orders", "fact_order_items"]
        if table_name in allowed:
            return con.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchdf()
    return pd.DataFrame()

def run_custom_query(sql_query):
    con = get_db_connection()
    if not con:
        raise RuntimeError("Chưa kết nối được CSDL DuckDB.")
    if not sql_query.strip().lower().startswith("select") and not sql_query.strip().lower().startswith("with"):
        raise ValueError("Chỉ chấp nhận các câu lệnh truy vấn dữ liệu SELECT / WITH.")
    return con.execute(sql_query).fetchdf()
