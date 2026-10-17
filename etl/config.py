import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Cấu hình CSDL từ Environment Variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "instacart_dw")

# Tìm đường dẫn chứa file CSV thô
POSSIBLE_DATA_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "data"),
    r"d:\DataWarehouse\InstacartDataWarehouse\data",
    r"d:\DataWarehouse\DataWarehouse\data",
]

DATA_DIR = None
for path in POSSIBLE_DATA_PATHS:
    if os.path.exists(os.path.join(path, "departments.csv")):
        DATA_DIR = os.path.abspath(path)
        break

def get_db_engine():
    """Tạo và trả về kết nối SQLAlchemy engine tới MySQL/MariaDB"""
    connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    return create_engine(connection_string, echo=False)
