"""Tests for Microsoft SQL Server Data Warehouse (DataWarehouse_DB)."""

import os
import sys
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from etl.db_config import get_pyodbc_connection

def test_sqlserver_connection():
    """Kiểm tra kết nối trực tiếp pyodbc tới SQL Server."""
    conn = get_pyodbc_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION;")
    version = cursor.fetchone()[0]
    assert "Microsoft SQL Server" in version
    cursor.close()
    conn.close()

def test_sqlserver_star_schema_tables():
    """Kiểm tra sự hiện diện đầy đủ của 7 bảng Star Schema trong SQL Server."""
    conn = get_pyodbc_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        "dim_time", "dim_departments", "dim_aisles", 
        "dim_products", "dim_users", "fact_orders", "fact_order_items"
    ]
    for table in expected_tables:
        assert table in tables, f"Thiếu bảng {table} trong DataWarehouse_DB trên SQL Server"
    cursor.close()
    conn.close()

def test_sqlserver_data_present():
    """Kiểm tra dữ liệu đã nạp thành công vào các bảng Dimension và Fact."""
    conn = get_pyodbc_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_time;")
    assert cursor.fetchone()[0] == 168
    
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_departments;")
    assert cursor.fetchone()[0] == 21
    
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_aisles;")
    assert cursor.fetchone()[0] == 134
    
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_products;")
    assert cursor.fetchone()[0] >= 49000
    
    cursor.execute("SELECT COUNT(*) FROM dbo.fact_orders;")
    assert cursor.fetchone()[0] > 0
    
    cursor.execute("SELECT COUNT(*) FROM dbo.fact_order_items;")
    assert cursor.fetchone()[0] > 0
    
    cursor.execute("SELECT COUNT(*) FROM dbo.dim_users;")
    assert cursor.fetchone()[0] > 0
    
    cursor.close()
    conn.close()

def test_sqlserver_olap_query():
    """Kiểm tra câu lệnh OLAP ROLLUP chạy tốt trên SQL Server."""
    conn = get_pyodbc_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 5
            p.department_name,
            COUNT(*) AS total_items
        FROM dbo.fact_order_items foi
        JOIN dbo.dim_products p ON foi.product_id = p.product_id
        GROUP BY p.department_name
        ORDER BY total_items DESC;
    """)
    rows = cursor.fetchall()
    assert len(rows) > 0
    cursor.close()
    conn.close()
