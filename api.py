from fastapi import FastAPI, HTTPException
import boto3

app = FastAPI()

# Create an S3 client
s3 = boto3.client('s3',region_name='us-east-1')

@app.get("/remote_link")
async def remote_link(url_link:str):
    #1. todo: download file and upload to s3
    response = {
        "status":200,
        "bucket":"",
        "key":""
    }
    return response

@app.get("/check_files")
async def check_files(file_path: str):
    # Parse the input file path
    bucket_name, key = file_path.replace("s3://", "").split("/", 1)

    # Define the file extensions to check
    extensions = [".json", ".txt"]

    # Create a list to store the existing file URLs
    result = {
        "status":200,
        "origin_file":file_path,
        "transcribe_file":"None",
        "transcribe_content":"None",
        "summary_file":"None",
        "summary_content":"None"
    }
    # Check if each file exists
    for ext in extensions:
        key_path,_ = key.split(".", -1)
        file_key = key_path+ext
        try:
            s3_object = s3.get_object(Bucket=bucket_name, Key=file_key)
            content = s3_object['Body'].read().decode('utf-8')
            if ext == ".json":
                result["transcribe_file"] = f"s3://{bucket_name}/{file_key}"
                result["transcribe_content"] = content
            elif ext == ".txt":
                result["summary_file"] = f"s3://{bucket_name}/{file_key}"
                result["summary_content"] = content
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist, continue to the next extension
                print("file not found")
            else:
                result["status"]=500
                result["error"]=str(e)
                return result

    # Return the list of existing file URLs
    return result