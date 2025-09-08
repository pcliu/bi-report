# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Business Intelligence (BI) reporting system** for network traffic analysis built with Python. The system reads CSV data files directly and provides interactive web dashboards and PDF reports for traffic analytics.

**Note**: This CSV branch reads data directly from CSV files in the local directory, replacing the original ClickHouse database dependency.

## Architecture

The system follows a 3-layer architecture:

1. **Data Service Layer** (`csv_data_service.py`): Centralized CSV data access using Repository pattern
   - `CSVDataService` class handles all CSV file reading and data processing
   - `FilterConditions` class manages multi-dimensional filtering (user, IP type, date range, app category)
   - All Plotly chart generation logic is contained here
   - Automatically discovers and loads CSV files from the specified directory

2. **Web Dashboard** (`streamlit_dashboard.py`): Interactive Streamlit-based web interface
   - Tab-based navigation: Overview, Traffic Analysis, User Analysis, App Analysis, Time Analysis
   - Real-time filtering controls in sidebar
   - Data overview page showing CSV file information
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
# Start web dashboard (reads CSV files from current directory)
streamlit run streamlit_dashboard.py

# Test CSV data service functionality  
python test_csv_service.py
```

### CSV File Requirements
Required CSV files in the current directory:
- **Main traffic data**: `tbl_statistic_userapp_day*.csv` (pattern matching supported)
  - Format: user_account,ip_type,app_category_major,app_category_minor,upstream_traffic,downstream_traffic,total_traffic,duration,stat_time
  - No header row required
- **Application categories**:
  - `app_catagory_major.csv`: Application major category mappings (ID,Name format)
  - `app_catagory_minor.csv`: Application minor category mappings (ID,Name format)

## Data Schema

The main CSV file contains network traffic records with these key fields:
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
- Uses pandas DataFrame filtering with name-to-ID mapping for efficient filtering

All data service methods accept optional `filters` parameter. The CSV service applies filters using pandas DataFrame operations for optimal performance.

## Chart Types and Analysis

The system provides these analytical views:
- **Traffic Analysis**: Upload/download distribution, duration patterns, top users
- **User Analysis**: Activity levels, consumption patterns, high-upload risk detection
- **Application Analysis**: Category-based usage and popularity metrics with human-readable names
- **Time Analysis**: Temporal patterns and trend monitoring

## Development Patterns

### Adding New Analysis
1. Add query method to `CSVDataService` class with `filters` parameter
2. Add corresponding chart generation method if needed
3. Integrate into appropriate Streamlit tab
4. Update PDF generator to include new analysis

### Application Category Mapping
The CSV service automatically loads application category mappings from CSV files:
- Category names are loaded from `app_catagory_major.csv` and `app_catagory_minor.csv`
- Use `get_available_app_categories()` to get user-selectable category names  
- Filtering by category name is supported and recommended for user interfaces
- Automatic fallback to ID-based names when mapping files are unavailable

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
- Charts are generated in `CSVDataService` for reuse between web and PDF
- Color schemes are predefined for professional appearance
- Error handling returns `None` for graceful degradation

### Filtering Integration
When adding new features:
- Accept `FilterConditions` parameter in data methods
- Use `filters.apply_to_dataframe()` to apply filters to pandas DataFrames
- Update PDF generation to pass filters through
- Ensure Streamlit controls create proper `FilterConditions` objects

## File Organization

- `streamlit_dashboard.py`: Main web application entry point
- `csv_data_service.py`: Core CSV data access and chart generation
- `pdf_generator.py`: Report generation with ReportLab
- `test_csv_service.py`: Test script for validating CSV service functionality
- Legacy files (for reference only):
  - `data_service.py`: Original ClickHouse-based data service
  - `import_csv_to_clickhouse.py`: Original data import utility

## CSV Data Operations

The system reads CSV files directly from the file system:
- Automatic file discovery using glob patterns
- Data validation and type conversion using pandas
- Lazy loading with caching for optimal performance
- Error handling provides meaningful feedback for missing or invalid files

The `CSVDataService` uses pandas DataFrame operations for all data processing and filtering.

## Memorized Commands

- Start dashboard: `source .venv/bin/activate && streamlit run streamlit_dashboard.py`
- Test CSV service: `source .venv/bin/activate && python test_csv_service.py`

## CSV Branch Deployment

This branch is designed for simplified local deployment:

1. **Requirements**:
   - Python virtual environment with dependencies installed (`uv sync`)
   - CSV files in the current directory (see CSV File Requirements above)

2. **Local Development**:
   ```bash
   # Activate environment and start dashboard
   source .venv/bin/activate
   streamlit run streamlit_dashboard.py
   ```

3. **Data Preparation**:
   - Place main traffic data CSV file with pattern `tbl_statistic_userapp_day*.csv`
   - Include application category mapping files: `app_catagory_major.csv`, `app_catagory_minor.csv`
   - No database setup required - reads directly from CSV files

4. **Benefits of CSV Approach**:
   - No database installation or configuration needed
   - Faster setup for development and testing
   - Easy data sharing via CSV files
   - Reduced system dependencies

**Note**: For production deployment with database backend, use the main branch with ClickHouse integration.

## Date Formatting Considerations
- When handling date formats in the project, pay special attention to:
  - Consistent parsing of `stat_time` field across different components
  - Converting between timestamp and human-readable date formats
  - Handling timezone considerations in date-based queries and visualizations
  - Implementing robust date range filtering in `FilterConditions` class