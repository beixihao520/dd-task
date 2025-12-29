# Analysis Run Report

**Run ID:** 2025-12-29T15-21-16Z_9760a9ae
**Timestamp:** 2025-12-29T15:21:31.780675+00:00
**Dataset Hash:** a6f03d8d1e33da7d...

## Status: ✅ Success

## Analysis Plan
**Intents:** 5
**Rationale:** The analysis plan aims to provide a comprehensive understanding of customer satisfaction and identify actionable insights for product improvement. By analyzing NPS, satisfaction levels, and feature usage across different customer segments, we can pinpoint areas of strength and weakness. This will help prioritize improvements in the product roadmap and enhance customer retention strategies.

## Cuts Executed: 3
- **cut_nps_by_region**: nps on Q_NPS
- **cut_nps_by_tenure_segment**: nps on Q_NPS
- **cut_at_risk_customers**: frequency on Q_NPS

## Failed Cuts: 2
- **intent_002**: Compare satisfaction across subscription plans to ...
- **intent_003**: Analyze correlation between feature usage and over...

## Execution Results
**Tables Generated:** 3

### cut_nps_by_region
- Metric: nps
- Question: Q_NPS
- Base N: 60
- ⚠️ [CENTRAL] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [EAST] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [NORTH] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [SOUTH] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [WEST] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.

### cut_nps_by_tenure_segment
- Metric: nps
- Question: Q_NPS
- Base N: 60
- ⚠️ Multi-dimension cross-tabs not fully supported. Using first dimension only. Ignored: ['long_term_customers', 'new_customers']
- ⚠️ [LONG] Base size (29) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [MED] Base size (15) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [NEW] Base size (16) is below minimum threshold (30). Results may not be statistically reliable.

### cut_at_risk_customers
- Metric: frequency
- Question: Q_NPS
- Base N: 13
- ⚠️ [low_purchase_intent] Base size (5) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [not_low_purchase_intent] Base size (8) is below minimum threshold (30). Results may not be statistically reliable.
