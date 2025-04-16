# Changelog

All notable changes to the FOLIO API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-04-16

### Added
- JavaScript linting configuration for improved code quality
- Double-click functionality to expand/collapse tree nodes

### Changed
- Enhanced search functionality in taxonomy tree to show all matching results
- Improved taxonomy tree filtering to reduce unnecessary API calls
- Fixed search bar interaction to prevent unintended taxonomy tree filtering
- Replaced print statements with proper logging in API initialization
- Removed console.log statements from JavaScript for production readiness
- Improved error handling in JavaScript with user-friendly error messages

### Fixed
- Issue with top search input affecting taxonomy tree search
- Performance issues when clearing tree filters
- Memory usage issues by reducing duplicate API calls

## [0.3.0] - 2025-04-15

### Added
- Footer version display showing FOLIO branch and repository information
- Expanded editorial information display in HTML templates

### Changed
- Replaced D3.js with Cytoscape.js for improved graph visualization
- Enhanced HTML templates with better responsive design and user interface
- Improved search functionality to handle case-insensitive substring matching
- Updated typeahead search to highlight matching text
- Improved graph interactivity with tooltips and better controls
- Expanded footer with additional resources and links
- Updated copyright years to include 2025

## [0.2.0] - 2025-03-23

### Added
- Top-level browsing endpoint for user convenience/demo
- Non-root user in Docker for better security
- Health check endpoint with detailed information
- Optional production rate limiting for API endpoints
- Port configuration via command-line options (--api-port, --web-port) and environment variables


### Changed
- Improved Docker Compose setup for easier deployment
- Improved API documentation with better OpenAPI tags
- Enhanced HTML templates with improved UI/UX
- Improved environment variable support for configuration
- Improved Dockerfile with layer optimization and proper caching
- Enhanced Caddy configuration with security headers
- Better error handling and response formatting
- Improved search functionality with case-insensitive matching

## [0.1.0] - 2025-02-15

### Added
- Initial release of the FOLIO API
- Basic search functionality
- Class retrieval in multiple formats (JSON, HTML, Markdown, XML)
- Taxonomy browsing
- Simple Docker container
- Basic Swagger documentation