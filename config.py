import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-3.5-turbo"

    # ChromaDB Configuration
    CHROMADB_API_KEY = os.getenv("CHROMADB_API_KEY")

    # Logging Configuration
    LOG_LEVEL_APP = os.getenv("LOG_LEVEL_APP", "DEBUG")
    LOG_LEVEL_DEPS = os.getenv("LOG_LEVEL_DEPS", "INFO")
    LOG_TO_STDOUT = os.getenv("LOG_TO_STDOUT", "true").lower() == "true"
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "app.log")
