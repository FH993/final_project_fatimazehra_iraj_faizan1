# From Request to Resolution: A High-Frequency Operational Analysis of Chicago’s 311 Service Delivery, 2021–2024
Final Project Repository for Data Analytics and Visualization
##### Group Members
Iraj Butt - Iraj,
Fatima Hussain - fatimazehra,
Faizan Rashid - faizan1

### Policy Topic and Motivation

City governments rely heavily on administrative data to monitor operational performance and ensure equitable service delivery. In Chicago, 311 service requests provide a detailed, high-frequency record of resident demand for city services and the speed at which those services are resolved across neighborhoods.

This project analyzes how patterns in Chicago’s 311 service delivery evolved between January 2021 and the most recent available data in 2024, spanning both the period prior to and during the mayoral administration of Brandon Johnson within the City of Chicago. The analysis is intentionally descriptive rather than causal, focusing on whether observable patterns in service demand, response times, and neighborhood-level disparities shifted around a major administrative transition.

This type of operational analysis reflects how governments and analytics teams use performance data in practice: to diagnose system behavior, identify equity concerns, and inform where deeper evaluation or intervention may be warranted.

### Research Questions

1.	How did overall demand for city services, measured as 311 requests per capita, change between 2021 and 2024?
2.	Did service response times exhibit changes in level, trend, or variability before versus during the Johnson administration?
3.	How did disparities in service delivery across neighborhoods particularly by income level evolve over time?
4.	Which categories of services (e.g., sanitation, rodent control, infrastructure-related requests) contributed most to observed changes in operational performance?

The project does not make causal claims or attribute observed changes to specific policies; instead, it documents high-frequency operational patterns around an administrative regime change.

### Proposed Datasets

1.	**Chicago 311 Service Requests (2021–2024):**
2.	*Publicly available administrative data containing request dates, completion dates, service categories, and geolocation. These data allow construction of monthly time series and neighborhood-level performance metrics.*
3.	**American Community Survey (ACS) Census Tract Data:**
4.	*Socioeconomic indicators including median household income, poverty rates, and population counts, used to contextualize service delivery patterns and normalize request volume.*
5.	**Chicago Geographic Boundary Files:**
*Census tract or community area shapefiles used to spatially aggregate service requests and visualize neighborhood-level variation.
All datasets are publicly available and can be accessed within the quarter.*

### Our Visualization Plan

##### I. System-Level Performance Over Time
*(How is the system behaving overall?)*

1. Regime-Annotated Time Series (Core Figure)
•	What: Monthly median response time
•	Extras: Interquartile range (25–75%)
•	Split by: Service category (facets)
•	Annotation: Vertical line at May 2023 (administrative transition)

2. Request Volume Over Time
•	What: Monthly requests per 1,000 residents
•	Split by: Service category
•	Optional: Seasonal smoothing


##### II. Distributional Performance (Beyond Averages)
*(Where are the delays happening?)*

3. Quantile Shift Plot (Pre vs During)
•	What: Empirical quantiles (10th–90th percentile)
•	Compare:
o	Pre: Jan 2021–Apr 2023
o	Post: May 2023–2024
•	Reference: 45° line

Why it matters:
Shows whether tail delays improved or worsened.

4. Response-Time Survival Curves
•	What: Probability a request remains unresolved after t days
•	Compare: Pre vs post
•	Split by: Service category

Why it matters:
Explicitly visualizes long delays.

##### III. Equity & Inequality Over Time
*(Who benefits, and who waits?)*

5. Dynamic Equity Gap Over Time
•	What:
Rolling 3-month median response time
(lowest income quintile − highest income quintile)
•	Time span: 2021–2024

Why it matters:
Measures inequality as a dynamic operational outcome.

6. Equity Concentration Curve
•	What:
Cumulative share of slowest responses by income quintile
•	Interpretation:
Are delays disproportionately concentrated in low-income areas?

##### IV. Spatial Heterogeneity
*(Where are problems concentrated?)*

7. Spatial Change Map (Δ Performance)
•	What:
Change in median response time
(post−Pre)
•	Geography: Census tracts or community areas
•	Scale: Diverging, symmetric

Why it matters:
Shows where performance improved or deteriorated.

8. Paired Dot Plot (Before vs During)
•	What:
Each neighborhood as a dot
X = pre median, Y = post median
•	Reference: 45° line

Why it matters:
Cleanly shows heterogeneity without a map.

##### V. Operational Decision Tools (Recruiter Gold)

9. Priority Matrix (Impact × Volume)
•	X-axis: Median response time
•	Y-axis: Requests per capita
•	Units: Neighborhood × service type

Why it matters:
This is exactly how ops and consulting teams prioritize interventions.

10. Stability vs Change Classification
•	What:
Neighborhoods classified as:
o	Persistently poor
o	Newly deteriorating
o	Improving
o	Consistently strong

Why it matters:
Distinguishes chronic issues from emerging ones.

##### VI. Demand Composition
*(What residents are asking for)*

11. Service Mix Shift
•	What:
Stacked bars or stacked area chart
•	Time: Annual or monthly
•	Categories: Top service types

Why it matters:
Provides demand-side context for performance trends.

This project demonstrates Python-based data cleaning, feature engineering, time-series aggregation, spatial joins, and distributional analysis using large-scale administrative data. By combining temporal, spatial, and equity-focused visualizations, the analysis provides a detailed operational view of city service delivery and produces insights suitable for inclusion in a professional data analytics portfolio.

