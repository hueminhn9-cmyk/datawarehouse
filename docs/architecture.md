# Instacart Data Warehouse & Decision Intelligence Architecture

## 1. System Overview
The **Instacart Data Warehouse** is built to process market-basket dataset into a MariaDB/MySQL analytical data warehouse powering an interactive Streamlit Multi-Page cockpit.

```
+------------------+       +-------------------+       +---------------------+
| 6 Source CSVs    | ----> | ETL Pipeline      | ----> | MariaDB / MySQL     |
| (Instacart Data) |       | (Python Chunking) |       | (Star Schema DW)    |
+------------------+       +-------------------+       +---------------------+
                                                                  |
                                                                  v
                                                       +---------------------+
                                                       | Streamlit Dashboard |
                                                       | (Multi-Page UI)     |
                                                       +---------------------+
```

## 2. Star Schema Design
The warehouse consists of 5 Dimension tables and 2 Fact tables:

### Dimensions
- `dim_departments`: Department catalog
- `dim_aisles`: Aisle catalog
- `dim_products`: Product catalog
- `dim_users`: User catalog
- `dim_time`: Shopping time dimension

### Facts
- `fact_orders`: Order level granularity
- `fact_order_items`: Order detail product item level granularity

## 3. Two-Phase Roadmap
- **Phase 1 (Midterm Exam):** Containerization, Star Schema SQL DDL, Chunked ETL, Streamlit Core Pages (`Overview`, `Products`, `Data Tables`).
- **Phase 2 (Final Exam):** K-Means Customer Clustering, FP-Growth Association Rules, Recommendation Engine.
