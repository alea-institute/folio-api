#!/bin/bash
# FOLIO API Docker Compose runner script
# This script helps manage the FOLIO API Docker setup

# Process command line arguments
# MODE is the first argument (default: prod)
MODE=${1:-"prod"}
shift 2>/dev/null || true

# Default ports
export PORT=${PORT:-8000}
export WEB_PORT=${WEB_PORT:-80}

# Process additional options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --api-port=*|--port=*)
            export PORT="${1#*=}"
            ;;
        --web-port=*)
            export WEB_PORT="${1#*=}"
            ;;
        --api-port|--port)
            export PORT="$2"
            shift
            ;;
        --web-port)
            export WEB_PORT="$2"
            shift
            ;;
        *)
            echo -e "\033[31mUnknown parameter: $1\033[0m"
            exit 1
            ;;
    esac
    shift
done

# Display the ASCII logo
echo -e "\033[34m"
cat << "EOF"
  ______ _____ _      _____ _____ 
 |  ____|  __ \ |    |_   _/ ____|
 | |__  | |  | | |      | || |  __ 
 |  __| | |  | | |      | || | |_ |
 | |    | |__| | |____ _| || |__| |
 |_|    |_____/|______|_____\_____|  API
EOF
echo -e "\033[0m"

# Show port configuration
echo -e "API Port: \033[36m$PORT\033[0m"
echo -e "Web Port: \033[36m$WEB_PORT\033[0m"

# Make sure config.json exists
if [ ! -f "config.json" ]; then
    echo -e "\033[33mWarning:\033[0m config.json not found, creating from example file"
    cp config.json.example config.json
    echo -e "\033[33mPlease edit config.json to add your configuration\033[0m"
fi

# Create logs directory if it doesn't exist
mkdir -p logs/caddy

# Ensure run.sh is executable
chmod +x run.sh

case $MODE in
    "dev")
        echo -e "\033[36mStarting FOLIO API in development mode\033[0m"
        echo -e "\033[33mHot reloading enabled - code changes will restart the server\033[0m"
        echo -e "\033[33mPress Ctrl+C to stop\033[0m"
        
        # Check if .env file exists, if not, create from example
        if [ ! -f ".env" ] && [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "\033[33mCreated .env file from example\033[0m"
        fi
        
        # Run docker-compose with the dev configuration
        docker compose -f docker-compose.dev.yml up --build
        ;;
        
    "prod")
        echo -e "\033[36mStarting FOLIO API in production mode\033[0m"
        
        # Run docker-compose with the production configuration
        docker compose up -d --build
        
        echo -e "\033[32mFOLIO API is running in the background\033[0m"
        echo -e "To view logs: \033[33mdocker compose logs -f\033[0m"
        echo -e "To stop: \033[33m./run.sh stop\033[0m"
        ;;
        
    "stop")
        echo -e "\033[36mStopping FOLIO API\033[0m"
        
        # Stop all running containers
        docker compose down
        
        echo -e "\033[32mFOLIO API stopped\033[0m"
        ;;
        
    "logs")
        echo -e "\033[36mShowing FOLIO API logs\033[0m"
        echo -e "\033[33mPress Ctrl+C to exit logs view\033[0m"
        
        # Display logs
        docker compose logs -f
        ;;
        
    "restart")
        echo -e "\033[36mRestarting FOLIO API\033[0m"
        
        # Restart all containers
        docker compose restart
        
        echo -e "\033[32mFOLIO API restarted\033[0m"
        ;;
        
    "status")
        echo -e "\033[36mFOLIO API Status\033[0m"
        
        # Show container status
        docker compose ps
        ;;
        
    "clean")
        echo -e "\033[36mCleaning up FOLIO API containers and volumes\033[0m"
        
        # Stop and remove containers, networks, volumes
        docker compose down -v
        
        echo -e "\033[32mCleanup complete\033[0m"
        ;;
        
    *)
        echo -e "\033[31mUnknown mode: $MODE\033[0m"
        echo -e "Usage: ./run.sh [mode] [options]"
        echo -e "Available modes:"
        echo -e "  \033[33mprod\033[0m (default) - Run in production mode"
        echo -e "  \033[33mdev\033[0m - Run in development mode with hot reloading"
        echo -e "  \033[33mstop\033[0m - Stop all containers"
        echo -e "  \033[33mlogs\033[0m - View logs"
        echo -e "  \033[33mrestart\033[0m - Restart all containers"
        echo -e "  \033[33mstatus\033[0m - Show container status"
        echo -e "  \033[33mclean\033[0m - Stop and remove containers, networks, volumes"
        echo -e "\nOptions:"
        echo -e "  \033[33m--api-port=PORT\033[0m or \033[33m--port=PORT\033[0m - Set the API port (default: 8000)"
        echo -e "  \033[33m--web-port=PORT\033[0m - Set the web server port (default: 80)"
        echo -e "\nExamples:"
        echo -e "  ./run.sh prod --api-port=9000 --web-port=8080"
        echo -e "  ./run.sh dev --port=3000 --web-port=3080"
        exit 1
        ;;
esac

exit 0