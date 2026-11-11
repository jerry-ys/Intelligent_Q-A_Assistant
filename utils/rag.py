import os 
import sys
import shutil
from pathlib import Path
from typing import List,Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import DashScopeEmbeddings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import LoggerManager
from utils.llms import MODEL_CONFIGS,DEFAULT_LLM_TYPE
from utils.DocParseKit import parse_file_to_documents

logger = LoggerManager.get_logger()
FOLDER_PATH = str(Path(__file__).parent.parent/"data")
CHROMA_PERSIST_DIR = Path(__file__).parent/"chroma_docs"
COLLECTION_NAME = "docs"
_vector_store:Optional[Chroma] = None

def get_embedding_model():
    """获取嵌入模型实例（使用DashScopeEmbeddings）"""
    config = MODEL_CONFIGS.get(DEFAULT_LLM_TYPE,MODEL_CONFIGS["qwen"])
    return DashScopeEmbeddings(
        model = config["embedding_model"],
        dashscope_api_key = config["api_key"]
    )

def load_and_split_documents() -> List[Document]:
    all_splits = []
    text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 50,
            chunk_overlap = 5,
            separators = ["\n","。","：","，"," "]
        )
    for filename in os.listdir(FOLDER_PATH):
        filepath = os.path.join(FOLDER_PATH, filename)
        documents = parse_file_to_documents(filepath)
        splits = text_splitter.split_documents(documents)
        all_splits.extend(splits)
    logger.info(f"数据加载完成，共{len(documents)}个原始文档，分割为{len(splits)}个块")
    return all_splits

def get_vector_store() -> Chroma:
    """获取或创建向量存储（惰性初始化），使用Chroma持久化"""
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    logger.info("正在初始化文本向量存储(Chroma)...")
    splits = load_and_split_documents()
    embedding_model = get_embedding_model()
    vector_store = Chroma.from_documents(
        documents = splits,
        embedding = embedding_model,
        persist_directory = str(CHROMA_PERSIST_DIR),
        collection_name = COLLECTION_NAME
    )
    _vector_store = vector_store
    logger.info("数据向量存储初始化完成，持久化目录:{CHROMA_PERSIST_DIR}")
    return vector_store

def retrieve_data(query:str,k:int = 3) -> List[Document]:
    """
    检查与查询相关的法律条文

    Args:
        query:查询字符串
        k:返回的文档数量

    Returns:
        相关法律条纹文档列表
    """
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(query,k)
    return docs

def format_docs(docs:list[Document]) -> str:
    """将文档列表格式化为字符串"""
    formatted = []
    for i,doc in enumerate(docs,1):
        content = doc.page_content.strip()
        formatted.append(f"{i}.{content}")
    return "\n\n".join(formatted)

def rag_query(query:str,k:int = 3) -> str:
    """
    RAG文本数据查询入口函数
    Args:
        query:用户查询
    Returns:
        检索到的文本内容，如果无结果则返回提示
    """
    try:
        docs = retrieve_data(query,k)
        if not docs:
            return "未找到相关数据"
        return format_docs(docs)
    except Exception as e:
        logger.error(f"相关数据查询失败:{e}")
        return f"数据检索时发生错误:{str(e)}"
    
def clear_vector_store():
    """清理旧的向量数据库（删除持久化文件夹）"""
    if CHROMA_PERSIST_DIR.exists():
        shutil.rmtree(CHROMA_PERSIST_DIR)
        logger.info(f"✅ 旧向量数据库已成功清理：{CHROMA_PERSIST_DIR}")
    else:
        logger.info(f"ℹ️ 未找到旧的向量数据库文件夹，无需清理。")
    
if __name__ == "__main__":
    test_query = "什么是家庭暴力？"
    clear_vector_store()
    print(f"测试查询:{test_query}")
    result = rag_query(test_query)
    print(f"检索结果:\n{result}")