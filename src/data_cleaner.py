from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"


class DataCleaner:
    """Clean, standardize, classify, and export retail transactions."""

    def __init__(self, dataframe: pd.DataFrame) -> None:
        self.raw_df = dataframe

    def clean_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return the cleaned transactions and a cleaning summary."""

        df = self.raw_df.copy()
        raw_row_count = len(df)

        # Standardize column names for Python, SQL, and Power BI.
        df = df.rename(
            columns={
                "Invoice": "invoice_id",
                "StockCode": "stock_code",
                "Description": "description",
                "Quantity": "quantity",
                "InvoiceDate": "invoice_date",
                "Price": "unit_price",
                "Customer ID": "customer_id",
                "Country": "country",
            }
        )

        # Remove only exact duplicate records.
        duplicate_count = int(df.duplicated().sum())
        df = df.drop_duplicates().copy()

        # Standardize string fields.
        string_columns = [
            "invoice_id",
            "stock_code",
            "description",
            "country",
            "source_sheet",
        ]

        for column in string_columns:
            df[column] = df[column].astype("string").str.strip()

        df["description"] = df["description"].str.replace(
            r"\s+",
            " ",
            regex=True,
        )

        df["country"] = df["country"].str.replace(
            r"\s+",
            " ",
            regex=True,
        )

        # Standardize numeric and date fields.
        df["quantity"] = pd.to_numeric(
            df["quantity"],
            errors="coerce",
        )

        df["unit_price"] = pd.to_numeric(
            df["unit_price"],
            errors="coerce",
        )

        df["invoice_date"] = pd.to_datetime(
            df["invoice_date"],
            errors="coerce",
        )

        # Customer IDs are identifiers, not measurements.
        df["customer_id"] = (
            pd.to_numeric(df["customer_id"], errors="coerce")
            .astype("Int64")
            .astype("string")
        )

        # Transaction classification flags.
        df["is_cancelled"] = (
            df["invoice_id"]
            .str.upper()
            .str.startswith("C", na=False)
        )

        df["is_return"] = df["quantity"] < 0
        df["is_zero_price"] = df["unit_price"] == 0
        df["is_invalid_price"] = df["unit_price"] < 0
        df["has_customer_id"] = df["customer_id"].notna()

        df["is_valid_sale"] = (
            (df["quantity"] > 0)
            & (df["unit_price"] > 0)
            & (~df["is_cancelled"])
            & (df["invoice_date"].notna())
        )

        # Financial features.
        df["net_line_value"] = (
            df["quantity"] * df["unit_price"]
        ).round(2)

        df["sales_revenue"] = np.where(
            df["is_valid_sale"],
            df["net_line_value"],
            0.0,
        ).round(2)

        df["return_value"] = np.where(
            df["is_return"] | df["is_cancelled"],
            df["quantity"].abs()
            * df["unit_price"].clip(lower=0),
            0.0,
        ).round(2)

        # Calendar features for SQL and Power BI.
        df["invoice_year"] = df["invoice_date"].dt.year
        df["invoice_quarter"] = (
            "Q"
            + df["invoice_date"].dt.quarter.astype("Int64").astype("string")
        )
        df["invoice_month_number"] = df["invoice_date"].dt.month
        df["invoice_month_name"] = df["invoice_date"].dt.month_name()
        df["year_month"] = (
            df["invoice_date"]
            .dt.to_period("M")
            .astype("string")
        )
        df["day_of_week"] = df["invoice_date"].dt.day_name()
        df["invoice_hour"] = df["invoice_date"].dt.hour
        df["invoice_date_only"] = df["invoice_date"].dt.date

        # Assign a primary quality/business status to each row.
        conditions = [
            df["unit_price"] < 0,
            df["unit_price"] == 0,
            df["quantity"] == 0,
            df["invoice_date"].isna(),
            df["is_cancelled"],
            df["is_return"],
            df["description"].isna(),
            df["customer_id"].isna(),
            df["is_valid_sale"],
        ]

        statuses = [
            "invalid_price",
            "zero_price",
            "zero_quantity",
            "missing_invoice_date",
            "cancelled",
            "return_or_adjustment",
            "missing_description",
            "missing_customer_id",
            "valid_sale",
        ]

        df["transaction_status"] = np.select(
            conditions,
            statuses,
            default="requires_review",
        )

        # Records that require investigation but should remain traceable.
        exception_mask = (
            (df["unit_price"] <= 0)
            | (df["quantity"] == 0)
            | (df["invoice_date"].isna())
            | (df["description"].isna())
        )

        exceptions = df.loc[exception_mask].copy()

        valid_sales = df.loc[df["is_valid_sale"]]
        customer_sales = valid_sales.loc[
            valid_sales["customer_id"].notna()
        ]

        summary = pd.DataFrame(
            [
                {
                    "metric": "Raw rows",
                    "value": raw_row_count,
                },
                {
                    "metric": "Exact duplicates removed",
                    "value": duplicate_count,
                },
                {
                    "metric": "Rows after deduplication",
                    "value": len(df),
                },
                {
                    "metric": "Valid sales rows",
                    "value": int(df["is_valid_sale"].sum()),
                },
                {
                    "metric": "Valid sales with customer ID",
                    "value": len(customer_sales),
                },
                {
                    "metric": "Cancelled rows",
                    "value": int(df["is_cancelled"].sum()),
                },
                {
                    "metric": "Return or negative-quantity rows",
                    "value": int(df["is_return"].sum()),
                },
                {
                    "metric": "Rows missing customer ID",
                    "value": int(df["customer_id"].isna().sum()),
                },
                {
                    "metric": "Zero-price rows",
                    "value": int(df["is_zero_price"].sum()),
                },
                {
                    "metric": "Negative-price rows",
                    "value": int(df["is_invalid_price"].sum()),
                },
                {
                    "metric": "Exception rows",
                    "value": len(exceptions),
                },
                {
                    "metric": "Total valid sales revenue",
                    "value": round(
                        float(valid_sales["sales_revenue"].sum()),
                        2,
                    ),
                },
                {
                    "metric": "Total recorded return value",
                    "value": round(
                        float(df["return_value"].sum()),
                        2,
                    ),
                },
            ]
        )

        return df, summary

    @staticmethod
    def save_outputs(
        cleaned_df: pd.DataFrame,
        summary: pd.DataFrame,
    ) -> None:
        """Save the processed dataset and cleaning report."""

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        cleaned_path = (
            PROCESSED_DIR / "retail_transactions_clean.csv"
        )
        exceptions_path = (
            PROCESSED_DIR / "data_exceptions.csv"
        )
        summary_path = REPORTS_DIR / "cleaning_summary.csv"

        exception_mask = (
            (cleaned_df["unit_price"] <= 0)
            | (cleaned_df["quantity"] == 0)
            | (cleaned_df["invoice_date"].isna())
            | (cleaned_df["description"].isna())
        )

        cleaned_df.to_csv(
            cleaned_path,
            index=False,
        )

        cleaned_df.loc[exception_mask].to_csv(
            exceptions_path,
            index=False,
        )

        summary.to_csv(
            summary_path,
            index=False,
        )

        print("\nProcessed outputs saved:")
        print(cleaned_path)
        print(exceptions_path)
        print(summary_path)