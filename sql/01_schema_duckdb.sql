-- ====================================================================
-- DDL THIẾT KẾ KHO DỮ LIỆU INSTACART THEO MÔ HÌNH HÌNH SAO (STAR SCHEMA)
-- HỆ QUẢN TRỊ CSDL: DUCKDB
-- ====================================================================

-- 1. BẢNG CHIỀU THỜI GIAN TUẦN HOÀN (Dim_Time: 168 trạng thái = 7 ngày x 24 giờ)
CREATE TABLE IF NOT EXISTS dim_time (
    time_id INT PRIMARY KEY,
    order_dow TINYINT NOT NULL,
    order_hour_of_day TINYINT NOT NULL,
    dow_name VARCHAR(15) NOT NULL,
    hour_range VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. BẢNG CHIỀU PHÂN CẤP NGÀNH HÀNG (Dim_Department)
CREATE TABLE IF NOT EXISTS dim_departments (
    department_id INT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL
);

-- 3. BẢNG CHIỀU KỆ HÀNG (Dim_Aisle)
CREATE TABLE IF NOT EXISTS dim_aisles (
    aisle_id INT PRIMARY KEY,
    aisle_name VARCHAR(100) NOT NULL
);

-- 4. BẢNG CHIỀU SẢN PHẨM CHUẨN STAR SCHEMA (Dim_Product - Denormalized)
CREATE TABLE IF NOT EXISTS dim_products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    aisle_id INT NOT NULL,
    department_id INT NOT NULL,
    aisle_name VARCHAR(100) NOT NULL,
    department_name VARCHAR(100) NOT NULL
);

-- 5. BẢNG CHIỀU KHÁCH HÀNG (Dim_User - Phân khúc hành vi mua sắm)
CREATE TABLE IF NOT EXISTS dim_users (
    user_id INT PRIMARY KEY,
    user_segment VARCHAR(20) NOT NULL,
    total_orders INT NOT NULL,
    total_items INT NOT NULL,
    avg_basket_size DOUBLE NOT NULL,
    avg_reorder_ratio DOUBLE NOT NULL,
    avg_days_between_orders DOUBLE NULL
);

-- 6. BẢNG DỮ KIỆN ĐƠN HÀNG (Fact_Orders - Hạt đơn hàng / Order Grain)
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    time_id INT NOT NULL,
    eval_set VARCHAR(10) NOT NULL,
    order_number INT NOT NULL,
    order_dow TINYINT NOT NULL,
    order_hour_of_day TINYINT NOT NULL,
    days_since_prior_order DOUBLE NULL,
    total_items INT DEFAULT 0,
    reorder_ratio DOUBLE DEFAULT 0.0
);

-- 7. BẢNG DỮ KIỆN CHI TIẾT SẢN PHẨM TRONG ĐƠN (Fact_Order_Items - Hạt mặt hàng / Line-item Grain)
CREATE TABLE IF NOT EXISTS fact_order_items (
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    add_to_cart_order SMALLINT NOT NULL,
    reordered BOOLEAN NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
