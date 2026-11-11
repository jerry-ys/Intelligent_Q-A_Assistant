import os

class Config:
    LOG_FILE = "logfile/app.log"
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE))
    MAX_BYTES = 5*1024*1024
    BACKUP_COUNT = 3
    LLM_TYPE = "qwen"
    MEMORY_DB_PATH = "memory/memory_db"
    SQL_AGENT_DB_PATH = "data/app.db"
    USER_UPLOAD_DIR = "user_data/uploads"
    USER_CHROMA_DIR = "user_data/chroma_user"
    for d in [USER_UPLOAD_DIR,USER_CHROMA_DIR]:
        if not os.path.exists(d):
            os.makedirs(d,exist_ok=True)