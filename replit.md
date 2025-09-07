# Idealista Land Watch & Rank

## Overview

This is a production-ready web application that automates property listing analysis from Idealista real estate emails. The system fetches property listings from Gmail twice daily, enriches the data using external APIs (Google Maps, Google Places, OSM), applies a multi-criteria scoring algorithm, and presents the results through a web interface with filtering, sorting, and export capabilities.

The application serves as a real estate investment analysis tool, helping users evaluate land properties based on infrastructure, transportation, environment, neighborhood quality, and legal status factors.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM for database operations
- **Application Factory Pattern**: Uses `create_app()` function for proper initialization
- **Blueprint Structure**: Separates routes into `main_routes` (web pages) and `api_routes` (REST endpoints)
- **Service Layer**: Modular services for Gmail integration, data enrichment, scoring, and scheduling
- **Configuration Management**: Centralized config class with environment variable support

### Frontend Architecture
- **Template Engine**: Jinja2 for server-side rendering
- **UI Framework**: Bootstrap with dark theme for responsive design
- **Progressive Enhancement**: HTMX for dynamic interactions without full page reloads
- **Vanilla JavaScript**: Custom scripts for table interactions, form handling, and UI enhancements

### Data Storage
- **Primary Database**: PostgreSQL with SQLAlchemy ORM
- **Schema Design**: Single `lands` table with JSONB fields for complex scoring data
- **Data Enrichment**: Structured storage for infrastructure, transport, environment, and neighborhood metrics
- **Flexible Scoring**: Separate criteria management for customizable scoring weights

### Authentication & Security
- **Gmail Integration**: OAuth2/API key authentication for email access
- **Environment Variables**: Secure storage of API keys and sensitive configuration
- **Input Validation**: SQLAlchemy model constraints and form validation
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

### Scheduling System
- **Background Scheduler**: APScheduler for automated email ingestion
- **Cron-like Jobs**: Twice-daily execution (7 AM and 7 PM CET)
- **Manual Triggers**: API endpoints for on-demand ingestion
- **Error Handling**: Comprehensive logging and graceful failure handling

### Scoring Algorithm
- **Multi-Criteria Decision Analysis**: Weighted scoring across 7 main categories
- **Configurable Weights**: Database-driven scoring criteria with admin interface
- **Real-time Calculation**: Automatic score updates when criteria weights change
- **Normalization**: Scores scaled to 0-100 range for consistent comparison

## External Dependencies

### Email Integration
- **Gmail API**: Fetches property listings from labeled emails
- **Google OAuth2**: Authentication for Gmail access
- **Email Parsing**: Custom regex-based parser for Idealista email formats

### Geospatial Services
- **Google Maps Geocoding API**: Converts addresses to coordinates
- **Google Places API**: Finds nearby amenities and services
- **OpenStreetMap Overpass API**: Infrastructure and transportation data
- **Distance Matrix API**: Travel time calculations to key locations

### Data Enrichment APIs
- **Google Places**: Restaurant ratings, school quality, nearby services
- **OSM Overpass**: Public transportation, utilities, environmental features
- **Geocoding Services**: Fallback geocoding when Google APIs unavailable

### Infrastructure Dependencies
- **PostgreSQL**: Primary database (Replit SQL)
- **APScheduler**: Background job scheduling
- **Flask-SQLAlchemy**: Database ORM and migrations
- **Bootstrap CDN**: Frontend styling and components
- **HTMX**: Dynamic frontend interactions
- **Font Awesome**: Icon library for UI elements

### Development & Testing
- **Pytest**: Comprehensive test suite with fixtures
- **Mock/Patch**: External API mocking for reliable testing
- **SQLite**: In-memory database for test isolation
- **Logging**: Structured logging throughout application layers