import abc
import boto3
import time
import json
import logging
from urllib.parse import urlparse

class SQSMessageProcessor(abc.ABC):
    def __init__(self, queue_url,max_number_of_messages=1, wait_time_seconds=10):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # 创建一个文件处理器并设置日志级别
        file_handler = logging.FileHandler('whisper-access.log')
        file_handler.setLevel(logging.DEBUG)

         # 创建一个控制台处理器并设置日志级别
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建一个格式化器并将其添加到处理器中
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理器添加到 logger 中
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        parsed_url = urlparse(queue_url)
        self.region = parsed_url.netloc.split('.')[1]
        self.logger.info("region: %s",self.region)
        self.sqs = boto3.client('sqs',region_name=self.region)
        self.queue_url = queue_url
        self.max_number_of_messages=max_number_of_messages
        self.wait_time_seconds=wait_time_seconds

    def process(self):
        while True:
            messages = self.receive_messages()
            self.logger.debug("Get the message from sqs: %s",messages)
            if not messages:
                self.logger.info("message not found,waite %d",self.wait_time_seconds)
                time.sleep(self.wait_time_seconds)

            for message in messages:
                try:
                    self.logger.info("Get the message from sqs : %s",message)
                    self.process_message(message)
                    self.delete_message(message)
                except Exception as e:
                    self.logger.error("An error occurred when process : %s",e)
                    self.logger.info("The message will be added to dead letter exchange...")

    def receive_messages(self):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=self.max_number_of_messages,  # 每次最多接收10条消息
            WaitTimeSeconds=self.wait_time_seconds  # 长轮询时间为10秒
        )
        return response.get('Messages', [])

    def delete_message(self, message):
        self.logger.info("Delete the message,MessageId : %s",message['MessageId'])
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
    
    def change_message_visibility(self, message_receipt_handle, visibility_timeout=300):
        self.logger.info("Change visibility timeout to :%d",visibility_timeout)
        """
        设置消息的可见性超时,防止消息在处理期间被其他消费者获取。
        :param message: 从SQS接收到的消息
        :param visibility_timeout: 消息的可见性超时时间(秒),默认为300秒(5分钟)
        """
        self.sqs.change_message_visibility(
            QueueUrl=self.queue_url,
            ReceiptHandle=message_receipt_handle,
            VisibilityTimeout=visibility_timeout
        )

    @abc.abstractmethod
    def process_message(self, message):
        """
        处理消息的抽象方法,需要在子类中实现具体的处理逻辑。
        :param message: 从SQS接收到的消息
        """
        pass
