-- ==============================================================================
-- KỊCH BẢN TRUY VẤN PHÂN TÍCH OLAP NÂNG CAO TRÊN KHO DỮ LIỆU INSTACART
-- HỆ QUẢN TRỊ CSDL: MICROSOFT SQL SERVER (T-SQL)
-- DATABASE: DataWarehouse_DB
-- ==============================================================================

USE DataWarehouse_DB;
GO

-- ------------------------------------------------------------------------------
-- CÂU 1: PHÉP TOÁN ROLL-UP (TỔNG HỢP THEO THỨ BẬC PHÂN CẤP SẢN PHẨM)
-- Nghiệp vụ: Tính tổng số sản phẩm bán ra theo phân cấp Ngành hàng -> Kệ hàng.
-- Cú pháp OLAP: GROUP BY ROLLUP (department_name, aisle_name)
-- ------------------------------------------------------------------------------
SELECT TOP 25
    COALESCE(p.department_name, N'=== TỔNG TOÀN BỘ SIÊU THỊ ===') AS department_name,
    COALESCE(p.aisle_name, N'--- TỔNG NGÀNH HÀNG ---') AS aisle_name,
    COUNT(*) AS total_items_sold,
    ROUND(AVG(CAST(foi.reordered AS FLOAT)) * 100, 2) AS avg_reorder_rate_pct
FROM dbo.fact_order_items foi
JOIN dbo.dim_products p ON foi.product_id = p.product_id
GROUP BY ROLLUP (p.department_name, p.aisle_name)
ORDER BY 
    GROUPING(p.department_name) DESC, 
    total_items_sold DESC;
GO


-- ------------------------------------------------------------------------------
-- CÂU 2: PHÉP TOÁN CUBE (PHÂN TÍCH ĐA CHIỀU KHÔNG GIAN THỜI GIAN)
-- Nghiệp vụ: Phân tích số lượng đơn hàng theo mọi tổ hợp giữa Ngày trong tuần x Khung giờ.
-- Cú pháp OLAP: GROUP BY CUBE (dow_name, hour_range)
-- ------------------------------------------------------------------------------
SELECT TOP 30
    COALESCE(t.dow_name, N'TẤT CẢ CÁC NGÀY') AS dow_name,
    COALESCE(t.hour_range, N'TẤT CẢ KHUNG GIỜ') AS hour_range,
    COUNT(DISTINCT fo.order_id) AS total_orders,
    ROUND(AVG(CAST(fo.total_items AS FLOAT)), 2) AS avg_basket_size
FROM dbo.fact_orders fo
JOIN dbo.dim_time t ON fo.time_id = t.time_id
GROUP BY CUBE (t.dow_name, t.hour_range)
ORDER BY 
    GROUPING(t.dow_name) DESC, 
    total_orders DESC;
GO


-- ------------------------------------------------------------------------------
-- CÂU 3: WINDOW FUNCTION - RANKING TOP 3 SẢN PHẨM BÁN CHẠY NHẤT MỖI NGÀNH HÀNG
-- Nghiệp vụ: Dùng DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...) để tìm Top 3 
-- mặt hàng có sản lượng tiêu thụ cao nhất trong từng ngành hàng.
-- ------------------------------------------------------------------------------
WITH product_sales AS (
    SELECT 
        p.department_name,
        p.product_id,
        p.product_name,
        COUNT(*) AS total_sold,
        DENSE_RANK() OVER (
            PARTITION BY p.department_name 
            ORDER BY COUNT(*) DESC
        ) AS rank_in_dept
    FROM dbo.fact_order_items foi
    JOIN dbo.dim_products p ON foi.product_id = p.product_id
    GROUP BY p.department_name, p.product_id, p.product_name
)
SELECT 
    department_name,
    rank_in_dept,
    product_name,
    total_sold
FROM product_sales
WHERE rank_in_dept <= 3
ORDER BY department_name, rank_in_dept;
GO


-- ------------------------------------------------------------------------------
-- CÂU 4: PHÉP TOÁN SLICE & DICE (CẮT LÁT DỮ LIỆU CUỐI TUẦN VS NGÀY THƯỜNG)
-- Nghiệp vụ: So sánh hành vi mua sắm giữa 2 ngày Cuối tuần (Thứ 7, CN) và Ngày trong tuần.
-- ------------------------------------------------------------------------------
SELECT 
    CASE WHEN t.is_weekend = 1 THEN N'Cuối tuần (Thứ 7 & CN)' ELSE N'Ngày thường (T2 - T6)' END AS time_type,
    COUNT(DISTINCT fo.order_id) AS total_orders,
    COUNT(DISTINCT fo.user_id) AS active_users,
    ROUND(COUNT(DISTINCT fo.order_id) * 1.0 / NULLIF(COUNT(DISTINCT t.order_dow), 0), 2) AS avg_orders_per_day,
    ROUND(AVG(CAST(fo.total_items AS FLOAT)), 2) AS avg_basket_size,
    ROUND(AVG(fo.reorder_ratio) * 100, 2) AS avg_reorder_rate_pct
FROM dbo.fact_orders fo
JOIN dbo.dim_time t ON fo.time_id = t.time_id
GROUP BY t.is_weekend;
GO


-- ------------------------------------------------------------------------------
-- CÂU 5: PHÂN KHÚC KHÁCH HÀNG & ĐÓNG GÓP DOANH SỐ (MARKET SHARE CALCULATION)
-- Nghiệp vụ: Sử dụng SUM(...) OVER () để tính phần trăm đóng góp đơn hàng của từng 
-- nhóm khách hàng (VIP, Frequent, Regular, New) trên tổng thị trường.
-- ------------------------------------------------------------------------------
SELECT 
    user_segment,
    COUNT(*) AS total_customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct,
    SUM(total_orders) AS total_orders_placed,
    ROUND(SUM(total_orders) * 100.0 / SUM(SUM(total_orders)) OVER (), 2) AS order_share_pct,
    ROUND(AVG(avg_basket_size), 2) AS avg_basket_size,
    ROUND(AVG(avg_reorder_ratio) * 100, 2) AS avg_reorder_rate_pct
FROM dbo.dim_users
GROUP BY user_segment
ORDER BY total_orders_placed DESC;
GO


-- ------------------------------------------------------------------------------
-- CÂU 6: PHÂN TÍCH PHÂN BỐ KÍCH THƯỚC GIỎ HÀNG (BASKET SIZE BINNING)
-- Nghiệp vụ: Dùng kỹ thuật CASE WHEN để gom nhóm độ lớn giỏ hàng thành các khoảng 
-- (1-5 món, 6-10 món, 11-20 món, ...) và tính tần suất xuất hiện.
-- ------------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN total_items BETWEEN 1 AND 5 THEN N'1. Nhỏ (1 - 5 món)'
        WHEN total_items BETWEEN 6 AND 10 THEN N'2. Vừa (6 - 10 món)'
        WHEN total_items BETWEEN 11 AND 20 THEN N'3. Lớn (11 - 20 món)'
        WHEN total_items BETWEEN 21 AND 30 THEN N'4. Rất lớn (21 - 30 món)'
        ELSE N'5. Mua sỉ (> 30 món)'
    END AS basket_group,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct,
    ROUND(AVG(reorder_ratio) * 100, 2) AS avg_reorder_rate_pct
FROM dbo.fact_orders
WHERE total_items > 0
GROUP BY 
    CASE 
        WHEN total_items BETWEEN 1 AND 5 THEN N'1. Nhỏ (1 - 5 món)'
        WHEN total_items BETWEEN 6 AND 10 THEN N'2. Vừa (6 - 10 món)'
        WHEN total_items BETWEEN 11 AND 20 THEN N'3. Lớn (11 - 20 món)'
        WHEN total_items BETWEEN 21 AND 30 THEN N'4. Rất lớn (21 - 30 món)'
        ELSE N'5. Mua sỉ (> 30 món)'
    END
ORDER BY basket_group;
GO
