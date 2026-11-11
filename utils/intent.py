import re
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llms import get_llm

# ======================
class RuleIntentRecognizer:
    def __init__(self):
        self.rules = {
            "knowledge_query": [
                "是什么", "定义", "概念", "解释", "原理", "含义",
                "特点", "作用", "怎么理解", "介绍一下", "详解",
                "简述", "阐述", "区别", "联系", "组成", "构成"
            ],
            "exercise_analysis": [
                "怎么做", "解题", "答案", "步骤", "这道题", "解法",
                "习题", "练习", "怎么算", "计算", "求解", "列式",
                "分析题目", "思路", "验算", "对错"
            ],
            "content_summary": [
                "总结", "重点", "归纳", "梳理", "考点", "概括",
                "提炼", "主要内容", "全文总结", "梳理要点",
                "精简", "汇总", "梗概", "核心内容", "回顾"
            ],
            "general_chat": [
                "你好", "在吗", "哈喽", "嗨", "谢谢", "再见", "拜拜",
                "你是谁", "能做什么", "有什么功能", "你能干什么",
                "聊聊天", "有空吗", "早上好", "下午好", "晚上好"
            ],
            "web_search": [
                "最新", "现在", "目前", "实时", "新闻", "资讯",
                "查一下", "搜索", "网上", "网络上", "今年", "今年最新",
                "行情", "热点", "事件", "现状", "外网资料"
            ]
        }

    def recognize(self, question):
        q = question.strip().lower()
        score = {
            "knowledge_query": 0,
            "exercise_analysis": 0,
            "content_summary": 0,
            "general_chat": 0,
            "web_search":0
        }
        for intent, keywords in self.rules.items():
            for kw in keywords:
                if re.search(kw, q):
                    score[intent] += 1

        best_intent = max(score, key=score.get)
        best_score = score[best_intent]
        confidence = min(best_score / 2, 1.0)

        if best_score == 0:
            return {
                "intent": "general_chat",
                "confidence": 0.0,
                "need_tool": False,
                "tool_type": "none"
            }
        if best_intent == "general_chat":
            need_tool = False
            tool_type = "none"
        elif best_intent == "web_search":
            need_tool = True
            tool_type = "web_search"
        else:
            need_tool = True
            tool_type = "rag"
        return {
            "intent": best_intent,
            "confidence": confidence,
            "need_tool": need_tool,
            "tool_type": tool_type
        }
    

rule_recognizer = RuleIntentRecognizer()

# ======================
llm, _ = get_llm()
prompt = ChatPromptTemplate.from_template("""
你是助手决策引擎，仅输出标准JSON，禁止额外回答、解释。

规则说明：
1. 工具选择规则
- 询问已上传文件、课程知识点、习题、内容总结 → 选用工具：rag
- 询问实时信息、外部常识、网络资讯、最新内容 → 选用工具：web_search
- 日常打招呼、闲聊、问候 → 不使用工具：none

2. 业务意图分类（四选一）
knowledge_query：知识点答疑
exercise_analysis：习题解析
content_summary：内容总结
general_chat：日常闲聊

输出字段要求：
- need_tool：布尔值，true=需要工具，false=不需要
- tool_type：字符串，可选值：rag / web_search / none
- intent：字符串，上面四类意图名称
- confidence：0~1之间小数

严格按格式输出JSON。
用户问题：{question}
""")

chain = prompt | llm | StrOutputParser()

def llm_intent(question):
    try:
        res = chain.invoke({"question": question})
        res = res.replace("```json", "").replace("```", "").strip()
        data = json.loads(res)
        data.setdefault("need_tool",False)
        data.setdefault("tool_type","none")
        data.setdefault("intent", "general_chat")
        data.setdefault("confidence", 0.5)
        return data
    except:
        return {
            "need_tool":False,
            "tool_type":"none",
            "intent":"general_chat",
            "confidence":0.5
        }

# ======================
THRESHOLD = 0.6

def get_intent(question):
    rule_result = rule_recognizer.recognize(question)
    if rule_result["confidence"] >= THRESHOLD:
        return rule_result
    return llm_intent(question)