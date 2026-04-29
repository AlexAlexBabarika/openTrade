from fastapi import HTTPException
import logging
from abc import abstractmethod

logger = logging.getLogger(__name__)


class DBErrorHandler:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @abstractmethod
    def handle_db_error(self, exc: Exception, operation: str) -> HTTPException:
        pass
