from pydantic_settings import BaseSettings, SettingsConfigDict
import os 

class Settings(BaseSettings):
    OPEN_AI_KEY: str
    BOT_TOKEN: str

    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env"), extra="ignore")

    def get_llm_key(self):
        return self.OPEN_AI_KEY

    def get_bot_token(self):
        return self.BOT_TOKEN
    
settings = Settings()