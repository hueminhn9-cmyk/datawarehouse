import os
import sys
import pytest
import duckdb

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(ROOT_DIR, "data", "instacart_dw.duckdb")
PARQUET_DIR = os.path.join(ROOT_DIR, "data", "parquet")

def test_parquet_files_exist():
    """Kiểm tra các file Parquet đã được nén từ CSV thành công"""
    required_files = [
        "departments.parquet", "aisles.parquet", "products.parquet",
        "orders.parquet", "order_products__train.parquet", "order_products__prior.parquet"
    ]
    for file_name in required_files:
        path = os.path.join(PARQUET_DIR, file_name)
        assert os.path.exists(path), f"Thiếu file parquet: {file_name}"

def test_duckdb_connection_and_tables():
    """Kiểm tra kết nối DuckDB và sự hiện diện của 7 bảng Star Schema"""
    assert os.path.exists(DB_PATH), "Không tìm thấy file CSDL instacart_dw.duckdb"
    con = duckdb.connect(DB_PATH, read_only=True)
    tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
    
    expected_tables = [
        "dim_time", "dim_departments", "dim_aisles", 
        "dim_products", "dim_users", "fact_orders", "fact_order_items"
    ]
    for table in expected_tables:
        assert table in tables, f"Thiếu bảng {table} trong DuckDB"
    con.close()

def test_data_integrity_counts():
    """Kiểm tra số lượng bản ghi tối thiểu trong kho dữ liệu"""
    con = duckdb.connect(DB_PATH, read_only=True)
    orders_cnt = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    items_cnt = con.execute("SELECT COUNT(*) FROM fact_order_items").fetchone()[0]
    prods_cnt = con.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
    users_cnt = con.execute("SELECT COUNT(*) FROM dim_users").fetchone()[0]
    
    assert orders_cnt > 3_000_000, "Bảng fact_orders phải có hơn 3 triệu đơn"
    assert items_cnt > 30_000_000, "Bảng fact_order_items phải có hơn 30 triệu dòng"
    assert prods_cnt >= 49_000, "Bảng dim_products phải có gần 50k sản phẩm"
    assert users_cnt > 200_000, "Bảng dim_users phải có hơn 200k khách hàng"
    con.close()

def test_olap_rollup_query():
    """Kiểm tra câu lệnh truy vấn OLAP ROLLUP chạy trơn tru trên DuckDB"""
    con = duckdb.connect(DB_PATH, read_only=True)
    res = con.execute("""
        SELECT 
            department_name,
            COUNT(*) AS total_items
        FROM fact_order_items foi
        JOIN dim_products p ON foi.product_id = p.product_id
        GROUP BY department_name
        ORDER BY total_items DESC
        LIMIT 5
    """).fetchall()
    assert len(res) == 5
    assert res[0][0] == "produce"  # Ngành hàng nông sản luôn có số lượng bán nhiều nhất
    con.close()
