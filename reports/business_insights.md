# RetailIQ Business Insights

## Executive Summary

RetailIQ analyzes 1,067,371 online retail transaction records covering
December 2009 through December 2011. The solution combines Python-based
data validation and cleaning, a SQLite analytical warehouse, SQL views,
RFM customer segmentation, and a three-page Power BI dashboard.

## Key Performance Indicators

| Metric | Result |
|---|---:|
| Gross Sales Revenue | $20.91M |
| Estimated Net Revenue | $19.39M |
| Valid Orders | 40,077 |
| Identified Customers | 5,878 |
| Units Sold | 11.39M |
| Average Order Value | $521.84 |
| Return Value Rate | 7.29% |
| Repeat Customer Rate | 72.39% |
| Unidentified Revenue Share | 15.44% |

## Customer Insights

- Champion customers account for 68.16% of identified-customer revenue.
- The business has 1,291 Champion customers.
- The 354 At Risk customers generated approximately $1.12M in historical revenue.
- Hibernating and Lost Customers represent significant reactivation opportunities.
- A repeat-customer rate of 72.39% indicates strong customer retention.
- Revenue is highly concentrated among the most valuable customer segments.

## Product Insights

- The company sold 4,745 active products.
- The highest-revenue product generated approximately $344.07K.
- Several products generate high unit volume but comparatively lower revenue.
- Product revenue is concentrated among a relatively small set of top-performing items.
- High-volume products should be reviewed for pricing, margin, and inventory availability.

## Market Insights

- The United Kingdom contributes approximately 85.18% of total revenue.
- International markets contribute approximately 14.82%.
- Ireland, the Netherlands, Germany, and France are leading international markets.
- Heavy dependence on the United Kingdom creates geographic concentration risk.
- Selected European markets show potential for targeted expansion.

## Data-Quality Findings

- 12,133 exact duplicate rows were identified and removed.
- 242,870 records were missing Customer IDs after deduplication.
- Missing Customer IDs were retained for revenue analysis but excluded from RFM segmentation.
- 19,433 cancellation rows and 22,889 negative-quantity rows were preserved for return analysis.
- Zero-price and invalid-price transactions were separated as data exceptions.
- Non-product entries such as postage and manual adjustments were excluded from product rankings.

## Business Recommendations

1. Launch personalized retention campaigns for high-value At Risk customers.
2. Introduce loyalty and VIP benefits for Champion customers.
3. Develop reactivation campaigns for Lost and Hibernating customers.
4. Prioritize inventory planning for consistently high-volume products.
5. Review high-volume, low-revenue products for pricing and profitability.
6. Expand marketing efforts in strong European markets.
7. Improve customer identification because 15.44% of revenue lacks a Customer ID.
8. Investigate the main causes of the 7.29% return-value rate.
9. Reduce geographic concentration by growing international revenue.
10. Track customer-segment movement over time to measure campaign effectiveness.