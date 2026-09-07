# Gamma Exposure Dashboard

A modular Gamma Exposure and Delta Exposure analytics platform for options markets.

This project analyzes options market structure through Gamma Exposure (GEX), Delta Exposure (DEX), Gamma Flip levels, dealer positioning, options flow, volatility, and historical market data.

It currently focuses on major US indices and related instruments, including:

* SPX
* NDX
* SPY
* QQQ
* ES
* NQ

## Project Origin and Acknowledgements

This project is based on the excellent work of [Darthreign](https://github.com/Darthreign), whose original **GEX Dashboard** repository provided the foundation for this project.

The original project established the initial Gamma Exposure dashboard, data ingestion mechanisms, market calculations, visualizations, and options analytics architecture.

Special thanks to:

**[Darthreign](https://github.com/Darthreign)**

for creating and maintaining the original foundation that made this project possible.

This repository is an independently developed fork and has undergone significant architectural restructuring and refactoring.

The goal is not simply to modify the original interface, but to evolve the codebase into a more modular, maintainable, and extensible Gamma Exposure analytics platform.

## What Changed From the Original Project

The original implementation concentrated many responsibilities inside large modules.

This version progressively separates responsibilities into dedicated architectural layers.

The refactoring focuses on:

* Modular calculations
* Domain models
* Provider abstraction
* Storage separation
* Application orchestration
* Infrastructure isolation
* UI separation
* Backward compatibility
* Improved testing boundaries

The project is being refactored incrementally to avoid changing mathematical behavior unnecessarily.

Existing formulas are preserved unless tests demonstrate a real bug.

## Architecture

The project is organized around clear responsibilities.

```text
gex/
│
├── analysis/
│   ├── backtest.py
│   └── analytical workflows
│
├── api/
│   ├── rest.py
│   └── mcp.py
│
├── application/
│   ├── refresh_market.py
│   ├── refresh_native.py
│   ├── flush_streams.py
│   ├── scheduler.py
│   ├── digest.py
│   ├── export.py
│   └── roll.py
│
├── calculations/
│   ├── gex.py
│   ├── gamma_flip.py
│   ├── levels.py
│   ├── regime.py
│   ├── flow.py
│   ├── greeks.py
│   ├── pinning.py
│   ├── tickstats.py
│   └── native.py
│
├── cli/
│   ├── run.py
│   ├── backfill.py
│   ├── backup.py
│   └── pricehist.py
│
├── config/
│   ├── __init__.py
│   └── providers.py
│
├── domain/
│   ├── models.py
│   ├── quality.py
│   └── state.py
│
├── infrastructure/
│   ├── git_repository.py
│   ├── logsetup.py
│   └── rates.py
│
├── providers/
│   ├── ingest.py
│   ├── idxopt.py
│   ├── futopt.py
│   ├── rtquote.py
│   ├── flowtape.py
│   ├── tickcapture.py
│   ├── tt_auth.py
│   └── tt_web.py
│
├── storage/
│   ├── snapshots.py
│   ├── history.py
│   ├── prices.py
│   ├── ticks.py
│   ├── flow.py
│   └── parquet.py
│
├── ui/
│   ├── app.py
│   ├── i18n.py
│   └── scales.py
│
├── state.py
├── metrics.py
├── scheduler.py
└── app.py
```

## Architectural Principles

The project follows a practical incremental architecture rather than introducing unnecessary abstraction.

### Calculations

Pure mathematical and analytical logic belongs in:

```text
gex/calculations/
```

Examples include:

* Gamma Exposure calculations
* Delta Exposure calculations
* Gamma Flip
* Key levels
* Market regimes
* Flow calculations
* Greeks
* Pinning calculations

These modules should not depend on Dash, scheduling, HTTP endpoints, or storage implementation.

### Domain

Core concepts and business models belong in:

```text
gex/domain/
```

This includes:

* Data quality
* Market state
* Core analytical models
* Domain-level configuration

### Providers

External market-data connections belong in:

```text
gex/providers/
```

Providers are responsible for acquiring data, not calculating the entire market analysis.

Examples include:

* CBOE ingestion
* Real-time quotes
* Index options
* Futures options
* Flow feeds

### Storage

Persistence is isolated in:

```text
gex/storage/
```

This includes:

* Snapshots
* Historical data
* Prices
* Tick data
* Flow data
* Parquet operations

### Application

Application workflows belong in:

```text
gex/application/
```

Examples include:

* Refreshing market data
* Refreshing native instruments
* Flushing streams
* Scheduling workflows
* Exporting data
* Digest generation

The application layer coordinates the system without containing the mathematical implementation itself.

### Infrastructure

Technical infrastructure belongs in:

```text
gex/infrastructure/
```

Examples:

* Logging
* Git repository operations
* Rates and external infrastructure helpers

### User Interface

UI-specific code belongs in:

```text
gex/ui/
```

The UI should consume application and analytical layers rather than containing core business calculations.

## Main Features

### Gamma Exposure

The platform calculates Gamma Exposure across options strikes and expirations.

The general GEX convention used is:

```text
GEX = Gamma × Open Interest × Contract Multiplier × Spot² × 0.01
```

Calls and puts are represented according to the project's established sign convention.

### Delta Exposure

DEX measures the delta-weighted market exposure associated with open interest.

Historical and live calculations are kept consistent through characterization and regression tests.

### Gamma Flip

The Gamma Flip estimates the underlying price level where aggregate gamma exposure changes sign.

The calculation evaluates the gamma profile over a range of theoretical spot prices and identifies the zero crossing.

### Key Gamma Levels

The system identifies important market structure levels such as:

* Call Wall
* Put Wall
* High Gamma strikes
* Gamma Flip
* Key GEX concentrations

### Market Regime

The project classifies market structure using gamma-related thresholds and percentile calculations.

### Options Flow

Flow calculations analyze changes in options activity and delta-weighted exposure.

Where real signed aggressor information is available, the system can distinguish actual reported flow from proxy calculations.

### Historical Analysis

The project supports persistence and historical analysis of:

* GEX
* DEX
* Spot price
* Gamma Flip
* Options structure
* Flow data

### Backtesting

Analytical and backtesting functionality is separated from the primary application workflow.

## Data Sources

### CBOE

The primary public data source is CBOE delayed market data.

This allows the project to operate without requiring a brokerage account for the core dashboard functionality.

The public source provides approximately delayed options market information depending on the endpoint and market conditions.

### Optional Providers

The architecture is designed so additional providers can be integrated without placing provider-specific logic throughout the entire application.

Provider metadata and capabilities are centralized to support future expansion.

Potential categories include:

* Delayed public data
* Real-time brokerage feeds
* Historical market data providers
* Licensed institutional feeds

Provider integrations must respect licensing and redistribution restrictions.

## Installation

Clone the repository:

```bash
git clone https://github.com/Juanchoszs/Gamma-.git
cd Gamma-
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the tests:

```bash
python -m pytest tests -q
```

Start the application:

```bash
python run.py
```

The dashboard should be available locally at:

```text
http://127.0.0.1:8050
```

## Development Philosophy

This project is being improved through incremental refactoring.

The goal is not to rewrite everything at once.

Each architectural change should:

1. Preserve existing behavior.
2. Maintain public compatibility where practical.
3. Avoid duplicating formulas.
4. Keep mathematical calculations deterministic.
5. Add regression tests when behavior is not already protected.
6. Run targeted tests after changes.
7. Run the complete test suite before completion.
8. Avoid unnecessary abstraction.

Large "enterprise architecture" structures are intentionally avoided unless they solve a real problem.

The architecture should become clearer, not simply contain more folders.

## Testing

The project contains an extensive regression test suite covering:

* Metrics
* GEX calculations
* DEX calculations
* Gamma Flip
* Market state
* Data quality
* Providers
* Native instruments
* Flow processing
* Storage
* Scheduling boundaries
* API behavior

Run the complete suite with:

```bash
python -m pytest tests -q
```

Before committing significant architectural changes, the full suite should pass.

## Project Status

The project is under active architectural development.

The current work focuses on transforming the original codebase into a clearer modular structure while preserving the analytical functionality that made the original project valuable.

Current refactoring areas include:

* Calculation isolation
* Provider boundaries
* Storage separation
* Application orchestration
* UI separation
* Import compatibility
* Dependency reduction
* Test coverage
* Documentation

## Important Notice

This project is an analytical and educational tool.

It does not provide:

* Investment advice
* Trading signals
* Automated trading recommendations
* Guaranteed market predictions

Options and derivatives involve substantial financial risk.

Any analysis generated by this software should be independently evaluated.

## License and Original Work

The original project and its licensing terms must be respected.

This repository acknowledges the work of the original author:

**[Darthreign](https://github.com/Darthreign)**

The original GEX Dashboard provided the foundation upon which this independently refactored and extended version is being developed.

If you use, redistribute, or contribute to this project, please also respect the licensing and attribution requirements associated with the original work.

## Acknowledgements

Special thanks again to:

**[Darthreign](https://github.com/Darthreign)**

for the original GEX Dashboard project and for creating the foundation that enabled this project to evolve.

This repository represents continued independent development, architectural restructuring, and experimentation built upon that foundation.

## Repository

Current project repository:

https://github.com/Juanchoszs/Gamma-

Original author:

https://github.com/Darthreign
