import os
import sys
import subprocess

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 65)
    print("🚀 ĐANG KHỞI CHẠY DASHBOARD STREAMLIT KHO DỮ LIỆU INSTACART...")
    print("=" * 65)
    
    app_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    print(f"Lệnh thực thi: {' '.join(cmd)}")
    print("Đang mở trình duyệt tại: http://localhost:8501")
    print("Nhấn Ctrl + C để dừng Dashboard.")
    print("=" * 65)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Đã dừng Dashboard thành công.")

if __name__ == "__main__":
    main()
