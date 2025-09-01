#!/bin/bash

# GitHub Actions Workflow Trigger Script
# This script triggers a GitHub Actions workflow using the GitHub API

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration - UPDATE THESE VALUES
GITHUB_USERNAME="tomisile"
REPO_NAME="atom"
WORKFLOW_ID="scrape_today.yml"  # or workflow ID number
BRANCH="main"

# Optional: Log file for tracking executions
LOG_FILE="${SCRIPT_DIR}/today_workflow_trigger.log"
MAX_LOG_SIZE=10485760  # 10MB in bytes

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to rotate log file if it gets too large
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        log_message "Log rotated - previous log saved as ${LOG_FILE}.old"
    fi
}

# Function to load environment variables from .env file
load_environment() {
    local env_loaded=false
    
    # Load from .env file in script directory
    if [[ -f "${SCRIPT_DIR}/.env" ]]; then
        set -a
        source <(grep -v '^#' "${SCRIPT_DIR}/.env" | grep -v '^$')
        set +a
        log_message "Loaded environment from ${SCRIPT_DIR}/.env"
        env_loaded=true
        fi
    
    if [[ "$env_loaded" == false ]]; then
        log_message "No .env file found. Using system environment variables."
    fi
}

# Function to validate and get GitHub token
get_github_token() {
    local token=""
    
    # Try different environment variable names
    if [[ -n "$GITHUB_TOKEN" ]]; then
        token="$GITHUB_TOKEN"
    fi
    
    # Validate token format
    if [[ -n "$token" ]]; then
        if [[ "$token" =~ ^gh[ps]_[A-Za-z0-9]{36,}$ ]]; then
            echo "$token"
            return 0
        else
            log_message "WARNING: Token format appears invalid. Expected format: ghp_* or ghs_*"
            echo "$token"
            return 0
        fi
    else
        log_message "ERROR: No GitHub token found in environment variables"
        log_message "Expected GITHUB_TOKEN"
        return 1
    fi
}

# Function to check if required tools are installed
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_message "ERROR: curl is not installed. Please install curl first."
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_message "WARNING: jq is not installed. JSON responses won't be pretty-printed."
    fi
}

# Function to validate configuration
validate_config() {
    # Load environment first
    load_environment
    
    # if [[ -z "$GITHUB_USERNAME" ]] || [[ "$GITHUB_USERNAME" == "tomisile" ]]; then
    #     log_message "ERROR: Please set GITHUB_USERNAME in the script or .env file"
    #     exit 1
    # fi
    
    # if [[ -z "$REPO_NAME" ]] || [[ "$REPO_NAME" == "atom" ]]; then
    #     log_message "ERROR: Please set REPO_NAME in the script or .env file"
    #     exit 1
    # fi
    
    # if [[ -z "$WORKFLOW_ID" ]] || [[ "$WORKFLOW_ID" == "scrape_today.yml" ]]; then
    #     log_message "ERROR: Please set WORKFLOW_ID in the script or .env file"
    #     exit 1
    # fi
    
    # Get and validate GitHub token
    if ! GITHUB_TOKEN=$(get_github_token); then
        exit 1
    fi
    
    log_message "Configuration validated successfully"
}

# Function to trigger the workflow
trigger_workflow() {
    local api_url="https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/actions/workflows/${WORKFLOW_ID}/dispatches"
    
    log_message "Triggering workflow: $WORKFLOW_ID on branch: $BRANCH"
    
    # Make the API request
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -X POST \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"ref\":\"$BRANCH\"}" \
        "$api_url")
    
    # Extract HTTP status and body
    http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    response_body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    # Check response
    if [[ "$http_status" == "204" ]]; then
        log_message "SUCCESS: Workflow triggered successfully"
        return 0
    else
        log_message "ERROR: Failed to trigger workflow. HTTP Status: $http_status"
        if [[ -n "$response_body" ]]; then
            if command -v jq &> /dev/null; then
                log_message "Response: $(echo "$response_body" | jq '.')"
            else
                log_message "Response: $response_body"
            fi
        fi
        return 1
    fi
}

# Function to check workflow status (optional)
check_workflow_status() {
    local runs_url="https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/actions/runs"
    
    response=$(curl -s \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token $GITHUB_TOKEN" \
        "$runs_url?per_page=5")
    
    if command -v jq &> /dev/null; then
        log_message "Recent workflow runs:"
        echo "$response" | jq -r '.workflow_runs[] | "\(.created_at) - \(.name) - \(.status) - \(.conclusion)"' | head -3 | while read line; do
            log_message "  $line"
        done
    fi
}

# Main execution
main() {
    # Rotate log if needed
    # rotate_log
    
    log_message "=== GitHub Workflow Trigger Started ==="
    
    # # Run checks
    # check_dependencies
    validate_config
    
    # Trigger the workflow
    if trigger_workflow; then
        log_message "Workflow trigger completed successfully"
        
        # Optionally check status (uncomment if needed)
        # check_workflow_status
    else
        log_message "Workflow trigger failed"
        exit 1
    fi
    
    log_message "=== GitHub Workflow Trigger Completed ==="
}

# Execute main function
main "$@"