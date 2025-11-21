from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CLEAN_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "retail_transactions_clean.csv"
)

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "retailiq.db"
)


class DatabaseBuilder:
    """Build the RetailIQ SQLite analytical data warehouse."""

    def __init__(
        self,
        clean_data_path: Path = CLEAN_DATA_PATH,
        database_path: Path = DATABASE_PATH,
    ) -> None:
        self.clean_data_path = clean_data_path
        self.database_path = database_path

    def load_clean_data(self) -> pd.DataFrame:
        """Load the previously cleaned transaction dataset."""

        if not self.clean_data_path.exists():
            raise FileNotFoundError(
                f"Clean dataset not found: {self.clean_data_path}"
            )

        print(f"Loading clean data from: {self.clean_data_path}")

        df = pd.read_csv(
            self.clean_data_path,
            dtype={
                "invoice_id": "string",
                "stock_code": "string",
                "description": "string",
                "customer_id": "string",
                "country": "string",
                "source_sheet": "string",
                "transaction_status": "string",
            },
            parse_dates=["invoice_date"],
            low_memory=False,
        )

        print(f"Rows loaded: {len(df):,}")
        return df

    @staticmethod
    def create_customer_dimension(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create one row per identified customer."""

        customers = (
            df.loc[
                df["customer_id"].notna(),
                ["customer_id", "country"],
            ]
            .drop_duplicates(subset=["customer_id"])
            .sort_values("customer_id")
            .reset_index(drop=True)
        )

        customers.insert(
            0,
            "customer_key",
            np.arange(1, len(customers) + 1),
        )

        return customers

    @staticmethod
    def create_product_dimension(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create one row per product using its most common description."""

        product_descriptions = (
            df.loc[
                df["stock_code"].notna()
                & df["description"].notna(),
                ["stock_code", "description"],
            ]
            .groupby("stock_code")["description"]
            .agg(
                lambda values: (
                    values.mode().iloc[0]
                    if not values.mode().empty
                    else values.iloc[0]
                )
            )
            .reset_index()
        )

        all_products = (
            df[["stock_code"]]
            .drop_duplicates()
            .merge(
                product_descriptions,
                on="stock_code",
                how="left",
            )
            .sort_values("stock_code")
            .reset_index(drop=True)
        )

        all_products["description"] = (
            all_products["description"]
            .fillna("UNKNOWN PRODUCT")
        )

        all_products.insert(
            0,
            "product_key",
            np.arange(1, len(all_products) + 1),
        )

        return all_products

    @staticmethod
    def create_country_dimension(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create one row per country."""

        countries = (
            df[["country"]]
            .drop_duplicates()
            .sort_values("country")
            .reset_index(drop=True)
        )

        countries.insert(
            0,
            "country_key",
            np.arange(1, len(countries) + 1),
        )

        return countries

    @staticmethod
    def create_date_dimension(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create a complete date dimension."""

        minimum_date = df["invoice_date"].min().normalize()
        maximum_date = df["invoice_date"].max().normalize()

        dates = pd.DataFrame(
            {
                "full_date": pd.date_range(
                    minimum_date,
                    maximum_date,
                    freq="D",
                )
            }
        )

        dates["date_key"] = (
            dates["full_date"].dt.strftime("%Y%m%d").astype(int)
        )
        dates["year"] = dates["full_date"].dt.year
        dates["quarter"] = (
            "Q" + dates["full_date"].dt.quarter.astype(str)
        )
        dates["month_number"] = dates["full_date"].dt.month
        dates["month_name"] = dates["full_date"].dt.month_name()
        dates["year_month"] = (
            dates["full_date"].dt.to_period("M").astype(str)
        )
        dates["day_of_month"] = dates["full_date"].dt.day
        dates["day_name"] = dates["full_date"].dt.day_name()
        dates["week_number"] = (
            dates["full_date"]
            .dt.isocalendar()
            .week
            .astype(int)
        )
        dates["is_weekend"] = (
            dates["full_date"].dt.dayofweek >= 5
        ).astype(int)

        return dates[
            [
                "date_key",
                "full_date",
                "year",
                "quarter",
                "month_number",
                "month_name",
                "year_month",
                "day_of_month",
                "day_name",
                "week_number",
                "is_weekend",
            ]
        ]

    @staticmethod
    def create_fact_table(
        df: pd.DataFrame,
        customers: pd.DataFrame,
        products: pd.DataFrame,
        countries: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create the transaction fact table with surrogate keys."""

        customer_lookup = customers.set_index(
            "customer_id"
        )["customer_key"]

        product_lookup = products.set_index(
            "stock_code"
        )["product_key"]

        country_lookup = countries.set_index(
            "country"
        )["country_key"]

        fact = pd.DataFrame()

        fact["transaction_key"] = np.arange(1, len(df) + 1)
        fact["invoice_id"] = df["invoice_id"]

        fact["customer_key"] = (
            df["customer_id"]
            .map(customer_lookup)
            .fillna(0)
            .astype(int)
        )

        fact["product_key"] = (
            df["stock_code"]
            .map(product_lookup)
            .fillna(0)
            .astype(int)
        )

        fact["country_key"] = (
            df["country"]
            .map(country_lookup)
            .fillna(0)
            .astype(int)
        )

        fact["date_key"] = (
            df["invoice_date"]
            .dt.strftime("%Y%m%d")
            .astype(int)
        )

        fact["invoice_datetime"] = df["invoice_date"]
        fact["invoice_hour"] = df["invoice_hour"]
        fact["quantity"] = df["quantity"]
        fact["unit_price"] = df["unit_price"]
        fact["net_line_value"] = df["net_line_value"]
        fact["sales_revenue"] = df["sales_revenue"]
        fact["return_value"] = df["return_value"]
        fact["is_cancelled"] = df["is_cancelled"].astype(int)
        fact["is_return"] = df["is_return"].astype(int)
        fact["is_valid_sale"] = df["is_valid_sale"].astype(int)
        fact["has_customer_id"] = df["has_customer_id"].astype(int)
        fact["transaction_status"] = df["transaction_status"]

        return fact

    def build_database(self) -> None:
        """Create dimension tables, fact table, indexes, and views."""

        df = self.load_clean_data()

        print("Creating dimensions...")

        customers = self.create_customer_dimension(df)
        products = self.create_product_dimension(df)
        countries = self.create_country_dimension(df)
        dates = self.create_date_dimension(df)

        print("Creating fact table...")

        fact_transactions = self.create_fact_table(
            df=df,
            customers=customers,
            products=products,
            countries=countries,
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.database_path.exists():
            self.database_path.unlink()

        print(f"Building database: {self.database_path}")

        with sqlite3.connect(self.database_path) as connection:
            customers.to_sql(
                "dim_customer",
                connection,
                index=False,
                if_exists="replace",
            )

            products.to_sql(
                "dim_product",
                connection,
                index=False,
                if_exists="replace",
            )

            countries.to_sql(
                "dim_country",
                connection,
                index=False,
                if_exists="replace",
            )

            dates.to_sql(
                "dim_date",
                connection,
                index=False,
                if_exists="replace",
            )

            fact_transactions.to_sql(
                "fact_transactions",
                connection,
                index=False,
                if_exists="replace",
                chunksize=50_000,
            )

            self.create_indexes(connection)
            self.create_views(connection)

        print("\nDatabase created successfully.")
        print(f"Customers: {len(customers):,}")
        print(f"Products: {len(products):,}")
        print(f"Countries: {len(countries):,}")
        print(f"Dates: {len(dates):,}")
        print(f"Fact rows: {len(fact_transactions):,}")

    @staticmethod
    def create_indexes(
        connection: sqlite3.Connection,
    ) -> None:
        """Create indexes for common analytical filters and joins."""

        index_statements = [
            """
            CREATE INDEX idx_fact_invoice
            ON fact_transactions(invoice_id)
            """,
            """
            CREATE INDEX idx_fact_customer
            ON fact_transactions(customer_key)
            """,
            """
            CREATE INDEX idx_fact_product
            ON fact_transactions(product_key)
            """,
            """
            CREATE INDEX idx_fact_country
            ON fact_transactions(country_key)
            """,
            """
            CREATE INDEX idx_fact_date
            ON fact_transactions(date_key)
            """,
            """
            CREATE INDEX idx_fact_valid_sale
            ON fact_transactions(is_valid_sale)
            """,
        ]

        for statement in index_statements:
            connection.execute(statement)

    @staticmethod
    def create_views(
        connection: sqlite3.Connection,
    ) -> None:
        """Create reusable analytical SQL views."""

        connection.executescript(
            """
            DROP VIEW IF EXISTS vw_valid_sales;
            DROP VIEW IF EXISTS vw_monthly_sales;
            DROP VIEW IF EXISTS vw_country_performance;
            DROP VIEW IF EXISTS vw_product_performance;
            DROP VIEW IF EXISTS vw_customer_performance;

            CREATE VIEW vw_valid_sales AS
            SELECT
                f.transaction_key,
                f.invoice_id,
                f.invoice_datetime,
                f.date_key,
                f.invoice_hour,
                f.quantity,
                f.unit_price,
                f.sales_revenue,
                f.customer_key,
                c.customer_id,
                f.product_key,
                p.stock_code,
                p.description,
                f.country_key,
                co.country
            FROM fact_transactions AS f
            LEFT JOIN dim_customer AS c
                ON f.customer_key = c.customer_key
            LEFT JOIN dim_product AS p
                ON f.product_key = p.product_key
            LEFT JOIN dim_country AS co
                ON f.country_key = co.country_key
            WHERE f.is_valid_sale = 1;

            CREATE VIEW vw_monthly_sales AS
            SELECT
                d.year,
                d.month_number,
                d.month_name,
                d.year_month,
                ROUND(SUM(f.sales_revenue), 2) AS revenue,
                COUNT(DISTINCT f.invoice_id) AS orders,
                COUNT(DISTINCT CASE
                    WHEN f.customer_key > 0
                    THEN f.customer_key
                END) AS customers,
                SUM(f.quantity) AS units_sold
            FROM fact_transactions AS f
            JOIN dim_date AS d
                ON f.date_key = d.date_key
            WHERE f.is_valid_sale = 1
            GROUP BY
                d.year,
                d.month_number,
                d.month_name,
                d.year_month;

            CREATE VIEW vw_country_performance AS
            SELECT
                co.country,
                ROUND(SUM(f.sales_revenue), 2) AS revenue,
                COUNT(DISTINCT f.invoice_id) AS orders,
                COUNT(DISTINCT CASE
                    WHEN f.customer_key > 0
                    THEN f.customer_key
                END) AS customers,
                SUM(f.quantity) AS units_sold
            FROM fact_transactions AS f
            JOIN dim_country AS co
                ON f.country_key = co.country_key
            WHERE f.is_valid_sale = 1
            GROUP BY co.country;

            CREATE VIEW vw_product_performance AS
            SELECT
                p.stock_code,
                p.description,
                ROUND(SUM(f.sales_revenue), 2) AS revenue,
                SUM(f.quantity) AS units_sold,
                COUNT(DISTINCT f.invoice_id) AS orders
            FROM fact_transactions AS f
            JOIN dim_product AS p
                ON f.product_key = p.product_key
            WHERE f.is_valid_sale = 1
            GROUP BY
                p.stock_code,
                p.description;

            CREATE VIEW vw_customer_performance AS
            SELECT
                c.customer_id,
                ROUND(SUM(f.sales_revenue), 2) AS revenue,
                COUNT(DISTINCT f.invoice_id) AS orders,
                SUM(f.quantity) AS units_purchased,
                MIN(f.invoice_datetime) AS first_purchase,
                MAX(f.invoice_datetime) AS latest_purchase
            FROM fact_transactions AS f
            JOIN dim_customer AS c
                ON f.customer_key = c.customer_key
            WHERE
                f.is_valid_sale = 1
                AND f.customer_key > 0
            GROUP BY c.customer_id;
            """
        )