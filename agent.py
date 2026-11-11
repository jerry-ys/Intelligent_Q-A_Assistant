import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from utils.memory_sqlite import get_sqlite_saver
from utils.config import Config
from utils.llms import get_llm
from utils.models import Context,ResponseFormat
from utils.logger import LoggerManager
from utils.intent import get_intent
from utils.rag import rag_query
from utils.user_rag import user_rag_query
from utils.tavily_search import tavily_search

load_dotenv()
logger = LoggerManager.get_logger()
llm_chat,llm_embedding = get_llm(Config.LLM_TYPE)
SYSTEM_PROMPT = f"""
你是「高校课程智能问答助手」，专为大学生、专升本、考研学生打造，核心能力包括：课程答疑、考点梳理、习题解析、内容总结提炼。

---
### 核心回答规范
1.  **回答策略**：请优先基于用户提供的「参考资料」进行回答。如果参考资料信息不足，**你可以结合自身的通用知识进行补充和解答**，但需要在回答中说明哪些是基于资料的，哪些是基于通用知识的。
2.  语言专业易懂，条理清晰，避免无关内容。
3.  不同场景回答格式要求：
    - 【知识点答疑】：
        1.  核心定义：xxx
        2.  关键要点：
            - 要点1
            - 要点2
        3.  易混淆点：xxx
    - 【课后习题解析】：
        1.  解题步骤：
            - 步骤1：xxx
            - 步骤2：xxx
        2.  考点分析：xxx
        3.  易错提醒：xxx
    - 【考点梳理/内容总结】：
        1.  核心知识点：
            - 知识点1
            - 知识点2
        2.  重点难点：
            - 重点：xxx
            - 难点：xxx

4.  边界处理：
    - 仅当「参考资料」完全为空，且该问题属于极度冷门的特定课程内部资料时，再告知用户：“当前参考资料中未包含相关内容，请补充更多课程信息或上传课件后再提问。”
    - 不回答与学习无关的问题。

---
请结合用户提供的「参考资料」和问题，生成符合上述规范的回答。
"""
checkpointer = get_sqlite_saver()

agent = create_agent(
    model = llm_chat,
    system_prompt = SYSTEM_PROMPT,
    context_schema = Context,
    response_format = ToolStrategy(ResponseFormat),
    checkpointer = checkpointer
)

def run_conversation_api(question: str, thread_id: str = "1", user_id: str = "1", use_user_rag: bool = False):
    """
    正确版本：意图识别 → 调用工具 → 拼装prompt → 生成回答
    """
    intent_info = get_intent(question)
    intent = intent_info["intent"]
    need_tool = intent_info["need_tool"]
    tool_type = intent_info["tool_type"]
    context = ""
    if need_tool:
        if tool_type == "web_search":
            context = tavily_search(question)
        elif tool_type == "rag":
            if use_user_rag:
                logger.info("🔍 触发用户上传文件 RAG 检索")
                if intent == "knowledge_query":
                    context = user_rag_query(question, 3)
                elif intent == "exercise_analysis":
                    context = user_rag_query(question, 5)
                elif intent == "content_summary":
                    context = user_rag_query(question, 8)
                else:
                    context = user_rag_query(question, 3)
            else:
                # 走系统内置知识库检索
                if intent == "knowledge_query":
                    context = rag_query(question, 3)
                elif intent == "exercise_analysis":
                    context = rag_query(question, 5)
                elif intent == "content_summary":
                    context = rag_query(question, 8)
    content = f"参考资料：{context}\n用户问题：{question}"
    print(f"🔍 最终传给大模型的参考资料长度: {len(context)}")
    if len(context) < 10 and need_tool:
        print("⚠️ 警报：参考资料几乎为空！请检查 RAG 检索结果。")
    langgraph_thread_id = f"{user_id}___{thread_id}"
    config = {
        "configurable": {
            "thread_id": langgraph_thread_id  
        }
    }
    response = agent.invoke(
        {"messages":[{"role":"user","content":content}]},
        config = config,
        context = Context(user_id = user_id)
    )
    structured = response.get("structured_response")
    if structured:
        answer = structured.answer
    else:
        answer = response["messages"][-1].content
    return answer

if __name__ == "__main__":
    question = "你好"
    answer = run_conversation_api(question)
    print(answer)