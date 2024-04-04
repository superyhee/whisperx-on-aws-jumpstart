import json
import boto3
import os
import logging
import whisperx_transcribe
from subprocess import call
from sqs_message_processor import SQSMessageProcessor
from bedrock_handler.summary_bedrock_handler import SummaryBedrockHandler
from dotenv import load_dotenv
load_dotenv()

class WhisperSQSMessageProcessor(SQSMessageProcessor): 
    def __init__(self, queue_url, max_number_of_messages=20, wait_time_seconds=10):
        super().__init__(queue_url, max_number_of_messages, wait_time_seconds)
        self.s3 = boto3.client('s3',region_name=self.region)
        self.bedrock_runtime = boto3.client(service_name='bedrock-runtime',region_name=self.region)
        self.audio_extensions = ['.wav', '.mp3', '.m4a']
        self.video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        
    def download_file(self, bucket_name, object_key):
        self.s3.download_file(bucket_name, object_key, f'/tmp/{object_key}')
        self.logger.info("Downloaded file from S3: s3://%s/%s",bucket_name,object_key)

    def convert_to_audio(self, video_file):
        self.logger.info("Converting the video_file %s to audio_file",video_file)
        audio_file = os.path.splitext(video_file)[0] + '.wav'
        call(['ffmpeg', '-i', video_file, '-vn', '-ar', '16000', '-ac', '1', '-f', 'wav', audio_file])
        self.logger.info(f"The audio file is : %s",audio_file)
    
    def get_tag_value(self, tags, key):
        value = tags.get(key)
        if value:
            return value
        else:
            return ""

    def llm_summary(self,transcription_text):
        llm = SummaryBedrockHandler(region=self.region,content=transcription_text)
        response_body = llm.invoke()
        self.logger.info("The summary info is : %s",response_body)
        return response_body

    def transcribe(self, audio_file, message_body,message_receipt_handle):
        self.logger.info(f"Transcribing the audio file : %s",audio_file)
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        visibility_timeout = int(file_size_mb * 5 * 10)  # 每MB文件10秒
        self.change_message_visibility(message_receipt_handle, visibility_timeout)

        # 执行transcribe操作
        model_size = self.get_tag_value(message_body.get('tags', {}),"model_size")
        if model_size == "":
            model_size = "medium"
        self.logger.info("Use the model size:{0}".format(model_size))
        transcription_text = whisperx_transcribe.transcribe(audio_file, model_size)
        self.logger.info("The transcription text:{0}".format(transcription_text))
        # 判断transcription是否为空，如果不为空，则将transcription内容以json文件的形式上传到S3中
        if transcription_text:
            bucket_name = message_body['bucket']
            object_key = message_body['key']
            transcription_key = f"{os.path.splitext(object_key)[0]}.json"
            self.s3.put_object(Body=json.dumps(transcription_text,ensure_ascii=False), Bucket=bucket_name, Key=transcription_key)
            self.logger.info("Uploaded transcription text to s3://%s/%s",bucket_name,transcription_key)

        # 判断message中的tags,如果tags中存在summary的tag，则调用llm_summary方法对transcription内容进行总结
        if 'summary' in message_body.get('tags', []):
            summary = self.llm_summary(transcription_text)
            summary_key = f"{os.path.splitext(object_key)[0]}.txt"
            self.s3.put_object(Body=summary.encode('utf-8'), Bucket=bucket_name, Key=summary_key)
            self.logger.info("Uploaded summary to s3://%s/%s",bucket_name,summary_key)
    
    # 实现抽象方法，处理业务逻辑
    def process_message(self, message):
        #1. get info from the message
        self.logger.info("Handle the message begin ...")
        message_body = json.loads(message['Body'])
        bucket_name = message_body['bucket']
        object_key = message_body['key']
        message_receipt_handle = message['ReceiptHandle']

        #2.download the file from s3
        self.download_file(bucket_name, object_key)

        #3.检查文件类型和文件大小
        file_extension = os.path.splitext(object_key)[1].lower()
        if file_extension in self.audio_extensions:
            self.transcribe(f'/tmp/{object_key}',message_body,message_receipt_handle)
        elif file_extension in self.video_extensions:
            self.convert_to_audio(f'/tmp/{object_key}')
            self.transcribe(f'/tmp/{os.path.splitext(object_key)[0]}.wav',message_body,message_receipt_handle)
        else:
            self.logger.info("Unsupported file type: %s",file_extension)
if __name__ == '__main__':
    # queue_url = sys.argv[1]
    queue_url = os.environ['SQS_QUEUE_URL']
    processor = WhisperSQSMessageProcessor(queue_url, max_number_of_messages=1, wait_time_seconds=20)
    processor.process()