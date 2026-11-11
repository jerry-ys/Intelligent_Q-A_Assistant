import os
import sys
from typing import List,Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import LoggerManager
from utils.DocParseKit import parse_file_to_documents
from utils.config import Config
from utils.rag import get_embedding_model,format_docs

logger = LoggerManager.get_logger()
USER_CHROMA_DIR = Config.USER_CHROMA_DIR
USER_COLLECTION_NAME = "user_docs"
_user_vector_store:Optional[Chroma] = None

def get_user_vector_store() -> Chroma:
    """获取或创建用户上传文档的向量存储（惰性初始化）"""
    global _user_vector_store
    if _user_vector_store is not None:
        return _user_vector_store
    
    logger.info("正在初始化用户上传文档向量存储...")
    embedding_model = get_embedding_model()
    
    # 确保目录存在
    os.makedirs(USER_CHROMA_DIR, exist_ok=True)
    
    try:
        # 尝试从持久化目录加载，如果失败则创建新的
        _user_vector_store = Chroma(
            embedding_function=embedding_model,
            persist_directory=str(USER_CHROMA_DIR),
            collection_name=USER_COLLECTION_NAME
        )
        logger.info(f"✅ 成功从 {USER_CHROMA_DIR} 加载用户向量库")
    except Exception as e:
        logger.warning(f"从 {USER_CHROMA_DIR} 加载用户向量库失败，将创建新的: {e}")
        _user_vector_store = Chroma(
            embedding_function=embedding_model,
            persist_directory=str(USER_CHROMA_DIR),
            collection_name=USER_COLLECTION_NAME
        )
        logger.info(f"✅ 新建用户向量库，持久化目录: {USER_CHROMA_DIR}")
    
    return _user_vector_store

def add_user_documents(file_paths: List[str]):
    """解析用户上传的文件并添加到专属向量库"""
    all_splits = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,
        chunk_overlap=5,
        separators=["\n", "。", "：", "，", " "]
    )
    
    for filepath in file_paths:
        try:
            documents = parse_file_to_documents(filepath)
            splits = text_splitter.split_documents(documents)
            all_splits.extend(splits)
            logger.info(f"用户文件 {filepath} 解析完成，分割为 {len(splits)} 个块")
        except Exception as e:
            logger.error(f"解析用户文件失败 {filepath}: {e}")
    
    if all_splits:
        vector_store = get_user_vector_store()
        if vector_store is None:
            logger.error("用户向量库初始化失败，无法添加文档。")
            return
            
        vector_store.add_documents(all_splits)
        logger.info(f"✅ 用户文档成功注入向量库，本次新增 {len(all_splits)} 个文本块")
    else:
        logger.warning("没有从上传文件中提取到任何可用的文本块。")

def user_rag_query(query: str, k: int = 3) -> str:
    """针对用户上传文件的 RAG 查询"""
    try:
        vector_store = get_user_vector_store()
        if vector_store is None:
            return "用户向量库初始化失败。"
            
        # 检查库中是否有数据
        if vector_store._collection.count() == 0:
            return "当前您尚未上传任何文件，或上传的文件内容为空。"
            
        docs = vector_store.similarity_search(query, k)
        if not docs:
            return "在您上传的文件中未找到与问题相关的内容。"
        return format_docs(docs)
    except Exception as e:
        logger.error(f"用户文件检索失败: {e}")
        return f"用户文件检索时发生错误: {str(e)}"