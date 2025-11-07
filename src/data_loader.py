from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx"


class DataLoader:
    """Load and combine the raw Online Retail II Excel sheets."""

    def __init__(self, data_path: Path = DEFAULT_DATA_PATH) -> None:
        self.data_path = data_path

    def load_data(self) -> pd.DataFrame:
        """Load every worksheet and combine them into one DataFrame."""

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Dataset not found at: {self.data_path}"
            )

        print(f"Loading dataset from: {self.data_path}")

        excel_file = pd.ExcelFile(self.data_path)
        print(f"Sheets found: {excel_file.sheet_names}")

        dataframes: list[pd.DataFrame] = []

        for sheet_name in excel_file.sheet_names:
            print(f"Loading sheet: {sheet_name}")

            sheet_df = pd.read_excel(
                self.data_path,
                sheet_name=sheet_name,
                dtype={
                    "Invoice": str,
                    "StockCode": str,
                },
            )

            sheet_df["source_sheet"] = sheet_name
            dataframes.append(sheet_df)

        combined_df = pd.concat(
            dataframes,
            ignore_index=True,
        )

        print("Dataset loaded successfully.")
        print(f"Total rows: {combined_df.shape[0]:,}")
        print(f"Total columns: {combined_df.shape[1]}")

        return combined_df