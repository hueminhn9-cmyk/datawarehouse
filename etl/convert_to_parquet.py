import os
import sys
import time
import polars as pl

# Thiết lập bảng mã UTF-8 cho Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Đường dẫn dữ liệu
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DATA_DIR = r"d:\DataWarehouse\InstacartDataWarehouse\data"
TARGET_PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet")

FILES = [
    ("departments.csv", "departments.parquet"),
    ("aisles.csv", "aisles.parquet"),
    ("products.csv", "products.parquet"),
    ("orders.csv", "orders.parquet"),
    ("order_products__train.csv", "order_products__train.parquet"),
    ("order_products__prior.csv", "order_products__prior.parquet"),
]

def convert_csv_to_parquet():
    print("=" * 65)
    print("🚀 BẮT ĐẦU CHUYỂN ĐỔI DỮ LIỆU CSV SANG PARQUET (BẰNG POLARS)")
    print("=" * 65)
    
    if not os.path.exists(SOURCE_DATA_DIR):
        print(f"❌ Không tìm thấy thư mục nguồn: {SOURCE_DATA_DIR}")
        sys.exit(1)
        
    os.makedirs(TARGET_PARQUET_DIR, exist_ok=True)
    total_start = time.time()
    
    total_csv_size = 0
    total_parquet_size = 0
    
    for csv_name, parquet_name in FILES:
        csv_path = os.path.join(SOURCE_DATA_DIR, csv_name)
        parquet_path = os.path.join(TARGET_PARQUET_DIR, parquet_name)
        
        if not os.path.exists(csv_path):
            print(f"⚠️ Bỏ qua {csv_name}: Không tìm thấy file.")
            continue
            
        csv_size = os.path.getsize(csv_path) / (1024 * 1024)
        total_csv_size += csv_size
        
        print(f"\n📂 Đang xử lý: {csv_name} ({csv_size:.2f} MB)...")
        file_start = time.time()
        
        # Đọc bằng Polars (tận dụng multi-threading cực nhanh)
        df = pl.read_csv(csv_path)
        row_count = len(df)
        
        # Ghi sang định dạng Parquet với chuẩn nén snappy
        df.write_parquet(parquet_path, compression="snappy")
        
        parquet_size = os.path.getsize(parquet_path) / (1024 * 1024)
        total_parquet_size += parquet_size
        elapsed = time.time() - file_start
        
        compression_ratio = (1 - (parquet_size / csv_size)) * 100 if csv_size > 0 else 0
        print(f"  ✔ Đã chuyển {row_count:,} dòng sang {parquet_name}")
        print(f"  ✔ Dung lượng: {csv_size:.2f} MB ➔ {parquet_size:.2f} MB (Tiết kiệm {compression_ratio:.1f}%)")
        print(f"  ✔ Thời gian: {elapsed:.2f} giây")

    total_elapsed = time.time() - total_start
    total_ratio = (1 - (total_parquet_size / total_csv_size)) * 100 if total_csv_size > 0 else 0
    print("\n" + "=" * 65)
    print(f"🎉 HOÀN THÀNH CHUYỂN ĐỔI TOÀN BỘ SANG PARQUET TRONG {total_elapsed:.2f} GIÂY!")
    print(f"📊 Tổng dung lượng CSV gốc:     {total_csv_size:.2f} MB")
    print(f"📊 Tổng dung lượng Parquet nén: {total_parquet_size:.2f} MB")
    print(f"💡 Giảm được: {total_ratio:.1f}% dung lượng đĩa cứng!")
    print("=" * 65)

if __name__ == "__main__":
    convert_csv_to_parquet()
