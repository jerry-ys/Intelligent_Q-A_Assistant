import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from utils.config import Config
from utils.logger import LoggerManager

logger = LoggerManager.get_logger()

def ensure_db_dir(db_path:str):
    """确保数据库文件所在目录存在"""
    dir_path = os.path.dirname(db_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path,exist_ok = True)
        logger.info(f"创建数据库目录：{dir_path}")

_sqlite_saver_instance = None

def get_sqlite_saver() -> SqliteSaver:
    """
    获取MemorySaver单例实例，连接到配置的MEMORY_DB_PATH。
    """
    global _sqlite_saver_instance
    if _sqlite_saver_instance is None:
        db_path = Config.MEMORY_DB_PATH
        ensure_db_dir(db_path)
        logger.info(f"初始化MemorySaver，数据库路径：{db_path}")
        conn = sqlite3.connect(db_path,check_same_thread = False)
        conn.execute("PRAGMA journal_mode = WAL;")
        serde = JsonPlusSerializer(allowed_json_modules="core")
        _sqlite_saver_instance = SqliteSaver(conn,serde = serde)
    return _sqlite_saver_instance

def clear_memory():
    """
    清空记忆数据库（用于测试或重置）。
    注意：这将删除所有检查点数据。
    """
    db_path = Config.MEMORY_DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.warning(f"已删除记忆数据库文件:{db_path}")
        global _sqlite_saver_instance
        _sqlite_saver_instance = None
    else:
        logger.info("记忆数据库文件不存在，无需清除。")

if __name__ == "__main__":
    saver = get_sqlite_saver()
    print("✅ SqliteSaver 初始化成功（已连接SQLite）")