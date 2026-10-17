-- ==========================================================
-- BƯỚC 2: THIẾT KẾ CÁC BẢNG DIM VÀ FACT (STAR SCHEMA)
-- ==========================================================

USE instacart_dw;

-- 1. BẢNG CHIỀU KỆ HÀNG (dim_aisles)
CREATE TABLE IF NOT EXISTS dim_aisles (
    aisle_id INT PRIMARY KEY,
    aisle VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. BẢNG CHIỀU NGÀNH HÀNG (dim_departments)
CREATE TABLE IF NOT EXISTS dim_departments (
    department_id INT PRIMARY KEY,
    department VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. BẢNG CHIỀU SẢN PHẨM (dim_products)
CREATE TABLE IF NOT EXISTS dim_products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    aisle_id INT NOT NULL,
    department_id INT NOT NULL,
    CONSTRAINT fk_prod_aisle FOREIGN KEY (aisle_id) REFERENCES dim_aisles(aisle_id),
    CONSTRAINT fk_prod_dept FOREIGN KEY (department_id) REFERENCES dim_departments(department_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. BẢNG CHIỀU KHÁCH HÀNG (dim_users)
CREATE TABLE IF NOT EXISTS dim_users (
    user_id INT PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. BẢNG CHIỀU THỜI GIAN (dim_time)
CREATE TABLE IF NOT EXISTS dim_time (
    time_id INT AUTO_INCREMENT PRIMARY KEY,
    order_dow INT NOT NULL,
    order_hour_of_day INT NOT NULL,
    days_since_prior_order FLOAT NULL,
    INDEX idx_time_dow_hour (order_dow, order_hour_of_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. BẢNG DỮ KIỆN ĐƠN HÀNG (fact_orders)
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    eval_set VARCHAR(10) NOT NULL,
    order_number INT NOT NULL,
    order_dow INT NOT NULL,
    order_hour_of_day INT NOT NULL,
    days_since_prior_order FLOAT NULL,
    INDEX idx_orders_user (user_id),
    INDEX idx_orders_dow_hour (order_dow, order_hour_of_day),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. BẢNG DỮ KIỆN CHI TIẾT SẢN PHẨM TRONG ĐƠN HÀNG (fact_order_items)
CREATE TABLE IF NOT EXISTS fact_order_items (
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    add_to_cart_order INT NOT NULL,
    reordered INT NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, product_id),
    INDEX idx_items_order (order_id),
    INDEX idx_items_product (product_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
