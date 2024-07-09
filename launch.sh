#!/bin/bash

# Switch to the project directory
cd /home/ubuntu/whisper/ || exit

# Install requirements
#pip3 install -r requirements.txt

add_notification_for_s3(){
   local bucket_name=$(read_env_var "BUCKET_NAME")
   local function_name=$(read_env_var "LAMBDA_NAME")
   local region=$(read_env_var "SQS_QUEUE_URL" | awk -F'.' '{print $2}')

   # 写一段脚本调用awscli命令，为bucket_name增加一个事件通知，当文件创建的时候触发 function_name
   # 获取 Lambda 函数的 ARN
    function_arn=$(aws lambda get-function --function-name "$function_name" --query 'Configuration.FunctionArn' --region $region --output text)

    # 创建事件通知配置
    notification_config=$(cat <<EOF
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "$function_arn",
      "Events": [
        "s3:ObjectCreated:*"
      ]
    }
  ]
}
EOF
)
    # 添加事件通知
    aws s3api put-bucket-notification-configuration \
        --bucket "$bucket_name" \
        --notification-configuration "$notification_config"
        
    echo "事件通知已添加到存储桶 $bucket_name，当创建新对象时将触发 Lambda 函数 $function_name"
}

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
        nohup uvicorn api:app --host 0.0.0.0 --port 9000 --reload &>/dev/null &
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
add_notification_for_s3
start_api_server
start_demo
start_event_workflow

wait