import glob
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from azure.storage.blob import BlobClient
from dotenv import find_dotenv, load_dotenv

from shipment_qna_bot.logging.logger import logger
from shipment_qna_bot.tools.analytics_metadata import ANALYTICS_METADATA
from shipment_qna_bot.tools.date_tools import get_today_date
from shipment_qna_bot.utils.runtime import is_test_mode

load_dotenv(find_dotenv(), override=True)


class BlobAnalyticsManager:
    """
    Manages the lifecycle of the local Master Cache for analytics.
    Downloads the full dataset from Azure Blob Storage once per day
    and provides filtered DataFrames to the application.
    """

    # In-memory singletons to prevent redundant I/O and OOM spikes
    _MASTER_DF_CACHE: Optional[pd.DataFrame] = None
    _FILTERED_CACHE: Dict[str, pd.DataFrame] = (
        {}
    )  # Map of frozenset(consignee_codes) -> DataFrame
    _LAST_LOAD_DATE: Optional[str] = None

    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = cache_dir
        self._test_mode = is_test_mode()

        # Ensure cache directory exists
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_UPLD")
        self.blob_name = os.getenv("AZURE_STORAGE_BLOB_NAME", "master_ds.parquet")

    def _get_today_str(self) -> str:
        return get_today_date()

    def _get_cache_path(self, date_str: str) -> str:
        suffix = ".test" if self._test_mode else ""
        return os.path.join(self.cache_dir, f"master_{date_str}{suffix}.parquet")

    def _cleanup_old_cache(self, current_date_str: str):
        """
        Removes any master_*.parquet files that do not match the current date and mode.
        """
        target_fname = os.path.basename(self._get_cache_path(current_date_str))
        pattern = os.path.join(self.cache_dir, "master_*.parquet")
        for fpath in glob.glob(pattern):
            fname = os.path.basename(fpath)
            if fname != target_fname:
                try:
                    os.remove(fpath)
                    logger.info(f"Cleaned up old cache file: {fpath}")
                except OSError as e:
                    logger.warning(f"Failed to remove old cache file {fpath}: {e}")

    def download_master_data(self) -> str:
        """
        Ensures the master dataset for today is present locally.
        Returns the absolute path to the local parquet file.
        """
        today = self._get_today_str()
        target_path = self._get_cache_path(today)

        # 1. Cleanup old cache
        self._cleanup_old_cache(today)

        # 2. Check if exists
        if os.path.exists(target_path):
            return target_path

        if self._test_mode:
            logger.info("TEST MODE: Creating dummy master parquet.")
            # Create a more robust mock DF for tests
            data = {
                "consignee_codes": [["TEST"], ["OTHER"]],
                "shipment_status": ["DELIVERED", "IN_OCEAN"],
                "container_number": ["CONT123", "CONT456"],
            }
            # Ensure all metadata columns are present
            from shipment_qna_bot.tools.analytics_metadata import ANALYTICS_METADATA

            for col in ANALYTICS_METADATA:
                if col not in data:
                    data[col] = [None, None]

            df = pd.DataFrame(data)
            df.to_parquet(target_path)
            return target_path

        # 3. Download
        if not self.conn_str or not self.container_name:
            raise RuntimeError(
                "Missing Azure Blob env vars (CONNECTION_STRING or CONTAINER_NAME)."
            )

        logger.info(f"Downloading {self.blob_name} to {target_path}...")
        try:
            blob_client = BlobClient.from_connection_string(
                conn_str=self.conn_str,
                container_name=self.container_name,
                blob_name=self.blob_name,
            )

            with open(target_path, "wb") as my_blob:
                blob_data = blob_client.download_blob()
                blob_data.readinto(my_blob)

            logger.info("Download complete.")
            return target_path
        except Exception as e:
            if os.path.exists(target_path):
                os.remove(target_path)
            raise RuntimeError(f"Blob download failed: {e}")

    def load_filtered_data(self, consignee_codes: List[str]) -> pd.DataFrame:
        """
        Loads the master dataset and returns a DataFrame filtered for the given consignee_ids.
        Uses in-memory caching to avoid redundant I/O and CPU-heavy filtering.
        """
        if not consignee_codes:
            return pd.DataFrame()

        today = self._get_today_str()
        cache_key = "|".join(sorted(consignee_codes))

        # 1. Check Consignee-Specific Cache
        if (
            BlobAnalyticsManager._LAST_LOAD_DATE == today
            and cache_key in BlobAnalyticsManager._FILTERED_CACHE
        ):
            logger.info("Consignee cache hit for codes: %s", consignee_codes[:2])
            return BlobAnalyticsManager._FILTERED_CACHE[cache_key]

        # 2. Check Master Cache
        if (
            BlobAnalyticsManager._LAST_LOAD_DATE != today
            or BlobAnalyticsManager._MASTER_DF_CACHE is None
        ):
            # Cache miss or date rollover - reload everything
            logger.info("Master cache miss or date rollover. Reloading master dataset.")
            file_path = self.download_master_data()

            # Column Pruning: Load only columns we actually use (metadata + technical keys)
            # This drastically reduces memory footprint.
            requested_cols = list(ANALYTICS_METADATA.keys()) + ["consignee_codes"]

            try:
                # 1. Identify which requested columns actually exist in the file
                import pyarrow.parquet as pq

                schema = pq.read_schema(file_path)
                available_cols = set(schema.names)
                actual_load_cols = [c for c in requested_cols if c in available_cols]

                logger.info(
                    "Pruning: Requesting %d/%d available columns.",
                    len(actual_load_cols),
                    len(available_cols),
                )

                # 2. Optimized read with valid columns only
                full_df = pd.read_parquet(file_path, columns=actual_load_cols)

                # Global Type Casting (Perform Once per Day for existing columns)
                for col, meta in ANALYTICS_METADATA.items():
                    if col in full_df.columns:
                        col_type = meta.get("type")
                        if col_type == "numeric":
                            full_df[col] = pd.to_numeric(full_df[col], errors="coerce")
                        elif col_type == "datetime":
                            full_df[col] = pd.to_datetime(full_df[col], errors="coerce")

                BlobAnalyticsManager._MASTER_DF_CACHE = full_df
                BlobAnalyticsManager._LAST_LOAD_DATE = today
                BlobAnalyticsManager._FILTERED_CACHE = (
                    {}
                )  # Invalidate all filtered slices
            except Exception as e:
                logger.error(f"Failed to read/process master parquet: {e}")
                raise e

        # 3. Filter from Master Cache
        df = BlobAnalyticsManager._MASTER_DF_CACHE
        target_col = "consignee_codes"

        try:
            # Efficient Filtering Logic
            exploded = df.explode(target_col)
            mask = exploded[target_col].isin(consignee_codes)
            valid_indices = exploded[mask].index.unique()

            # Return a copy to ensure node operations don't corrupt the master cache
            filtered_df = df.loc[valid_indices].copy()

            # Update filter cache
            BlobAnalyticsManager._FILTERED_CACHE[cache_key] = filtered_df

            logger.info(
                f"Filtered {len(filtered_df)} rows from master cache for codes {consignee_codes[:3]}..."
            )
            return filtered_df

        except Exception as e:
            logger.error(f"Filtering operation failed: {e}")
            raise e
