-- ====================================================================
-- DDL THIẾT KẾ KHO DỮ LIỆU INSTACART THEO MÔ HÌNH HÌNH SAO (STAR SCHEMA)
-- HỆ QUẢN TRỊ CSDL: MICROSOFT SQL SERVER (T-SQL)
-- ====================================================================

-- 0. TẠO CƠ SỞ DỮ LIỆU NẾU CHƯA TỒN TẠI
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'DataWarehouse_DB')
BEGIN
    CREATE DATABASE DataWarehouse_DB;
    PRINT N'✔ Đã tạo mới cơ sở dữ liệu DataWarehouse_DB.';
END
GO

USE DataWarehouse_DB;
GO

-- 1. BẢNG CHIỀU THỜI GIAN TUẦN HOÀN (Dim_Time: 168 trạng thái = 7 ngày x 24 giờ)
IF OBJECT_ID(N'dbo.dim_time', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_time (
        time_id INT PRIMARY KEY,
        order_dow TINYINT NOT NULL,
        order_hour_of_day TINYINT NOT NULL,
        dow_name NVARCHAR(50) NOT NULL,
        hour_range NVARCHAR(50) NOT NULL,
        is_weekend BIT NOT NULL
    );
    PRINT N'✔ Đã tạo bảng dbo.dim_time.';
END
GO

-- 2. BẢNG CHIỀU PHÂN CẤP NGÀNH HÀNG (Dim_Department)
IF OBJECT_ID(N'dbo.dim_departments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_departments (
        department_id INT PRIMARY KEY,
        department_name NVARCHAR(100) NOT NULL
    );
    PRINT N'✔ Đã tạo bảng dbo.dim_departments.';
END
GO

-- 3. BẢNG CHIỀU KỆ HÀNG (Dim_Aisle)
IF OBJECT_ID(N'dbo.dim_aisles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_aisles (
        aisle_id INT PRIMARY KEY,
        aisle_name NVARCHAR(100) NOT NULL
    );
    PRINT N'✔ Đã tạo bảng dbo.dim_aisles.';
END
GO

-- 4. BẢNG CHIỀU SẢN PHẨM CHUẨN STAR SCHEMA (Dim_Product - Denormalized)
IF OBJECT_ID(N'dbo.dim_products', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_products (
        product_id INT PRIMARY KEY,
        product_name NVARCHAR(255) NOT NULL,
        aisle_id INT NOT NULL,
        department_id INT NOT NULL,
        aisle_name NVARCHAR(100) NOT NULL,
        department_name NVARCHAR(100) NOT NULL
    );
    PRINT N'✔ Đã tạo bảng dbo.dim_products.';
END
GO

-- 5. BẢNG CHIỀU KHÁCH HÀNG (Dim_User - Phân khúc hành vi mua sắm)
IF OBJECT_ID(N'dbo.dim_users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_users (
        user_id INT PRIMARY KEY,
        user_segment NVARCHAR(50) NOT NULL,
        total_orders INT NOT NULL,
        total_items INT NOT NULL,
        avg_basket_size FLOAT NOT NULL,
        avg_reorder_ratio FLOAT NOT NULL,
        avg_days_between_orders FLOAT NULL
    );
    PRINT N'✔ Đã tạo bảng dbo.dim_users.';
END
GO

-- 6. BẢNG DỮ KIỆN ĐƠN HÀNG (Fact_Orders - Hạt đơn hàng / Order Grain)
IF OBJECT_ID(N'dbo.fact_orders', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_orders (
        order_id INT PRIMARY KEY,
        user_id INT NOT NULL,
        time_id INT NOT NULL,
        eval_set NVARCHAR(20) NOT NULL,
        order_number INT NOT NULL,
        order_dow TINYINT NOT NULL,
        order_hour_of_day TINYINT NOT NULL,
        days_since_prior_order FLOAT NULL,
        total_items INT DEFAULT 0,
        reorder_ratio FLOAT DEFAULT 0.0
    );
    
    CREATE NONCLUSTERED INDEX IX_fact_orders_time_id ON dbo.fact_orders(time_id);
    CREATE NONCLUSTERED INDEX IX_fact_orders_user_id ON dbo.fact_orders(user_id);
    PRINT N'✔ Đã tạo bảng dbo.fact_orders và các chỉ mục.';
END
GO

-- 7. BẢNG DỮ KIỆN CHI TIẾT SẢN PHẨM TRONG ĐƠN (Fact_Order_Items - Hạt mặt hàng / Line-item Grain)
IF OBJECT_ID(N'dbo.fact_order_items', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_order_items (
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        add_to_cart_order SMALLINT NOT NULL,
        reordered BIT NOT NULL,
        CONSTRAINT PK_fact_order_items PRIMARY KEY (order_id, product_id)
    );
    
    CREATE NONCLUSTERED INDEX IX_fact_order_items_product_id ON dbo.fact_order_items(product_id);
    PRINT N'✔ Đã tạo bảng dbo.fact_order_items và các chỉ mục.';
END
GO

PRINT N'🚀 KHỞI TẠO CẤU TRÚC STAR SCHEMA TRÊN SQL SERVER THÀNH CÔNG!';
GO
