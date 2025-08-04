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

# Import application category mappings
python import_app_categories.py
```

### Database Configuration
Default ClickHouse connection:
- Host: `127.0.0.1:8123`
- Username: `default`
- Password: `12345678`
- Database: `default`
- Tables: 
  - `tbl_statistic_userapp_day`: Main traffic data
  - `app_category_major`: Application major category mappings (ID → Name)
  - `app_category_minor`: Application minor category mappings (ID → Name)

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
- Application major category (by name or ID)

### Application Category Filtering
- **By Name**: Use Chinese names like "Web浏览", "即时通讯" for user-friendly filtering
- **By ID**: Still supports numeric IDs like "4", "3" for backward compatibility
- Automatic detection: numeric strings filter by ID, text strings filter by name
- Uses sub-queries to convert names to IDs internally for efficient filtering

All data service methods accept optional `filters` parameter. When modifying queries, ensure filtering is consistently applied.

## Chart Types and Analysis

The system provides these analytical views:
- **Traffic Analysis**: Upload/download distribution, duration patterns, top users
- **User Analysis**: Activity levels, consumption patterns, high-upload risk detection
- **Application Analysis**: Category-based usage and popularity metrics with human-readable names
- **Time Analysis**: Temporal patterns and trend monitoring

## Development Patterns

### Adding New Analysis
1. Add query method to `DataService` class with `filters` parameter
2. Add corresponding chart generation method if needed
3. Integrate into appropriate Streamlit tab
4. Update PDF generator to include new analysis

### Application Category Mapping
The system includes application category mapping tables:
- Use `get_app_category_major_name(id)` to get major category names
- Use `get_app_category_minor_name(id)` to get minor category names
- Use `get_app_categories_with_names()` for JOIN queries with category names
- Use `get_available_app_categories()` to get user-selectable category names
- Import new category data using `import_app_categories.py`
- Filtering by category name is now supported and recommended for user interfaces

### Application Analysis Display
The application analysis pages focus on upstream traffic analysis with comprehensive percentage visualization:
- **Traffic Focus**: Only analyzes upstream (upload) traffic, not total traffic
- **Percentage Calculation**: Shows each app's percentage of total upstream traffic in the filtered time period
- **Multi-Chart Display**: 
  - Bar chart with traffic values and percentage labels on each bar
  - Pie chart showing visual percentage distribution with "Others" category
  - User count analysis bar chart
- **Tables**: Show app names, upstream traffic (GB), percentage, and user count
- **Visual Enhancement**: Bar charts include data labels like "15430.6GB (32.5%)" above each bar
- **Filtering**: Users can filter by category names with dynamic percentage recalculation
- **Data Methods**: `get_app_major_analysis()`, `get_app_minor_analysis()`, and `create_app_traffic_pie_chart()` provide comprehensive analysis

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

## Date Formatting Considerations
- When handling date formats in the project, pay special attention to:
  - Consistent parsing of `stat_time` field across different components
  - Converting between timestamp and human-readable date formats
  - Handling timezone considerations in date-based queries and visualizations
  - Implementing robust date range filtering in `FilterConditions` class