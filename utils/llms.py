import sys
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import LoggerManager
load_dotenv()

logger = LoggerManager.get_logger()

MODEL_CONFIGS = {
    "qwen":{
        "base_url":os.getenv("DASHSCOPE_API_BASE_URL"),
        "api_key":os.getenv("DASHSCOPE_API_KEY"),
        "chat_model":"qwen3-max",
        "embedding_model":"text-embedding-v3"
    },
    "deepseek":{
        "base_url":os.getenv("DEEPSEEK_API_BASE"),
        "api_key":os.getenv("DEEPSEEK_API_KEY"),
        "chat_model":"deepseek-chat",
        "embedding_model":"deepseek-embedding"
    }
}

DEFAULT_LLM_TYPE = "qwen"
DEFAULT_TEMPERATURE = 0

class LLMInitializationError(Exception):
    """自定义异常类用于LLM初始化错误"""
    pass

def initialize_llm(llm_type:str = DEFAULT_LLM_TYPE) -> tuple[ChatOpenAI,OpenAIEmbeddings]:
    """初始化LLM"""
    try:
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"不支持LLM类型:{llm_type},可用的类型:{list(MODEL_CONFIGS.keys())}")
        config = MODEL_CONFIGS[llm_type]
        llm_chat = ChatOpenAI(
            base_url = config["base_url"],
            api_key = config["api_key"],
            model = config["chat_model"],
            temperature = DEFAULT_TEMPERATURE,
            timeout = 30,
            max_retries = 2 #最大重试次数
        )
        llm_embedding = OpenAIEmbeddings(
            base_url = config["base_url"],
            api_key = config["api_key"],
            model = config["embedding_model"]
        )
        logger.info(f"成功初始化{llm_type}LLM")
        return llm_chat,llm_embedding
    except ValueError as e:
        logger.error(f"LLM配置错误:{str(e)}")
        raise LLMInitializationError(f"LLM配置错误:{str(e)}")
    except Exception as e:
        logger.error(f"初始化LLM失败:{str(e)}")
        raise LLMInitializationError(f"初始化LLM失败:{str(e)}")
    
def get_llm(llm_type:str = DEFAULT_LLM_TYPE):
    """获取LLM实例的封装函数，提供默认值和错误处理"""
    try:
        return initialize_llm(llm_type)
    except LLMInitializationError as e:
        logger.warning(f"使用默认配置重试:{str(e)}")
        if llm_type != DEFAULT_LLM_TYPE:
            return initialize_llm(DEFAULT_LLM_TYPE)
        raise

if __name__ == "__main__":
    try:
        llm_openai,llm_embedding = get_llm("openai")
        llm_invalid = get_llm("invalid_type")
        llm_qwen = get_llm("qwen")
    except LLMInitializationError as e:
        logger.error(f"程序终止:{str(e)}")