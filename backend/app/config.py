from pydantic_settings import BaseSettings,SettingsConfigDict
from pathlib import Path

"""Base_DIR = backend 目录。用 resolve() 是为了把相对路径变成绝对路径，保证从任何地方运行都找得到。"""
Base_DIR = Path(__file__).resolve().parent.parent  
class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str 
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"


    model_config = SettingsConfigDict(env_file=Base_DIR / ".env", env_file_encoding="utf-8")

settings = Settings()

UPLOAD_DIR = Base_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True,exist_ok=True) #自动生成文件夹
MAX_FILE_SIZE = 100 * 1024 * 1024 #100M

ALLOW_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
}
