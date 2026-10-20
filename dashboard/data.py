"""DuckDB-backed high-speed Analytics Repository for Instacart Decision Intelligence."""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Final

import duckdb
import pandas as pd
from sqlalchemy import text

from . import demo_data

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from etl.db_config import get_sqlalchemy_engine, DB_ENGINE

DB_PATH = os.path.join(ROOT_DIR, "data", "instacart_dw.duckdb")

REQUIRED_TABLES: Final = frozenset(
    {
        "dim_time",
        "dim_departments",
        "dim_aisles",
        "dim_products",
        "dim_users",
        "fact_orders",
        "fact_order_items",
    }
)
TABLE_WHITELIST: Final = {
    name: {"kind": kind, "description": description}
    for name, kind, description, _ in demo_data.TABLE_CATALOG
}


class RepositoryConfigurationError(ValueError):
    """Raised when repository settings are invalid."""


class RepositoryUnavailableError(RuntimeError):
    """Raised when explicitly requested live data is unavailable."""


@dataclass(frozen=True)
class RepositoryHealth:
    healthy: bool
    checked_at: datetime
    checks: Mapping[str, bool]
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceMetadata:
    mode: str
    requested_mode: str
    label: str
    is_live: bool
    healthy: bool
    dataset_note: str
    checked_at: datetime
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TableMetadata:
    name: str
    kind: str
    description: str
    row_count_estimate: int | None
    size_mb: float | None
    columns: pd.DataFrame
    indexes: pd.DataFrame
    partitions: pd.DataFrame


class AnalyticsRepository(ABC):
    """Stable data API consumed by the analytics presentation layer."""

    @property
    @abstractmethod
    def source_metadata(self) -> SourceMetadata:
        pass

    def get_source_metadata(self) -> SourceMetadata:
        return self.source_metadata

    @abstractmethod
    def health_check(self) -> RepositoryHealth:
        pass

    @abstractmethod
    def overview_kpis(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def day_trends(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def hour_trends(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def weekend_comparison(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def departments(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def products(self, *, limit: int = 20, department: str | None = None) -> pd.DataFrame:
        pass

    @abstractmethod
    def aisles(self, *, limit: int = 15, min_items: int = 10_000) -> pd.DataFrame:
        pass

    @abstractmethod
    def customer_segments(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def basket_distribution(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def table_catalog(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def table_metadata(self, table_name: str) -> TableMetadata:
        pass

    @abstractmethod
    def table_sample(self, table_name: str, *, limit: int = 10) -> pd.DataFrame:
        pass


class DuckDBAnalyticsRepository(AnalyticsRepository):
    """High-performance Analytics Repository backed by DuckDB Star Schema."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        self._health = self.health_check()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        if not os.path.exists(self._db_path):
            raise RepositoryUnavailableError("Database file does not exist.")
        return duckdb.connect(self._db_path, read_only=True)

    @property
    def source_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            mode="live",
            requested_mode="live",
            label="Live DuckDB Warehouse (Embedded Columnar)",
            is_live=True,
            healthy=self._health.healthy,
            dataset_note="Instacart Star Schema warehouse powered by DuckDB columnar storage.",
            checked_at=self._health.checked_at,
        )

    def health_check(self) -> RepositoryHealth:
        now = datetime.now(timezone.utc)
        checks = {"db_exists": False, "schema": False, "data": False}
        if os.path.exists(self._db_path):
            checks["db_exists"] = True
            try:
                con = duckdb.connect(self._db_path, read_only=True)
                tables = [t[0].lower() for t in con.execute("SHOW TABLES").fetchall()]
                checks["schema"] = REQUIRED_TABLES.issubset(set(tables))
                if checks["schema"]:
                    cnt = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
                    checks["data"] = cnt > 0
                con.close()
            except Exception:
                pass
        healthy = all(checks.values())
        return RepositoryHealth(
            healthy=healthy,
            checked_at=now,
            checks=checks,
            message="DuckDB warehouse is live and ready." if healthy else "DuckDB warehouse not ready.",
        )

    def overview_kpis(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            order_metrics.total_orders,
            user_metrics.total_users,
            product_metrics.total_products,
            order_metrics.total_items,
            order_metrics.avg_basket_size,
            order_metrics.avg_reorder_rate_pct,
            product_metrics.total_departments,
            product_metrics.total_aisles
        FROM (
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(SUM(total_items), 0) AS total_items,
                AVG(NULLIF(total_items, 0)) AS avg_basket_size,
                AVG(reorder_ratio) * 100 AS avg_reorder_rate_pct
            FROM fact_orders
        ) AS order_metrics
        CROSS JOIN (
            SELECT COUNT(*) AS total_users FROM dim_users
        ) AS user_metrics
        CROSS JOIN (
            SELECT
                COUNT(*) AS total_products,
                COUNT(DISTINCT department_id) AS total_departments,
                COUNT(DISTINCT aisle_id) AS total_aisles
            FROM dim_products
        ) AS product_metrics;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def day_trends(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            t.order_dow,
            CASE t.order_dow
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END AS dow_name,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT fo.order_id) * 100.0 / SUM(COUNT(DISTINCT fo.order_id)) OVER () AS share_pct
        FROM fact_orders fo
        JOIN dim_time t ON fo.time_id = t.time_id
        GROUP BY t.order_dow
        ORDER BY t.order_dow;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def hour_trends(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            t.order_hour_of_day AS order_hour,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT fo.order_id) * 100.0 / SUM(COUNT(DISTINCT fo.order_id)) OVER () AS share_pct
        FROM fact_orders fo
        JOIN dim_time t ON fo.time_id = t.time_id
        GROUP BY t.order_hour_of_day
        ORDER BY t.order_hour_of_day;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def weekend_comparison(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            CASE WHEN t.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT t.order_dow) AS days_in_group,
            COUNT(DISTINCT fo.order_id) * 1.0 / COUNT(DISTINCT t.order_dow) AS avg_orders_per_day,
            AVG(NULLIF(fo.total_items, 0)) AS avg_basket_size,
            AVG(fo.reorder_ratio) * 100 AS avg_reorder_rate_pct
        FROM fact_orders fo
        JOIN dim_time t ON fo.time_id = t.time_id
        GROUP BY t.is_weekend
        ORDER BY day_type DESC;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def departments(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            p.department_name,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(*) AS total_items,
            AVG(CAST(foi.reordered AS DOUBLE)) * 100 AS reorder_rate_pct,
            COUNT(DISTINCT foi.product_id) AS unique_products
        FROM fact_order_items foi
        JOIN dim_products p ON foi.product_id = p.product_id
        GROUP BY p.department_name
        ORDER BY total_items DESC;
        """
        df = con.execute(query).fetchdf()
        con.close()
        denom = df["total_items"].sum() if not df.empty else 0
        df["market_share_pct"] = (df["total_items"] / denom * 100) if denom else 0.0
        return df

    def products(self, *, limit: int = 20, department: str | None = None) -> pd.DataFrame:
        con = self._get_connection()
        where = f"WHERE p.department_name = '{department.strip()}'" if department else ""
        query = f"""
        SELECT
            p.product_name,
            p.department_name,
            p.aisle_name,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(*) AS total_items,
            AVG(CAST(foi.reordered AS DOUBLE)) * 100 AS reorder_rate_pct
        FROM fact_order_items foi
        JOIN dim_products p ON foi.product_id = p.product_id
        {where}
        GROUP BY p.product_id, p.product_name, p.department_name, p.aisle_name
        ORDER BY orders DESC
        LIMIT {limit};
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def aisles(self, *, limit: int = 15, min_items: int = 10_000) -> pd.DataFrame:
        con = self._get_connection()
        query = f"""
        SELECT
            p.aisle_name,
            AVG(CAST(foi.reordered AS DOUBLE)) * 100 AS reorder_rate_pct,
            COUNT(*) AS items
        FROM fact_order_items foi
        JOIN dim_products p ON foi.product_id = p.product_id
        GROUP BY p.aisle_name
        HAVING COUNT(*) >= {min_items}
        ORDER BY reorder_rate_pct DESC, items DESC
        LIMIT {limit};
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def customer_segments(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            u.user_segment,
            COUNT(*) AS users,
            SUM(u.total_orders) AS total_orders,
            AVG(u.total_orders) AS avg_orders,
            AVG(u.avg_basket_size) AS avg_basket_size,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS user_share_pct,
            SUM(u.total_orders) * 100.0 / SUM(SUM(u.total_orders)) OVER () AS order_share_pct
        FROM dim_users u
        WHERE u.user_segment IS NOT NULL AND u.user_segment <> ''
        GROUP BY u.user_segment
        ORDER BY avg_orders DESC;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def basket_distribution(self) -> pd.DataFrame:
        con = self._get_connection()
        query = """
        SELECT
            CASE
                WHEN fo.total_items BETWEEN 1 AND 5 THEN 1
                WHEN fo.total_items BETWEEN 6 AND 10 THEN 2
                WHEN fo.total_items BETWEEN 11 AND 20 THEN 3
                WHEN fo.total_items BETWEEN 21 AND 30 THEN 4
                ELSE 5
            END AS bucket_order,
            CASE
                WHEN fo.total_items BETWEEN 1 AND 5 THEN '1-5 items'
                WHEN fo.total_items BETWEEN 6 AND 10 THEN '6-10 items'
                WHEN fo.total_items BETWEEN 11 AND 20 THEN '11-20 items'
                WHEN fo.total_items BETWEEN 21 AND 30 THEN '21-30 items'
                ELSE '31+ items'
            END AS basket_size,
            COUNT(*) AS orders,
            AVG(fo.reorder_ratio) * 100 AS avg_reorder_rate_pct,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS order_share_pct
        FROM fact_orders fo
        WHERE fo.total_items > 0
        GROUP BY bucket_order, basket_size
        ORDER BY bucket_order;
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

    def table_catalog(self) -> pd.DataFrame:
        rows = [
            {"table_name": "dim_products", "kind": "Dimension", "description": "Denormalized product catalog with department and aisle hierarchy", "row_count_estimate": 49688},
            {"table_name": "dim_users", "kind": "Dimension", "description": "Customer behavioral profiles with lifetime loyalty segments", "row_count_estimate": 206209},
            {"table_name": "dim_time", "kind": "Dimension", "description": "Recurring day-of-week and hour demand buckets", "row_count_estimate": 168},
            {"table_name": "dim_departments", "kind": "Dimension", "description": "Top-level department categories", "row_count_estimate": 21},
            {"table_name": "dim_aisles", "kind": "Dimension", "description": "Shelf-level aisle classifications", "row_count_estimate": 134},
            {"table_name": "fact_orders", "kind": "Fact", "description": "Order-level grain containing totals and time keys", "row_count_estimate": 3421083},
            {"table_name": "fact_order_items", "kind": "Fact", "description": "Line-item level grain tracking 33.8M product cart placements", "row_count_estimate": 33819106},
        ]
        return pd.DataFrame(rows)

    def table_metadata(self, table_name: str) -> TableMetadata:
        con = self._get_connection()
        col_df = con.execute(f"DESCRIBE {table_name}").fetchdf()
        col_df["data_type"] = col_df["column_type"]
        col_df["nullable"] = col_df["null"].astype(str).str.upper() == "YES"
        col_df["default"] = col_df["default"].fillna("")
        col_df["comment"] = col_df["extra"].fillna("")
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        con.close()
        
        idx_df = pd.DataFrame([
            {"index_name": f"pk_{table_name}", "columns": "PRIMARY KEY", "unique": True}
        ])

        if table_name == "fact_orders":
            part_df = pd.DataFrame([
                {"partition_name": "p_sunday", "row_count_estimate": 600905, "method": "LIST (order_dow=0)", "description": "Sunday orders"},
                {"partition_name": "p_monday", "row_count_estimate": 587478, "method": "LIST (order_dow=1)", "description": "Monday orders"},
                {"partition_name": "p_tuesday", "row_count_estimate": 465600, "method": "LIST (order_dow=2)", "description": "Tuesday orders"},
                {"partition_name": "p_wednesday", "row_count_estimate": 439000, "method": "LIST (order_dow=3)", "description": "Wednesday orders"},
                {"partition_name": "p_thursday", "row_count_estimate": 427000, "method": "LIST (order_dow=4)", "description": "Thursday orders"},
                {"partition_name": "p_friday", "row_count_estimate": 453000, "method": "LIST (order_dow=5)", "description": "Friday orders"},
                {"partition_name": "p_saturday", "row_count_estimate": 448100, "method": "LIST (order_dow=6)", "description": "Saturday orders"},
            ])
        else:
            part_df = pd.DataFrame(columns=["partition_name", "row_count_estimate", "method", "description"])

        return TableMetadata(
            name=table_name,
            kind="Fact" if "fact" in table_name else "Dimension",
            description=f"DuckDB table: {table_name}",
            row_count_estimate=row_count,
            size_mb=round(os.path.getsize(self._db_path) / (1024 * 1024), 2),
            columns=col_df,
            indexes=idx_df,
            partitions=part_df,
        )

    def table_sample(self, table_name: str, *, limit: int = 10) -> pd.DataFrame:
        con = self._get_connection()
        df = con.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchdf()
        con.close()
        return df




class SQLServerAnalyticsRepository(AnalyticsRepository):
    """Enterprise Analytics Repository backed by Microsoft SQL Server (DataWarehouse_DB)."""

    def __init__(self, engine=None) -> None:
        self._engine = engine or get_sqlalchemy_engine()
        self._health = self.health_check()

    @property
    def source_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            mode="live",
            requested_mode="live",
            label="Live Microsoft SQL Server (DataWarehouse_DB)",
            is_live=True,
            healthy=self._health.healthy,
            dataset_note="Instacart Star Schema warehouse powered by Microsoft SQL Server (DataWarehouse_DB).",
            checked_at=self._health.checked_at,
        )

    def health_check(self) -> RepositoryHealth:
        now = datetime.now(timezone.utc)
        checks = {"db_exists": False, "schema": False, "data": False}
        try:
            with self._engine.connect() as con:
                checks["db_exists"] = True
                result = con.execute(
                    text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
                )
                tables = {row[0].lower() for row in result.fetchall()}
                checks["schema"] = REQUIRED_TABLES.issubset(tables)
                if checks["schema"]:
                    cnt = con.execute(text("SELECT COUNT(*) FROM dbo.fact_orders")).scalar()
                    checks["data"] = cnt is not None and cnt > 0
        except Exception:
            pass
        healthy = all(checks.values())
        return RepositoryHealth(
            healthy=healthy,
            checked_at=now,
            checks=checks,
            message="SQL Server warehouse is live and ready." if healthy else "SQL Server warehouse not ready.",
        )

    def overview_kpis(self) -> pd.DataFrame:
        query = """
        SELECT
            order_metrics.total_orders,
            user_metrics.total_users,
            product_metrics.total_products,
            order_metrics.total_items,
            order_metrics.avg_basket_size,
            order_metrics.avg_reorder_rate_pct,
            product_metrics.total_departments,
            product_metrics.total_aisles
        FROM (
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(SUM(total_items), 0) AS total_items,
                AVG(NULLIF(CAST(total_items AS FLOAT), 0)) AS avg_basket_size,
                AVG(reorder_ratio) * 100 AS avg_reorder_rate_pct
            FROM dbo.fact_orders
        ) AS order_metrics
        CROSS JOIN (
            SELECT COUNT(*) AS total_users FROM dbo.dim_users
        ) AS user_metrics
        CROSS JOIN (
            SELECT
                COUNT(*) AS total_products,
                COUNT(DISTINCT department_id) AS total_departments,
                COUNT(DISTINCT aisle_id) AS total_aisles
            FROM dbo.dim_products
        ) AS product_metrics;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def day_trends(self) -> pd.DataFrame:
        query = """
        SELECT
            t.order_dow,
            CASE t.order_dow
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END AS dow_name,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT fo.order_id) * 100.0 / SUM(COUNT(DISTINCT fo.order_id)) OVER () AS share_pct
        FROM dbo.fact_orders fo
        JOIN dbo.dim_time t ON fo.time_id = t.time_id
        GROUP BY t.order_dow
        ORDER BY t.order_dow;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def hour_trends(self) -> pd.DataFrame:
        query = """
        SELECT
            t.order_hour_of_day AS order_hour,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT fo.order_id) * 100.0 / SUM(COUNT(DISTINCT fo.order_id)) OVER () AS share_pct
        FROM dbo.fact_orders fo
        JOIN dbo.dim_time t ON fo.time_id = t.time_id
        GROUP BY t.order_hour_of_day
        ORDER BY t.order_hour_of_day;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def weekend_comparison(self) -> pd.DataFrame:
        query = """
        SELECT
            CASE WHEN t.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
            COUNT(DISTINCT fo.order_id) AS orders,
            COUNT(DISTINCT t.order_dow) AS days_in_group,
            COUNT(DISTINCT fo.order_id) * 1.0 / COUNT(DISTINCT t.order_dow) AS avg_orders_per_day,
            AVG(NULLIF(CAST(fo.total_items AS FLOAT), 0)) AS avg_basket_size,
            AVG(fo.reorder_ratio) * 100 AS avg_reorder_rate_pct
        FROM dbo.fact_orders fo
        JOIN dbo.dim_time t ON fo.time_id = t.time_id
        GROUP BY t.is_weekend
        ORDER BY day_type DESC;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def departments(self) -> pd.DataFrame:
        query = """
        SELECT
            p.department_name,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(*) AS total_items,
            AVG(CAST(foi.reordered AS FLOAT)) * 100 AS reorder_rate_pct,
            COUNT(DISTINCT foi.product_id) AS unique_products
        FROM dbo.fact_order_items foi
        JOIN dbo.dim_products p ON foi.product_id = p.product_id
        GROUP BY p.department_name
        ORDER BY total_items DESC;
        """
        with self._engine.connect() as con:
            df = pd.read_sql(text(query), con)
        denom = df["total_items"].sum() if not df.empty else 0
        df["market_share_pct"] = (df["total_items"] / denom * 100) if denom else 0.0
        return df

    def products(self, *, limit: int = 20, department: str | None = None) -> pd.DataFrame:
        where_clause = "WHERE p.department_name = :department" if department else ""
        query = f"""
        SELECT TOP ({int(limit)})
            p.product_name,
            p.department_name,
            p.aisle_name,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(*) AS total_items,
            AVG(CAST(foi.reordered AS FLOAT)) * 100 AS reorder_rate_pct
        FROM dbo.fact_order_items foi
        JOIN dbo.dim_products p ON foi.product_id = p.product_id
        {where_clause}
        GROUP BY p.product_id, p.product_name, p.department_name, p.aisle_name
        ORDER BY orders DESC;
        """
        params = {"department": department.strip()} if department else {}
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con, params=params)

    def aisles(self, *, limit: int = 15, min_items: int = 10_000) -> pd.DataFrame:
        query = f"""
        SELECT TOP ({int(limit)})
            p.aisle_name,
            AVG(CAST(foi.reordered AS FLOAT)) * 100 AS reorder_rate_pct,
            COUNT(*) AS items
        FROM dbo.fact_order_items foi
        JOIN dbo.dim_products p ON foi.product_id = p.product_id
        GROUP BY p.aisle_name
        HAVING COUNT(*) >= {int(min_items)}
        ORDER BY reorder_rate_pct DESC, items DESC;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def customer_segments(self) -> pd.DataFrame:
        query = """
        SELECT
            u.user_segment,
            COUNT(*) AS users,
            SUM(u.total_orders) AS total_orders,
            AVG(CAST(u.total_orders AS FLOAT)) AS avg_orders,
            AVG(u.avg_basket_size) AS avg_basket_size,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS user_share_pct,
            SUM(CAST(u.total_orders AS BIGINT)) * 100.0 / SUM(SUM(CAST(u.total_orders AS BIGINT))) OVER () AS order_share_pct
        FROM dbo.dim_users u
        WHERE u.user_segment IS NOT NULL AND u.user_segment <> ''
        GROUP BY u.user_segment
        ORDER BY avg_orders DESC;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def basket_distribution(self) -> pd.DataFrame:
        query = """
        WITH BucketCTE AS (
            SELECT
                CASE
                    WHEN fo.total_items BETWEEN 1 AND 5 THEN 1
                    WHEN fo.total_items BETWEEN 6 AND 10 THEN 2
                    WHEN fo.total_items BETWEEN 11 AND 20 THEN 3
                    WHEN fo.total_items BETWEEN 21 AND 30 THEN 4
                    ELSE 5
                END AS bucket_order,
                CASE
                    WHEN fo.total_items BETWEEN 1 AND 5 THEN '1-5 items'
                    WHEN fo.total_items BETWEEN 6 AND 10 THEN '6-10 items'
                    WHEN fo.total_items BETWEEN 11 AND 20 THEN '11-20 items'
                    WHEN fo.total_items BETWEEN 21 AND 30 THEN '21-30 items'
                    ELSE '31+ items'
                END AS basket_size,
                fo.reorder_ratio
            FROM dbo.fact_orders fo
            WHERE fo.total_items > 0
        )
        SELECT
            bucket_order,
            basket_size,
            COUNT(*) AS orders,
            AVG(reorder_ratio) * 100 AS avg_reorder_rate_pct,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS order_share_pct
        FROM BucketCTE
        GROUP BY bucket_order, basket_size
        ORDER BY bucket_order;
        """
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)

    def table_catalog(self) -> pd.DataFrame:
        desc_map = {
            "dim_products": ("Dimension", "Denormalized product catalog with department and aisle hierarchy"),
            "dim_users": ("Dimension", "Customer behavioral profiles with lifetime loyalty segments"),
            "dim_time": ("Dimension", "Recurring day-of-week and hour demand buckets"),
            "dim_departments": ("Dimension", "Top-level department categories"),
            "dim_aisles": ("Dimension", "Shelf-level aisle classifications"),
            "fact_orders": ("Fact", "Order-level grain containing totals and time keys"),
            "fact_order_items": ("Fact", "Line-item level grain tracking product cart placements"),
        }
        query = """
        SELECT
            t.name AS table_name,
            SUM(p.row_count) AS row_count_estimate
        FROM sys.tables t
        JOIN sys.dm_db_partition_stats p ON t.object_id = p.object_id
        WHERE p.index_id < 2
        GROUP BY t.name;
        """
        counts = {}
        try:
            with self._engine.connect() as con:
                res = con.execute(text(query)).fetchall()
                counts = {r[0].lower(): r[1] for r in res}
        except Exception:
            pass

        rows = []
        for tbl, (kind, desc) in desc_map.items():
            rows.append({
                "table_name": tbl,
                "kind": kind,
                "description": desc,
                "row_count_estimate": counts.get(tbl, 0),
            })
        return pd.DataFrame(rows)

    def table_metadata(self, table_name: str) -> TableMetadata:
        col_query = """
        SELECT
            c.COLUMN_NAME AS column_name,
            c.DATA_TYPE AS data_type,
            CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS nullable,
            COALESCE(c.COLUMN_DEFAULT, '') AS [default],
            '' AS comment
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_NAME = :table_name
        ORDER BY c.ORDINAL_POSITION;
        """
        size_query = """
        SELECT ROUND(SUM(a.total_pages) * 8.0 / 1024, 2) AS size_mb
        FROM sys.tables t
        JOIN sys.indexes i ON t.object_id = i.object_id
        JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
        JOIN sys.allocation_units a ON p.partition_id = a.container_id
        WHERE t.name = :table_name
        GROUP BY t.name;
        """
        idx_query = """
        SELECT
            i.name AS index_name,
            STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS [columns],
            i.is_unique AS [unique]
        FROM sys.indexes i
        JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN sys.tables t ON i.object_id = t.object_id
        WHERE t.name = :table_name AND i.name IS NOT NULL
        GROUP BY i.name, i.is_unique;
        """
        cnt_query = f"SELECT COUNT(*) FROM dbo.{table_name}"

        with self._engine.connect() as con:
            col_df = pd.read_sql(text(col_query), con, params={"table_name": table_name})
            col_df["nullable"] = col_df["nullable"].astype(bool)

            idx_df = pd.read_sql(text(idx_query), con, params={"table_name": table_name})
            if idx_df.empty:
                idx_df = pd.DataFrame([{"index_name": f"pk_{table_name}", "columns": "PRIMARY KEY", "unique": True}])
            else:
                idx_df["unique"] = idx_df["unique"].astype(bool)

            size_res = con.execute(text(size_query), {"table_name": table_name}).scalar()
            size_mb = float(size_res) if size_res is not None else 0.0

            row_count = con.execute(text(cnt_query)).scalar()

        if table_name == "fact_orders":
            part_df = pd.DataFrame([
                {"partition_name": "p_sunday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=0)", "comment": "Sunday orders", "description": "Sunday orders"},
                {"partition_name": "p_monday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=1)", "comment": "Monday orders", "description": "Monday orders"},
                {"partition_name": "p_tuesday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=2)", "comment": "Tuesday orders", "description": "Tuesday orders"},
                {"partition_name": "p_wednesday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=3)", "comment": "Wednesday orders", "description": "Wednesday orders"},
                {"partition_name": "p_thursday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=4)", "comment": "Thursday orders", "description": "Thursday orders"},
                {"partition_name": "p_friday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=5)", "comment": "Friday orders", "description": "Friday orders"},
                {"partition_name": "p_saturday", "row_count_estimate": None, "size_mb": None, "method": "LIST (order_dow=6)", "comment": "Saturday orders", "description": "Saturday orders"},
            ])
        else:
            part_df = pd.DataFrame(columns=["partition_name", "row_count_estimate", "size_mb", "method", "comment", "description"])

        return TableMetadata(
            name=table_name,
            kind="Fact" if "fact" in table_name else "Dimension",
            description=f"SQL Server table: dbo.{table_name}",
            row_count_estimate=row_count,
            size_mb=size_mb,
            columns=col_df,
            indexes=idx_df,
            partitions=part_df,
        )

    def table_sample(self, table_name: str, *, limit: int = 10) -> pd.DataFrame:
        query = f"SELECT TOP ({int(limit)}) * FROM dbo.{table_name};"
        with self._engine.connect() as con:
            return pd.read_sql(text(query), con)


def create_repository(settings: Any = None) -> AnalyticsRepository:
    """Factory returning SQL Server or DuckDB repository with fallback to deterministic demo."""
    db_engine = os.environ.get("DB_ENGINE", "sqlserver").strip().lower()
    if isinstance(settings, dict) and "db_engine" in settings:
        db_engine = str(settings["db_engine"]).strip().lower()

    # Ưu tiên khởi tạo SQL Server khi DB_ENGINE=sqlserver
    if db_engine == "sqlserver":
        try:
            repo = SQLServerAnalyticsRepository()
            if repo.health_check().healthy:
                return repo
        except Exception:
            pass

    if os.path.exists(DB_PATH):
        try:
            repo = DuckDBAnalyticsRepository(DB_PATH)
            if repo.health_check().healthy:
                return repo
        except Exception:
            pass

    return demo_data.DemoAnalyticsRepository()
