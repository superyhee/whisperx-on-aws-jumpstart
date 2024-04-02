#!/bin/bash

# Switch to the project directory
cd /home/ubuntu/whisper/ || exit

# Install requirements
pip3 install -r requirements.txt

# Function to read a variable from the .env file
read_env_var() {
    local var_name=$1
    local var_value=$(cat .env | grep "^${var_name}=" | awk -F'=' '{print $2}')
    echo "$var_value"
}

# Start the API server if enabled
start_api_server() {
    local start_api=$(read_env_var "LAUNCH_API")
    if [ "$start_api" = "True" ]; then
        echo "Starting the API server"
        nohup uvicorn api:app --host 0.0.0.0 --reload &>/dev/null &
    fi
}

# Start the Streamlit demo if enabled
start_demo() {
    local start_demo=$(read_env_var "LAUNCH_DEMO")
    if [ "$start_demo" = "True" ]; then
        echo "Starting the Streamlit demo"
        nohup streamlit run ui.py --server.headless=true --server.port=8501 --browser.serverAddress=0.0.0.0 &>/dev/null &
    fi
}

# Start the event workflow if enabled
start_event_workflow() {
    local start_event=$(read_env_var "LAUNCH_EVENT")
    if [ "$start_event" = "True" ]; then
        echo "Starting the event workflow"
        nohup python3 whisper_sqs_message_processor.py &>/dev/null &
    fi
}

# Start the required services
start_api_server
start_demo
start_event_workflow