# Phase 4.5 — Marketplace weather enrichment

Closes Task 19 of the master plan ("Add Marketplace-sourced dataset enrichment...
Phase 4.5"). A genuine, queried Marketplace dataset joined into the ontology's
Gold layer — not just a namecheck in the README.

## Listing acquired

- **Title:** Pelmorex Weather Source: Frostbyte
- **Global name:** `GZSOZ1LLEL`
- **Provider:** Pelmorex Weather Source
- **Pricing:** Free (`is_monetized = false`), instantly available in this region
  (`is_ready_for_import = true`)
- **License:** Standard Snowflake Marketplace consumer terms, accepted via
  `SYSTEM$ACCEPT_LEGAL_TERMS('DATA_EXCHANGE_LISTING', 'GZSOZ1LLEL')` — no
  additional cost or usage restriction beyond the listing's standard terms.
- This is Pelmorex's standard free hands-on-lab sample dataset (used across
  several official Snowflake quickstarts) — real historical daily weather
  observations, not a toy/synthetic dataset.

Acquired into database `WEATHER_MARKETPLACE`, schema `ONPOINT_ID`:
`POSTAL_CODES` (postal_code → city/country) and `HISTORY_DAY` (daily
temperature/precipitation/wind/snow observations by postal code + date,
US coverage 2019-01-01 through 2026-09-11).

## Coverage limitation (found, not glossed over)

The free listing's ~447 US cities are concentrated in three metro clusters:
**NY/NJ/MA** (New York, Boston, Newark, Jersey City, ...), **Denver**, and
**Seattle/Bay Area** (Seattle, San Francisco, Oakland, ...). There is
**no South, Southeast, or additional Midwest coverage** — no Chicago, Dallas,
Houston, Atlanta, Miami, Charlotte, etc. Confirmed by querying
`POSTAL_CODES` for a shortlist of major cities in those regions: zero matches.
Full nationwide coverage exists in Pelmorex's paid
*"Global Weather & Climate Data by Pelmorex Weather Source"* listing, which
was not pulled in since the free tier already proves the enrichment pattern.

## Region-to-city mapping

`SUPPLY_CHAIN.GOVERNANCE.region_weather_city_map` maps the synthetic
`dim_plant.region` values (which have no geocoordinate) to a representative
city available in this listing's coverage:

| `dim_plant.region` | Representative city | Postal code | Fit |
|---|---|---|---|
| `NORTHEAST` | New York | `10001` | Direct — NYC metro is the best-covered region in the free listing. |
| `WEST` | Seattle | `98101` | Direct — Pacific Northwest / West Coast. |
| `MIDWEST` | Denver | `80202` | Approximate — Denver is Mountain West, not true Midwest, but the nearest continental-interior city this free listing covers. |
| `SOUTH` | *(none)* | — | **Deliberately unmapped** — no representative city exists in this free listing's coverage. |
| `SOUTHEAST` | *(none)* | — | **Deliberately unmapped**, same reason. |

Mapping `SOUTH`/`SOUTHEAST` to a wrong-climate proxy (e.g. Denver again) would
have produced a misleading correlation, so those two plant regions are simply
excluded from the enrichment view rather than force-mapped.

## Enrichment view

`SUPPLY_CHAIN.GOLD.v_shipment_weather_risk` joins
`fact_shipment → dim_plant → region_weather_city_map → HISTORY_DAY` on ship
date, flagging a `severe_weather_flag` when the destination region saw
≥1.0in precipitation, ≥1.0in snowfall, or ≥25mph sustained wind on the day the
shipment moved. Answers the genuine analytical question: *"are late shipments
correlated with severe weather at the destination on the ship date?"*

## Result of the correlation query (as run)

```sql
SELECT plant_region, severe_weather_flag, COUNT(*) AS shipments,
       ROUND(AVG(is_on_time) * 100, 1) AS on_time_pct
FROM SUPPLY_CHAIN.GOLD.v_shipment_weather_risk
GROUP BY plant_region, severe_weather_flag
ORDER BY plant_region, severe_weather_flag;
```

| plant_region | severe_weather_flag | shipments | on_time_pct |
|---|---|---|---|
| MIDWEST | FALSE | 137 | 72.3 |
| MIDWEST | TRUE | 1 | 100.0 |
| NORTHEAST | FALSE | 135 | 80.0 |
| WEST | FALSE | 131 | 66.4 |
| WEST | TRUE | 4 | 100.0 |

408 of 800 shipments matched (only `NORTHEAST`/`WEST`/`MIDWEST` plants have a
mapped city). **Honest finding:** the severe-weather sample sizes here (1 and
4 shipments) are too small to show a real signal in this synthetic dataset —
the demo's synthetic lateness is driven by supplier/entity-resolution logic,
not actual weather, so no causal weather effect should be expected. This
enrichment demonstrates the *join and analytical pattern* (a genuine use of
Marketplace data to test a real hypothesis) rather than asserting a discovered
insight that isn't statistically supported by the data.

## Files

- `01_acquire_weather_listing.sql` — the acquisition steps (idempotent: safe
  to re-run, `CREATE DATABASE IF NOT EXISTS`).
- `02_region_weather_enrichment.sql` — the mapping table + enrichment view +
  correlation query.
