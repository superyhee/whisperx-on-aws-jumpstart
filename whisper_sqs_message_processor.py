import json
import boto3
import whisperx_transcribe
from subprocess import call
from sqs_message_processor import SQSMessageProcessor

class WhisperSQSMessageProcessor(SQSMessageProcessor):
    def __init__(self, queue_url, max_number_of_messages=20, wait_time_seconds=20):
        super().__init__(queue_url, max_number_of_messages, wait_time_seconds)
        self.s3 = boto3.client('s3')
        self.bedrock_runtime = boto3.client(service_name='bedrock-runtime')
        self.audio_extensions = ['.wav', '.mp3', '.m4a']
        self.video_extensions = ['.mp4', '.avi', '.mkv', '.mov']

    def download_file(self, bucket_name, object_key):
        self.s3.download_file(bucket_name, object_key, f'/tmp/{object_key}')
        print(f"Downloaded file from S3: s3://{bucket_name}/{object_key}")

    def convert_to_audio(self, video_file):
        audio_file = os.path.splitext(video_file)[0] + '.wav'
        call(['ffmpeg', '-i', video_file, '-vn', '-ar', '16000', '-ac', '1', '-f', 'wav', audio_file])
        print(f"Converted {video_file} to {audio_file}")
    
    def get_tag_value(self, tags, key):
        for tag in tags:
            if key in tag:
                return tag[key]
        return None

    def llm_summary(self,transcription_text):
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        system_prompt = """你是一个文案专员，请认真阅读其中的内容<transcription_text>标签中包含的上下文内容，并按照以下要求进行总结
        - 识别 <transcription_text> 中的语言种类，用相同语言进行总结和返回
        - 理解 <transcription_text> 中的主要情节和场景，用精简的语言总结内容
        - 如果 <transcription_text> 中有多个speaker，请分别总结每个人的情感情绪和想要表达的中心思想

        以下是上下文:
        <transcription_text>
        {speak_context}
        </transcription_text>
        """
        max_tokens = 1000
        messages = [{"role": "user", "content":""}]
        system_prompt = system_prompt.replace("speak_context",transcription_text)
        try:
            body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages
                })
            response = self.bedrock_runtime.invoke_model(body=body, modelId=model_id)
            response_body = json.loads(response.get('body').read())
            return response_body

        except ClientError as err:
            message=err.response["Error"]["Message"]
            print(message)

    def transcribe(self, audio_file, message_body):
        print(f"Transcribing {audio_file}")
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        visibility_timeout = int(file_size_mb * 5 * 60)  # 每MB文件5分钟
        self.change_message_visibility(message, visibility_timeout)

        # 执行transcribe操作
        model_size = "medium"
        size_from_tag = self.get_tag_value(message_body.get('tags', []),"model_size")
        if size_from_tag is Not None:
            model_size = size_from_tag
        transcription_text = whisperx_transcribe.transcribe(audio_file_mp3, model_size)

        # 判断transcription是否为空，如果不为空，则将transcription内容以json文件的形式上传到S3中
        if transcription_text:
            bucket_name = message_body['bucket']
            object_key = message_body['key']
            transcription_key = f"{os.path.splitext(object_key)[0]}.json"
            self.s3.put_object(Body=json.dumps(transcription_text).encode('utf-8'), Bucket=bucket_name, Key=transcription_key)
            print(f"Uploaded transcription text to s3://{bucket_name}/{transcription_key}")

        # 判断message中的tags,如果tags中存在Summery的tag，则调用llm_summary方法对transcription内容进行总结
        if 'Summary' in message_body.get('tags', []):
            summary = self.llm_summary(transcription_text)
            summary_key = f"{os.path.splitext(object_key)[0]}.txt"
            self.s3.put_object(Body=summary.encode('utf-8'), Bucket=bucket_name, Key=summary_key)
            print(f"Uploaded summary to s3://{bucket_name}/{summary_key}")
    
    # 实现抽象方法，处理业务逻辑
    def process_message(self, message):
        #1. get info from the message
        message_body = json.loads(message['Body'])
        bucket_name = message_body['bucket']
        object_key = message_body['key']

        #2.download the file from s3
        self.download_file(bucket_name, object_key)

        #3.检查文件类型和文件大小
        file_extension = os.path.splitext(object_key)[1].lower()
        if file_extension in self.audio_extensions:
            self.transcribe(f'/tmp/{object_key}',message_body)
        elif file_extension in self.video_extensions:
            self.convert_to_audio(f'/tmp/{object_key}')
            self.transcribe(f'/tmp/{os.path.splitext(object_key)[0]}.wav',message_body)
        else:
            print(f"Unsupported file type: {file_extension}")

if __name__ == '__main__':
    queue_url = 'https://sqs.us-west-2.amazonaws.com/091063646508/sqs-queue-whisper'
    processor = WhisperSQSMessageProcessor(queue_url, max_number_of_messages=1, wait_time_seconds=20)
    processor.process()