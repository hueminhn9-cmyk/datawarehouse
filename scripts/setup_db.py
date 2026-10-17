import os
import sys
import pymysql
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load file môi trường .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "instacart_dw")

def execute_sql_file(cursor, filepath):
    print(f"Executing: {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Chia nhỏ từng câu lệnh theo dấu chấm phẩy
    statements = sql.split(';')
    for statement in statements:
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)

def main():
    print("--- TỰ ĐỘNG KHỞI TẠO CSDL VÀ BẢNG KHO DỮ LIỆU ---")
    try:
        # 1. Kết nối tới MySQL Server
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        print(f"✔ Kết nối thành công tới MySQL Server tại {DB_HOST}:{DB_PORT}")
        
        with connection.cursor() as cursor:
            # 2. Tạo Database
            sql_db = os.path.join(os.path.dirname(__file__), "..", "sql", "01_create_database.sql")
            execute_sql_file(cursor, sql_db)
            
            # 3. Kết nối vào Database vừa tạo và Tạo Bảng
            connection.select_db(DB_NAME)
            sql_tables = os.path.join(os.path.dirname(__file__), "..", "sql", "02_create_tables.sql")
            execute_sql_file(cursor, sql_tables)
            
        print(f"🎉 KHỞI TẠO THÀNH CÔNG DATABASE '{DB_NAME}' VÀ CÁC BẢNG STAR SCHEMA!")
        connection.close()

    except pymysql.MySQLError as e:
        print(f"❌ Lỗi kết nối CSDL: {e}")
        print("💡 Gợi ý: Hãy bật Laragon (bấm 'Start All') và kiểm tra port MySQL 3306.")

if __name__ == "__main__":
    main()
