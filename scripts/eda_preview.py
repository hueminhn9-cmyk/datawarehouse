import os
import sys
import pandas as pd

# Thiết lập UTF-8 cho console output trên Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Tìm đường dẫn thư mục chứa dữ liệu CSV thô
POSSIBLE_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "data"),
    r"d:\DataWarehouse\InstacartDataWarehouse\data",
]

DATA_DIR = None
for path in POSSIBLE_PATHS:
    if os.path.exists(os.path.join(path, "departments.csv")):
        DATA_DIR = path
        break

def preview_csv(filename, nrows=5):
    if not DATA_DIR:
        print("Không tìm thấy thư mục dữ liệu CSV.")
        return
        
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File {filename} không tồn tại tại {filepath}")
        return
    
    df = pd.read_csv(filepath, nrows=nrows)
    
    print(f"\n==========================================")
    print(f" File: {filename}")
    print(f"==========================================")
    print("Cấu trúc các cột (Data Types):")
    for col, dtype in df.dtypes.items():
        print(f"  - {col}: {dtype}")
    print("\n5 dòng đầu tiên:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    print(f"--- KIỂM TRA DỮ LIỆU THÔ INSTACART (Thư mục: {DATA_DIR}) ---")
    preview_csv("departments.csv")
    preview_csv("aisles.csv")
    preview_csv("products.csv")
    preview_csv("orders.csv")
    preview_csv("order_products__train.csv")
