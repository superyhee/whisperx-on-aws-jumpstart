import abc
import boto3
import time
from urllib.parse import urlparse

class SQSMessageProcessor(abc.ABC):
    def __init__(self, queue_url,max_number_of_messages=1, wait_time_seconds=10):
        parsed_url = urlparse(queue_url)
        region = parsed_url.netloc.split('.')[1]
        self.sqs = boto3.client('sqs',region_name=region)
        self.queue_url = queue_url
        self.max_number_of_messages=max_number_of_messages
        self.wait_time_seconds=wait_time_seconds

    def process(self):
        while True:
            messages = self.receive_messages()
            if not messages:
                time.sleep(self.wait_time_seconds)

            for message in messages:
                try:
                    self.process_message(message)
                    self.delete_message(message)
                except Exception as e:
                    print(f"Error processing the message: {e}")

    def receive_messages(self):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=self.max_number_of_messages,  # 每次最多接收10条消息
            WaitTimeSeconds=self.wait_time_seconds  # 长轮询时间为10秒
        )
        return response.get('Messages', [])

    def delete_message(self, message):
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
    
    def change_message_visibility(self, message, visibility_timeout=300):
        """
        设置消息的可见性超时,防止消息在处理期间被其他消费者获取。
        :param message: 从SQS接收到的消息
        :param visibility_timeout: 消息的可见性超时时间(秒),默认为300秒(5分钟)
        """
        self.sqs.change_message_visibility_batch(
            QueueUrl=self.queue_url,
            Entries=[
                {
                    'Id': str(time.time()),
                    'ReceiptHandle': message['ReceiptHandle'],
                    'VisibilityTimeout': visibility_timeout
                }
            ]
        )

    @abc.abstractmethod
    def process_message(self, message):
        """
        处理消息的抽象方法,需要在子类中实现具体的处理逻辑。
        :param message: 从SQS接收到的消息
        """
        pass
