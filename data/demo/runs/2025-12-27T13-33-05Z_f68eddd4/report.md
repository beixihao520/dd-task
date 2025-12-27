# Analysis Run Report

**Run ID:** 2025-12-27T13-33-05Z_f68eddd4
**Timestamp:** 2025-12-27T13:33:25.728690+00:00

## Status: ✅ Success

## Analysis Plan
**Intents:** 12
**Rationale:** The analysis plan is designed to address the key research objectives outlined in the project scope. The intents focus on understanding overall satisfaction, segment differences, feature usage, and retention risks. High priority is given to analyses that directly inform the Q1 product roadmap, such as NPS and satisfaction drivers. Segment analyses are prioritized to identify underperforming areas, while demographic and income analyses are lower priority but can provide additional insights.

## Cuts Executed: 9
- **cut_003**: nps on Q_NPS
- **cut_003**: top2box on Q_OVERALL_SAT
- **cut_003**: mean on Q_OVERALL_SAT
- **cut_003**: frequency on Q_FEATURES_USED
- **cut_003**: mean on Q_OVERALL_SAT
- **cut_003**: mean on Q_OVERALL_SAT
- **cut_003**: mean on Q_OVERALL_SAT
- **cut_003**: top2box on Q_EASE_OF_USE
- **cut_003**: mean on Q_OVERALL_SAT

## Failed Cuts: 3
- **intent_003**: Identify key drivers of satisfaction by correlatin...
- **intent_006**: Identify customers at risk of churn by analyzing l...
- **intent_007**: Examine the correlation between usage frequency (Q...

## Execution Results
**Tables Generated:** 9

### cut_003
- Metric: nps
- Question: Q_NPS
- Base N: 60
- ⚠️ [CENTRAL] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [EAST] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [NORTH] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [SOUTH] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [WEST] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: top2box
- Question: Q_OVERALL_SAT
- Base N: 60
- ⚠️ [segment_002] Base size (60) is below recommended threshold (100). Interpret results with caution.
- ⚠️ [Not segment_002] Base size (0) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: mean
- Question: Q_OVERALL_SAT
- Base N: 60
- ⚠️ Multi-dimension cross-tabs not fully supported. Using first dimension only. Ignored: ['segment_003', 'segment_001']
- ⚠️ [segment_002] Base size (60) is below recommended threshold (100). Interpret results with caution.
- ⚠️ [Not segment_002] Base size (0) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: frequency
- Question: Q_FEATURES_USED
- Base N: 60
- ⚠️ [2] Base size (4) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [3] Base size (10) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [4] Base size (24) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [5] Base size (22) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: mean
- Question: Q_OVERALL_SAT
- Base N: 60
- ⚠️ [LONG] Base size (29) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [MED] Base size (15) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [NEW] Base size (16) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: mean
- Question: Q_OVERALL_SAT
- Base N: 60
- ⚠️ Multi-dimension cross-tabs not fully supported. Using first dimension only. Ignored: ['Q_GENDER']
- ⚠️ [21] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [22] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [23] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [24] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [25] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [26] Base size (3) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [27] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [28] Base size (3) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [29] Base size (3) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [30] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [31] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [32] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [33] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [34] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [35] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [36] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [37] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [38] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [39] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [40] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [41] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [42] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [43] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [44] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [45] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [46] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [47] Base size (2) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [48] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [49] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [50] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [51] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [52] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [53] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [55] Base size (1) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: mean
- Question: Q_OVERALL_SAT
- Base N: 37
- ⚠️ [BASIC] Base size (11) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [ENT] Base size (17) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [FREE] Base size (9) is below minimum threshold (30). Results may not be statistically reliable.

### cut_003
- Metric: top2box
- Question: Q_EASE_OF_USE
- Base N: 60
- ⚠️ Base size (60) is below recommended threshold (100). Interpret results with caution.

### cut_003
- Metric: mean
- Question: Q_OVERALL_SAT
- Base N: 60
- ⚠️ [HIGH] Base size (20) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [LOW] Base size (12) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [MED] Base size (15) is below minimum threshold (30). Results may not be statistically reliable.
- ⚠️ [VHIGH] Base size (13) is below minimum threshold (30). Results may not be statistically reliable.

## Errors
- Intent intent_003 failed
- Intent intent_006 failed
- Intent intent_007 failed
