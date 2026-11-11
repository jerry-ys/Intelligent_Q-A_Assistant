import os 
import sys
from dotenv import load_dotenv
from typing import Optional
from tavily import TavilyClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import LoggerManager
load_dotenv()

logger = LoggerManager.get_logger()
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    logger.error("TAVILY_API_keY环境变量为设置,Tavily搜索可能无法正常工作")

_client:Optional[TavilyClient] = None

def get_tavily_client() -> TavilyClient:
    """
    获取Tavily客户端单例实例
    """
    global _client
    if _client is None:
        if not TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY环境变量未设置,请先设置该环境变量")
        _client = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("Tavily客户端已初始化成功.")
    return _client

def tavily_search(query:str,max_results:int = 5) -> str:
    """
    使用Tavily执行网络搜索，返回格式化后的搜索结果。

    Args:
        query:搜索查询字符串
        max_results:最大返回结果数量，默认为5

    Returns:
        格式化后的搜索结果字符串，包含每个搜索结果的标题、URL和内容摘要。
        如果发生错误，则返回错误信息。
    """
    try:
        client = get_tavily_client()
        logger.info(f"执行Tavily搜索:{query}")
        response = client.search(query,max_results=max_results)
        results = response.get("results",[])
        if not results:
            return "未找到相关结果"
        formatted = []
        for i,res in enumerate(results,1):
            title = res.get("title","无标题")
            url = res.get("url","")
            content = res.get("content","").strip()
            if len(content) > 300:
                content = content[:300] + "..."
            formatted.append(f"{i}.{title}\n链接:{url}\n摘要:{content}\n\n")
        result_text = "\n\n".join(formatted)
        logger.info(f"Tavily搜索完成,共找到{len(results)}个结果")
        return result_text
    except Exception as e:
        error_msg = f"Tavily搜索发生错误,{str(e)}"
        logger.error(error_msg)
        return error_msg
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "小米手机的最新型号"
    print("测试Tavily搜索:")
    print(tavily_search(query,max_results=2))