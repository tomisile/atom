#!/bin/bash

# Python Script to Slack Notification
# Runs a Python script and sends output to Slack channel

# Configuration
PROJECT_DIR="/home/tomi/Projects/pred-bot"
PYTHON_SCRIPT="live.py"
PYTHON_ENV="tfenv"  # Your conda environment name
LOG_FILE="$HOME/Projects/pred-bot/live_local.log"
MAX_LOG_SIZE=10485760  # 10MB

# Get script directory for .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to rotate log file if too large
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        log_message "Log rotated - previous log saved as ${LOG_FILE}.old"
    fi
}

# Function to load environment variables from .env file
load_environment() {
    local env_loaded=false
    
    # Try loading from multiple locations
    for env_path in "${SCRIPT_DIR}/.env" "$HOME/.env" "$HOME/.config/slack-bot/.env"; do
        if [[ -f "$env_path" ]]; then
            set -a
            source <(grep -v '^#' "$env_path" | grep -v '^$')
            set +a
            log_message "Loaded environment variables from $env_path"
            env_loaded=true
            break
        fi
    done
    
    if [[ "$env_loaded" == false ]]; then
        log_message "No .env file found. Using system environment variables."
    fi
}

# Function to validate Slack configuration
validate_slack_config() {
    if [[ -z "$SLACK_BOT_TOKEN" ]]; then
        log_message "ERROR: SLACK_BOT_TOKEN not found in environment"
        exit 1
    fi
    
    if [[ -z "$SLACK_LIVE_CHANNEL_ID" ]]; then
        log_message "ERROR: SLACK_LIVE_CHANNEL_ID not found in environment"
        exit 1
    fi
    
    # Validate token format (Slack bot tokens start with xoxb-)
    if [[ ! "$SLACK_BOT_TOKEN" =~ ^xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+$ ]]; then
        log_message "WARNING: Slack token format appears invalid. Expected format: xoxb-*"
    fi
    
    log_message "Slack configuration validated"
}

# Function to check dependencies
check_dependencies() {
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        log_message "ERROR: curl is not installed"
        exit 1
    fi
    
    # Check if conda/python environment exists
    if command -v conda &> /dev/null; then
        if ! conda env list | grep -q "$PYTHON_ENV"; then
            log_message "WARNING: Conda environment '$PYTHON_ENV' not found"
            log_message "Available environments:"
            conda env list | while read line; do
                log_message "  $line"
            done
        fi
    fi
    
    # Check if Python script exists
    if [[ ! -f "$PROJECT_DIR/$PYTHON_SCRIPT" ]]; then
        log_message "ERROR: Python script not found at $PROJECT_DIR/$PYTHON_SCRIPT"
        exit 1
    fi
}

# Function to run Python script and capture output
run_python_script() {
    # log_message "Changing to project directory: $PROJECT_DIR"
    cd "$PROJECT_DIR" || {
        log_message "ERROR: Cannot change to directory $PROJECT_DIR"
        exit 1
    }
    
    # log_message "Running Python script: $PYTHON_SCRIPT"
    
    # Run the Python script with conda environment and capture both stdout and stderr
    if command -v conda &> /dev/null; then
        # Use conda environment
        output=$(conda run -n "$PYTHON_ENV" python "$PYTHON_SCRIPT" 2>&1)
        exit_code=$?
    else
        # Fallback to system python
        output=$(python3 "$PYTHON_SCRIPT" 2>&1)
        exit_code=$?
    fi
    
    # if [[ $exit_code -eq 0 ]]; then
    #     log_message "Python script executed successfully"
    # else
    #     log_message "Python script failed with exit code: $exit_code"
    # fi
    
    echo "$output"
    return $exit_code
}

# Function to escape JSON for Slack payload
escape_json() {
    local text="$1"
    # Escape backslashes, quotes, and newlines for JSON
    echo "$text" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g'
}

# Function to send message to Slack
send_to_slack() {
    local message="$1"
    local success="$2"
    
    # Determine message color based on success
    local color="good"
    local title=":bar_chart: Summary"
    local emoji=":computer:"
    
    if [[ "$success" == "false" ]]; then
        color="danger"
        title="Python Script Error"
        emoji=":x:"
    fi
    
    # Escape the message for JSON
    local escaped_message=$(escape_json "$message")
    
    # Create timestamp
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    # Build Slack payload using attachments for better formatting
    local payload=$(cat <<EOF
{
    "channel": "$SLACK_LIVE_CHANNEL_ID",
    "username": "aTom_local",
    "icon_emoji": "$emoji",
    "attachments": [
        {
            "color": "$color",
            "title": "$title",
            "text": "$escaped_message",
            "footer": "Executed from $(hostname)",
            "ts": $(date +%s)
        }
    ]
}
EOF
)
    
    log_message "Sending message to Slack channel: $SLACK_LIVE_CHANNEL_ID"
    
    # Send to Slack
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -X POST \
        -H "Content-type: application/json" \
        -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        -d "$payload" \
        "https://slack.com/api/chat.postMessage")
    
    # Extract HTTP status and body
    local http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local response_body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    # Check response
    if [[ "$http_status" == "200" ]]; then
        # Check if Slack API returned success
        if command -v jq &> /dev/null; then
            local slack_ok=$(echo "$response_body" | jq -r '.ok')
            if [[ "$slack_ok" == "true" ]]; then
                log_message "SUCCESS: Message sent to Slack"
                return 0
            else
                local error_msg=$(echo "$response_body" | jq -r '.error')
                log_message "ERROR: Slack API error: $error_msg"
                return 1
            fi
        else
            log_message "SUCCESS: Message sent to Slack (HTTP 200)"
            return 0
        fi
    else
        log_message "ERROR: HTTP request failed with status: $http_status"
        log_message "Response: $response_body"
        return 1
    fi
}

# Function to truncate long output
truncate_output() {
    local text="$1"
    local max_length="${2:-3000}"  # Slack has message limits
    
    if [[ ${#text} -gt $max_length ]]; then
        echo "${text:0:$max_length}... [Output truncated - ${#text} total characters]"
    else
        echo "$text"
    fi
}

# Main execution function
main() {
    rotate_log
    log_message "=== Python to Slack Script Started ==="
    
    # Load configuration
    load_environment
    validate_slack_config
    check_dependencies
    
    # Run the Python script and capture output
    python_output=$(run_python_script)
    python_exit_code=$?
    
    # Truncate output if too long
    truncated_output=$(truncate_output "$python_output" 3000)
    
    # Check if output contains 👀 emoji
    if [[ $python_output == *"👀"* ]]; then
        log_message "Output contains 👀 emoji, sending to Slack"
        # Send to Slack based on success/failure
        if [[ $python_exit_code -eq 0 ]]; then
            if send_to_slack "$truncated_output" "true"; then
                log_message "SUCCESS: Output sent to Slack successfully"
            else
                log_message "ERROR: Failed to send to Slack"
                exit 1
            fi
        else
            # Send error output to Slack
            error_msg="Python script failed with exit code $python_exit_code\n\nOutput:\n$truncated_output"
            if send_to_slack "$error_msg" "false"; then
                log_message "ERROR: Python script failed, but error sent to Slack"
            else
                log_message "ERROR: Python script failed AND failed to send to Slack"
            fi
            exit 1
        fi
    else
        log_message "Output does not contain 👀 emoji, skipping Slack notification"
    fi
    
    log_message "=== Python to Slack Script Completed ==="
}

# Execute main function
main "$@"