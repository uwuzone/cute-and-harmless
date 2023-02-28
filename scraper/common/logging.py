import sys
from loguru import logger


logger.remove()
logging_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | '
    '(id:{extra[id]}, job:{extra[job]}, target:{extra[target]}) | '
    '<level>{message}</level>'
)
logger.configure(extra={'job': '', 'id': 'global', 'target': ''})
logger.add(sys.stderr, format=logging_format)
