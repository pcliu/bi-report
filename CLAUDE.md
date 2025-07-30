# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Business Intelligence (BI) reporting system** for network traffic analysis built with Python. The system ingests CSV data into ClickHouse database and provides interactive web dashboards and PDF reports for traffic analytics.

## Architecture

The system follows a 3-layer architecture:

1. **Data Service Layer** (`data_service.py`): Centralized data access using Repository pattern
   - `DataService` class handles all ClickHouse database interactions
   - `FilterConditions` class manages multi-dimensional filtering (user, IP type, date range, app category)
   - All Plotly chart generation logic is contained here

2. **Web Dashboard** (`streamlit_dashboard.py`): Interactive Streamlit-based web interface
   - Tab-based navigation: Overview, Traffic Analysis, User Analysis, App Analysis, Time Analysis
   - Real-time filtering controls in sidebar
   - PDF export functionality integrated

3. **PDF Report Generator** (`pdf_generator.py`): Professional report generation
   - Uses ReportLab for document creation
   - Cross-platform Chinese font support
   - Converts Plotly charts to static images for embedding

## Key Commands

### Environment Setup
```bash
# Activate virtual environment (required for all commands)
source .venv/bin/activate

# Install dependencies with uv
uv sync
```

### Running the Application
```bash
# Start web dashboard
streamlit run streamlit_dashboard.py

# Import CSV data to ClickHouse
python import_csv_to_clickhouse.py
```

### Database Configuration
Default ClickHouse connection:
- Host: `127.0.0.1:8123`
- Username: `default`
- Password: `12345678`
- Database: `default`
- Table: `tbl_statistic_userapp_day`

## Data Schema

The main table `tbl_statistic_userapp_day` contains network traffic records with these key fields:
- `user_account`: User identifier
- `ip_type`: 0=IPv4, 1=IPv6
- `app_category_major/minor`: Application classification
- `upstream_traffic/downstream_traffic/total_traffic`: Traffic volumes in bytes
- `duration`: Session duration in microseconds
- `stat_time`: Statistics timestamp

## Filtering System

The `FilterConditions` class supports filtering by:
- User account (dropdown selection)
- IP type (IPv4/IPv6)
- Date range (start/end dates)
- Application major category

All data service methods accept optional `filters` parameter. When modifying queries, ensure filtering is consistently applied.

## Chart Types and Analysis

The system provides these analytical views:
- **Traffic Analysis**: Upload/download distribution, duration patterns, top users
- **User Analysis**: Activity levels, consumption patterns, high-upload risk detection
- **Application Analysis**: Category-based usage and popularity metrics
- **Time Analysis**: Temporal patterns and trend monitoring

## Development Patterns

### Adding New Analysis
1. Add query method to `DataService` class with `filters` parameter
2. Add corresponding chart generation method if needed
3. Integrate into appropriate Streamlit tab
4. Update PDF generator to include new analysis

### Chart Generation
- All charts use Plotly for consistency
- Charts are generated in `DataService` for reuse between web and PDF
- Color schemes are predefined for professional appearance
- Error handling returns `None` for graceful degradation

### Filtering Integration
When adding new features:
- Accept `FilterConditions` parameter in data methods
- Use `filters.build_where_clause()` to generate SQL WHERE clauses
- Update PDF generation to pass filters through
- Ensure Streamlit controls create proper `FilterConditions` objects

## File Organization

- `streamlit_dashboard.py`: Main web application entry point
- `data_service.py`: Core data access and chart generation
- `pdf_generator.py`: Report generation with ReportLab
- `import_csv_to_clickhouse.py`: Data import utility
- `streamlit_dashboard_old.py`: Legacy dashboard (kept for reference)

## Database Operations

The system assumes ClickHouse is running and accessible. For CSV imports:
- Data is validated and converted to appropriate types
- Batch processing handles large files
- Error handling provides meaningful feedback for data issues

All database connections use connection pooling through `clickhouse_connect` library with lazy initialization pattern in `DataService`.

## Memorized Commands

- Start dashboard: `source .venv/bin/activate && streamlit run streamlit_dashboard.py`