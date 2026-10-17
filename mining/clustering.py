"""
Module Phân cụm Khách hàng (Customer Clustering) - Baseline Stub cho Phase 2 (Cuối Kỳ).
"""
import pandas as pd
import numpy as np

class CustomerClustering:
    def __init__(self, n_clusters=4, random_state=42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.is_fitted = False

    def fit_kmeans(self, user_features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Khung hàm fit_kmeans giả lập (Stub method) cho Báo cáo Giữa kỳ.
        Sẽ phát triển thuật toán K-Means thực tế ở Báo cáo Cuối kỳ (Phase 2).
        """
        if user_features_df.empty:
            return pd.DataFrame()
            
        res_df = user_features_df.copy()
        # Stub cluster assignment
        res_df['cluster'] = np.random.randint(0, self.n_clusters, size=len(res_df))
        res_df['segment'] = res_df['cluster'].map({
            0: 'VIP / Champion',
            1: 'Frequent',
            2: 'Regular',
            3: 'New / Occasional'
        })
        self.is_fitted = True
        return res_df

    def get_cluster_summary(self, df_clustered: pd.DataFrame) -> pd.DataFrame:
        """Trả về tóm tắt thông số các phân cụm"""
        if df_clustered.empty or 'cluster' not in df_clustered.columns:
            return pd.DataFrame()
        return df_clustered.groupby('cluster').mean(numeric_only=True)
