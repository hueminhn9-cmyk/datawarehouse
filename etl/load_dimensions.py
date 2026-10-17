import os
import pandas as pd
from etl.config import get_db_engine, DATA_DIR

def run_load_dimensions():
    """Quy trình Trích xuất - Biến đổi - Nạp dữ liệu vào 5 bảng Chiều (Dimensions)"""
    if not DATA_DIR:
        raise FileNotFoundError("Không tìm thấy thư mục chứa dữ liệu CSV thô.")

    engine = get_db_engine()
    
    print("--- [1/5] NẠP BẢNG CHIỀU NGÀNH HÀNG (dim_departments) ---")
    dept_file = os.path.join(DATA_DIR, "departments.csv")
    df_dept = pd.read_csv(dept_file)
    if "department" not in df_dept.columns and "department_name" in df_dept.columns:
        df_dept = df_dept.rename(columns={"department_name": "department"})
    df_dept.to_sql("dim_departments", engine, if_exists="append", index=False)
    print(f"✔ Đã nạp thành công {len(df_dept):,} bản ghi vào dim_departments")

    print("--- [2/5] NẠP BẢNG CHIỀU KỆ HÀNG (dim_aisles) ---")
    aisle_file = os.path.join(DATA_DIR, "aisles.csv")
    df_aisle = pd.read_csv(aisle_file)
    if "aisle" not in df_aisle.columns and "aisle_name" in df_aisle.columns:
        df_aisle = df_aisle.rename(columns={"aisle_name": "aisle"})
    df_aisle.to_sql("dim_aisles", engine, if_exists="append", index=False)
    print(f"✔ Đã nạp thành công {len(df_aisle):,} bản ghi vào dim_aisles")

    print("--- [3/5] NẠP BẢNG CHIỀU SẢN PHẨM (dim_products) ---")
    prod_file = os.path.join(DATA_DIR, "products.csv")
    df_prod = pd.read_csv(prod_file)
    df_prod.to_sql("dim_products", engine, if_exists="append", index=False)
    print(f"✔ Đã nạp thành công {len(df_prod):,} bản ghi vào dim_products")

    print("--- [4/5] NẠP BẢNG CHIỀU KHÁCH HÀNG (dim_users) ---")
    orders_file = os.path.join(DATA_DIR, "orders.csv")
    df_users = pd.read_csv(orders_file, usecols=["user_id"]).drop_duplicates()
    df_users.to_sql("dim_users", engine, if_exists="append", index=False)
    print(f"✔ Đã nạp thành công {len(df_users):,} bản ghi vào dim_users")

    print("--- [5/5] NẠP BẢNG CHIỀU THỜI GIAN (dim_time) ---")
    df_time = pd.read_csv(orders_file, usecols=["order_dow", "order_hour_of_day", "days_since_prior_order"]).drop_duplicates()
    df_time.to_sql("dim_time", engine, if_exists="append", index=False)
    print(f"✔ Đã nạp thành công {len(df_time):,} bản ghi vào dim_time")

if __name__ == "__main__":
    run_load_dimensions()
