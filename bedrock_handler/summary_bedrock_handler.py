import json
from bedrock_handler.bedrock_handler import BedrockHandler

class SummaryBedrockHandler(BedrockHandler):
    def __init__(self,region,model_id="anthropic.claude-3-haiku-20240307-v1:0",max_tokens = 1000,content=""):
        super().__init__(region,model_id=model_id,max_tokens = 1000)
        self.content = content

    def prompt(self):
        system_prompt = """
你是一个文案专员，请认真阅读其中的内容<transcription_text>标签中包含的上下文内容，并按照以下要求进行总结
- 识别 <transcription_text> 中的语言种类，用相同语言进行总结和返回
- 理解 <transcription_text> 中的主要情节和场景，用精简的语言总结内容
- 如果 <transcription_text> 中有多个speaker，请分别总结每个人的情感情绪和想要表达的中心思想

以下是上下文:
<transcription_text>
{speak_context}
</transcription_text>
"""
        system_prompt = system_prompt.replace("speak_context",json.dumps(self.content))
        return system_prompt