"""Database connection configuration for Microsoft SQL Server."""

import os
import urllib.parse
from pathlib import Path
import pyodbc
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Tự động nạp cấu hình từ .env ở thư mục gốc dự án
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Cấu hình kết nối SQL Server (Default: .\SQLEXPRESS)
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlserver")
SQL_SERVER = os.environ.get("SQL_SERVER", r".\SQLEXPRESS")
SQL_DATABASE = os.environ.get("SQL_DATABASE", "DataWarehouse_DB")
SQL_DRIVER = os.environ.get("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

# Chuỗi kết nối ODBC dùng cho pyodbc
ODBC_CONNECTION_STRING = (
    f"Driver={{{SQL_DRIVER}}};"
    f"Server={SQL_SERVER};"
    f"Database={SQL_DATABASE};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

def get_pyodbc_connection():
    """Tạo kết nối trực tiếp pyodbc với SQL Server."""
    return pyodbc.connect(ODBC_CONNECTION_STRING)

def get_sqlalchemy_engine():
    """Tạo SQLAlchemy engine kết nối với SQL Server."""
    params = urllib.parse.quote_plus(ODBC_CONNECTION_STRING)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)
