import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from .config import Config

class LoggerManager:
    """日志管理器类，提供统一的日志配置和获取接口"""
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    # 创建日志记录器
    def _setup_logger(self):
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = []
        handler = ConcurrentRotatingFileHandler(
            Config.LOG_FILE,
            maxBytes = Config.MAX_BYTES,
            backupCount = Config.BACKUP_COUNT
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self._logger.addHandler(handler)

    @property
    def logger(self):
        """获取日志记录器实例"""
        return self._logger
    
    @classmethod
    def get_logger(cls):
        """获取日志记录器实例"""
        instance = cls()
        return instance.logger