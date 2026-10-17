import sys
import time
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from etl.convert_to_parquet import convert_csv_to_parquet
from etl.build_warehouse import build_duckdb_warehouse

def main():
    start_time = time.time()
    print("=" * 70)
    print("🚀 BẮT ĐẦU QUY TRÌNH ETL TOÀN DIỆN KHO DỮ LIỆU INSTACART (GIỮA KỲ)")
    print("=" * 70)
    
    try:
        logging.info("Giai đoạn 1: Chuyển đổi CSV thô sang Apache Parquet nén (Polars)...")
        convert_csv_to_parquet()
        
        logging.info("Giai đoạn 2: Nạp dữ liệu vào Mô hình Star Schema trên DuckDB...")
        build_duckdb_warehouse()
        
        elapsed = time.time() - start_time
        print("=" * 70)
        print(f"🎉 HOÀN THÀNH TOÀN BỘ QUY TRÌNH ETL DWH TRONG {elapsed:.2f} GIÂY!")
        print("💡 Hệ thống Kho Dữ Liệu đã sẵn sàng để truy vấn và trực quan hóa Dashboard!")
        print("=" * 70)
    except Exception as e:
        logging.error(f"❌ XẢY RA LỖI TRONG QUY TRÌNH ETL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
