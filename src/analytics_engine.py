from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "retailiq.db"
)

ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytics"
)

REPORTS_DIR = PROJECT_ROOT / "reports"


class AnalyticsEngine:
    """Generate executive analytics and RFM customer segmentation."""

    def __init__(
        self,
        database_path: Path = DATABASE_PATH,
    ) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.database_path}"
            )

        return sqlite3.connect(self.database_path)

    def create_executive_kpis(self) -> pd.DataFrame:
        """Calculate the main business KPIs."""

        with self._connect() as connection:
            sales_summary = pd.read_sql_query(
                """
                SELECT
                    ROUND(SUM(sales_revenue), 2) AS gross_revenue,
                    COUNT(DISTINCT invoice_id) AS total_orders,
                    COUNT(
                        DISTINCT CASE
                            WHEN customer_key > 0
                            THEN customer_key
                        END
                    ) AS identified_customers,
                    SUM(quantity) AS units_sold,
                    ROUND(
                        SUM(
                            CASE
                                WHEN customer_key = 0
                                THEN sales_revenue
                                ELSE 0
                            END
                        ),
                        2
                    ) AS unidentified_customer_revenue
                FROM fact_transactions
                WHERE is_valid_sale = 1
                """,
                connection,
            ).iloc[0]

            return_summary = pd.read_sql_query(
                """
                SELECT
                    ROUND(SUM(return_value), 2) AS return_value,
                    COUNT(
                        DISTINCT CASE
                            WHEN is_cancelled = 1
                            THEN invoice_id
                        END
                    ) AS cancelled_invoices,
                    COUNT(DISTINCT invoice_id) AS all_invoices
                FROM fact_transactions
                """,
                connection,
            ).iloc[0]

            repeat_summary = pd.read_sql_query(
                """
                SELECT
                    COUNT(*) AS customers_with_orders,
                    SUM(
                        CASE
                            WHEN order_count > 1
                            THEN 1
                            ELSE 0
                        END
                    ) AS repeat_customers
                FROM (
                    SELECT
                        customer_key,
                        COUNT(DISTINCT invoice_id) AS order_count
                    FROM fact_transactions
                    WHERE
                        is_valid_sale = 1
                        AND customer_key > 0
                    GROUP BY customer_key
                )
                """,
                connection,
            ).iloc[0]

        gross_revenue = float(sales_summary["gross_revenue"] or 0)
        return_value = float(return_summary["return_value"] or 0)
        total_orders = int(sales_summary["total_orders"] or 0)
        all_invoices = int(return_summary["all_invoices"] or 0)

        customers_with_orders = int(
            repeat_summary["customers_with_orders"] or 0
        )

        repeat_customers = int(
            repeat_summary["repeat_customers"] or 0
        )

        average_order_value = (
            gross_revenue / total_orders
            if total_orders
            else 0
        )

        return_rate = (
            return_value / gross_revenue * 100
            if gross_revenue
            else 0
        )

        cancellation_rate = (
            int(return_summary["cancelled_invoices"])
            / all_invoices
            * 100
            if all_invoices
            else 0
        )

        repeat_customer_rate = (
            repeat_customers
            / customers_with_orders
            * 100
            if customers_with_orders
            else 0
        )

        unidentified_revenue = float(
            sales_summary["unidentified_customer_revenue"] or 0
        )

        unidentified_revenue_share = (
            unidentified_revenue / gross_revenue * 100
            if gross_revenue
            else 0
        )

        kpis = pd.DataFrame(
            [
                {
                    "metric": "Gross Sales Revenue",
                    "value": round(gross_revenue, 2),
                },
                {
                    "metric": "Recorded Return Value",
                    "value": round(return_value, 2),
                },
                {
                    "metric": "Estimated Net Revenue",
                    "value": round(
                        gross_revenue - return_value,
                        2,
                    ),
                },
                {
                    "metric": "Total Valid Orders",
                    "value": total_orders,
                },
                {
                    "metric": "Identified Customers",
                    "value": int(
                        sales_summary["identified_customers"]
                    ),
                },
                {
                    "metric": "Units Sold",
                    "value": int(sales_summary["units_sold"]),
                },
                {
                    "metric": "Average Order Value",
                    "value": round(average_order_value, 2),
                },
                {
                    "metric": "Return Value Rate (%)",
                    "value": round(return_rate, 2),
                },
                {
                    "metric": "Cancellation Rate (%)",
                    "value": round(cancellation_rate, 2),
                },
                {
                    "metric": "Repeat Customer Rate (%)",
                    "value": round(repeat_customer_rate, 2),
                },
                {
                    "metric": "Unidentified Customer Revenue",
                    "value": round(unidentified_revenue, 2),
                },
                {
                    "metric": "Unidentified Revenue Share (%)",
                    "value": round(
                        unidentified_revenue_share,
                        2,
                    ),
                },
            ]
        )

        return kpis

    def create_rfm_segmentation(
        self,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create customer-level RFM scores and segments."""

        with self._connect() as connection:
            maximum_date = pd.read_sql_query(
                """
                SELECT MAX(invoice_datetime) AS maximum_date
                FROM fact_transactions
                WHERE is_valid_sale = 1
                """,
                connection,
            ).iloc[0]["maximum_date"]

            rfm = pd.read_sql_query(
                """
                SELECT
                    c.customer_id,
                    MIN(f.invoice_datetime) AS first_purchase_date,
                    MAX(f.invoice_datetime) AS latest_purchase_date,
                    COUNT(DISTINCT f.invoice_id) AS frequency,
                    ROUND(SUM(f.sales_revenue), 2) AS monetary,
                    SUM(f.quantity) AS units_purchased
                FROM fact_transactions AS f
                JOIN dim_customer AS c
                    ON f.customer_key = c.customer_key
                WHERE
                    f.is_valid_sale = 1
                    AND f.customer_key > 0
                GROUP BY c.customer_id
                """,
                connection,
            )

        rfm["first_purchase_date"] = pd.to_datetime(
            rfm["first_purchase_date"]
        )

        rfm["latest_purchase_date"] = pd.to_datetime(
            rfm["latest_purchase_date"]
        )

        snapshot_date = pd.to_datetime(maximum_date) + pd.Timedelta(
            days=1
        )

        rfm["recency_days"] = (
            snapshot_date - rfm["latest_purchase_date"]
        ).dt.days

        rfm["customer_lifetime_days"] = (
            rfm["latest_purchase_date"]
            - rfm["first_purchase_date"]
        ).dt.days

        rfm["average_order_value"] = (
            rfm["monetary"] / rfm["frequency"]
        ).round(2)

        rfm["recency_score"] = pd.qcut(
            rfm["recency_days"].rank(method="first"),
            5,
            labels=[5, 4, 3, 2, 1],
        ).astype(int)

        rfm["frequency_score"] = pd.qcut(
            rfm["frequency"].rank(method="first"),
            5,
            labels=[1, 2, 3, 4, 5],
        ).astype(int)

        rfm["monetary_score"] = pd.qcut(
            rfm["monetary"].rank(method="first"),
            5,
            labels=[1, 2, 3, 4, 5],
        ).astype(int)

        rfm["rfm_score"] = (
            rfm["recency_score"].astype(str)
            + rfm["frequency_score"].astype(str)
            + rfm["monetary_score"].astype(str)
        )

        rfm["customer_segment"] = rfm.apply(
            self._assign_segment,
            axis=1,
        )

        segment_summary = (
            rfm.groupby(
                "customer_segment",
                as_index=False,
            )
            .agg(
                customer_count=("customer_id", "count"),
                total_revenue=("monetary", "sum"),
                average_revenue=("monetary", "mean"),
                average_recency_days=("recency_days", "mean"),
                average_frequency=("frequency", "mean"),
            )
        )

        total_revenue = segment_summary["total_revenue"].sum()

        segment_summary["revenue_share_percentage"] = (
            segment_summary["total_revenue"]
            / total_revenue
            * 100
        ).round(2)

        segment_summary["total_revenue"] = (
            segment_summary["total_revenue"].round(2)
        )

        segment_summary["average_revenue"] = (
            segment_summary["average_revenue"].round(2)
        )

        segment_summary["average_recency_days"] = (
            segment_summary["average_recency_days"].round(1)
        )

        segment_summary["average_frequency"] = (
            segment_summary["average_frequency"].round(1)
        )

        segment_summary = segment_summary.sort_values(
            "total_revenue",
            ascending=False,
        )

        return rfm, segment_summary

    @staticmethod
    def _assign_segment(row: pd.Series) -> str:
        """Assign a business-friendly RFM customer segment."""

        recency = row["recency_score"]
        frequency = row["frequency_score"]
        monetary = row["monetary_score"]

        if recency >= 4 and frequency >= 4 and monetary >= 4:
            return "Champions"

        if recency >= 3 and frequency >= 4:
            return "Loyal Customers"

        if recency == 5 and frequency == 1:
            return "New Customers"

        if recency >= 4 and frequency in [2, 3]:
            return "Potential Loyalists"

        if recency <= 2 and frequency >= 4:
            return "At Risk"

        if recency == 1 and frequency <= 2:
            return "Lost Customers"

        if recency <= 2 and frequency <= 3:
            return "Hibernating"

        if monetary >= 4 and frequency >= 2:
            return "Big Spenders"

        return "Need Attention"

    def export_analytics(self) -> None:
        """Export Power BI-ready analytics datasets."""

        ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            monthly_sales = pd.read_sql_query(
                """
                SELECT *
                FROM vw_monthly_sales
                ORDER BY year, month_number
                """,
                connection,
            )

            country_performance = pd.read_sql_query(
                """
                SELECT *
                FROM vw_country_performance
                ORDER BY revenue DESC
                """,
                connection,
            )

            product_performance = pd.read_sql_query(
                """
                SELECT *
                FROM vw_product_performance
                ORDER BY revenue DESC
                """,
                connection,
            )

            customer_performance = pd.read_sql_query(
                """
                SELECT *
                FROM vw_customer_performance
                ORDER BY revenue DESC
                """,
                connection,
            )

        executive_kpis = self.create_executive_kpis()
        customer_rfm, segment_summary = (
            self.create_rfm_segmentation()
        )

        executive_kpis.to_csv(
            REPORTS_DIR / "executive_kpis.csv",
            index=False,
        )

        segment_summary.to_csv(
            REPORTS_DIR / "rfm_segment_summary.csv",
            index=False,
        )

        monthly_sales.to_csv(
            ANALYTICS_DIR / "monthly_sales.csv",
            index=False,
        )

        country_performance.to_csv(
            ANALYTICS_DIR / "country_performance.csv",
            index=False,
        )

        product_performance.to_csv(
            ANALYTICS_DIR / "product_performance.csv",
            index=False,
        )

        customer_performance.to_csv(
            ANALYTICS_DIR / "customer_performance.csv",
            index=False,
        )

        customer_rfm.to_csv(
            ANALYTICS_DIR / "customer_rfm_segments.csv",
            index=False,
        )

        print("\nAnalytics exports created successfully.")
        print("\nExecutive KPIs:")
        print(executive_kpis.to_string(index=False))

        print("\nRFM segment summary:")
        print(segment_summary.to_string(index=False))