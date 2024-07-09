import json
from bedrock_handler.bedrock_handler import BedrockHandler


class AuditBedrockHandler(BedrockHandler):
    def __init__(self,region,model_id="anthropic.claude-3-haiku-20240307-v1:0",max_tokens = 1000,content=""):
        super().__init__(region, model_id=model_id, max_tokens = 1000)
        self.content = content

    def prompt(self):
        system_prompt = """ 你是一个文本内容审核专家,你的任务是审查<audit_content>中给定的文本,并从以下<tags>标签列表中选择最合适的标签.
在审核过程中,请保持客观、中立的态度,不带任何个人偏见和主观判断。如果选择了2-6任一标签,请在标签后简要说明是谁的内容以及为什么不合规.
如果无法确定内容属性,请选择"无法判断"。请在审核结果前注明"审核结果:"
<tags>
1. 合规
2. 色情内容
3. 暴力内容 
4. 仇恨言论
5. 政治敏感
6. 争议观点
7. 无法判断
</tags>

以下是需要审核的内容:
<audit_content>
{speak_context}
</audit_content>

以下是示例输出格式:
<example>
审核结果: 合规
</example>
"""
        system_prompt = system_prompt.replace("speak_context",json.dumps(self.content))
        return system_prompt