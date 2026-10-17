import os
import pandas as pd
from etl.config import get_db_engine, DATA_DIR

CHUNK_SIZE = 100000

def run_load_facts():
    """Quy trình Trích xuất - Nạp dữ liệu vào 2 bảng Dữ kiện (Fact Tables) dùng kỹ thuật Chunking"""
    if not DATA_DIR:
        raise FileNotFoundError("Không tìm thấy thư mục chứa dữ liệu CSV thô.")

    engine = get_db_engine()

    # 1. Nạp Bảng Fact Đơn Hàng (fact_orders)
    print("--- [1/2] NẠP BẢNG DỮ KIỆN ĐƠN HÀNG (fact_orders) theo Chunk ---")
    orders_file = os.path.join(DATA_DIR, "orders.csv")
    total_orders = 0
    for chunk in pd.read_csv(orders_file, chunksize=CHUNK_SIZE):
        chunk.to_sql("fact_orders", engine, if_exists="append", index=False)
        total_orders += len(chunk)
        print(f"  ➜ Đã nạp {total_orders:,} bản ghi vào fact_orders...")
    print(f"✔ Hoàn thành nạp {total_orders:,} bản ghi vào fact_orders")

    # 2. Nạp Bảng Fact Chi Tiết Sản Phẩm Trong Đơn Hàng (fact_order_items)
    print("--- [2/2] NẠP BẢNG DỮ KIỆN CHI TIẾT ĐƠN HÀNG (fact_order_items) theo Chunk ---")
    order_items_files = ["order_products__prior.csv", "order_products__train.csv"]
    total_items = 0

    for file_name in order_items_files:
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            print(f"⚠️ Cảnh báo: Không tìm thấy file {file_name}, bỏ qua.")
            continue
            
        print(f"📌 Đang đọc dữ liệu từ file {file_name}...")
        for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE):
            chunk.to_sql("fact_order_items", engine, if_exists="append", index=False)
            total_items += len(chunk)
            print(f"  ➜ Đã nạp {total_items:,} bản ghi vào fact_order_items...")
            
    print(f"✔ Hoàn thành nạp tổng cộng {total_items:,} bản ghi vào fact_order_items")

if __name__ == "__main__":
    run_load_facts()
