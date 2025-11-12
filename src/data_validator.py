from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


class DataValidator:
    """Generate data-quality reports for the raw retail dataset."""

    def __init__(self, dataframe: pd.DataFrame) -> None:
        self.df = dataframe.copy()

    def create_column_profile(self) -> pd.DataFrame:
        """Create a column-level quality profile."""

        total_rows = len(self.df)

        profile = pd.DataFrame({
            "column": self.df.columns,
            "data_type": [str(dtype) for dtype in self.df.dtypes],
            "total_rows": total_rows,
            "missing_values": self.df.isna().sum().values,
            "unique_values": [
                self.df[column].nunique(dropna=True)
                for column in self.df.columns
            ],
        })

        profile["missing_percentage"] = (
            profile["missing_values"] / total_rows * 100
        ).round(2)

        return profile

    def create_quality_summary(self) -> pd.DataFrame:
        """Create a business-focused data-quality summary."""

        invoice_series = self.df["Invoice"].astype("string")
        description_series = self.df["Description"].astype("string")
        country_series = self.df["Country"].astype("string")

        cancelled_rows = invoice_series.str.upper().str.startswith(
            "C",
            na=False,
        )

        summary = [
            {
                "metric": "Total rows",
                "value": len(self.df),
            },
            {
                "metric": "Total columns",
                "value": self.df.shape[1],
            },
            {
                "metric": "Duplicate rows",
                "value": int(self.df.duplicated().sum()),
            },
            {
                "metric": "Missing customer IDs",
                "value": int(self.df["Customer ID"].isna().sum()),
            },
            {
                "metric": "Missing descriptions",
                "value": int(self.df["Description"].isna().sum()),
            },
            {
                "metric": "Missing invoice dates",
                "value": int(self.df["InvoiceDate"].isna().sum()),
            },
            {
                "metric": "Blank descriptions",
                "value": int(
                    description_series.str.strip().eq("").sum()
                ),
            },
            {
                "metric": "Blank countries",
                "value": int(
                    country_series.str.strip().eq("").sum()
                ),
            },
            {
                "metric": "Cancelled transaction rows",
                "value": int(cancelled_rows.sum()),
            },
            {
                "metric": "Unique cancelled invoices",
                "value": int(
                    invoice_series[cancelled_rows].nunique()
                ),
            },
            {
                "metric": "Negative quantities",
                "value": int((self.df["Quantity"] < 0).sum()),
            },
            {
                "metric": "Zero quantities",
                "value": int((self.df["Quantity"] == 0).sum()),
            },
            {
                "metric": "Negative prices",
                "value": int((self.df["Price"] < 0).sum()),
            },
            {
                "metric": "Zero prices",
                "value": int((self.df["Price"] == 0).sum()),
            },
            {
                "metric": "Unique invoices",
                "value": int(self.df["Invoice"].nunique()),
            },
            {
                "metric": "Unique customers",
                "value": int(self.df["Customer ID"].nunique()),
            },
            {
                "metric": "Unique products",
                "value": int(self.df["StockCode"].nunique()),
            },
            {
                "metric": "Unique countries",
                "value": int(self.df["Country"].nunique()),
            },
            {
                "metric": "Earliest invoice date",
                "value": self.df["InvoiceDate"].min(),
            },
            {
                "metric": "Latest invoice date",
                "value": self.df["InvoiceDate"].max(),
            },
        ]

        return pd.DataFrame(summary)

    def save_reports(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Generate and save validation reports as CSV files."""

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        column_profile = self.create_column_profile()
        quality_summary = self.create_quality_summary()

        column_profile_path = REPORTS_DIR / "column_profile.csv"
        quality_summary_path = REPORTS_DIR / "data_quality_summary.csv"

        column_profile.to_csv(
            column_profile_path,
            index=False,
        )

        quality_summary.to_csv(
            quality_summary_path,
            index=False,
        )

        print("\nData-quality reports saved:")
        print(column_profile_path)
        print(quality_summary_path)

        return column_profile, quality_summary