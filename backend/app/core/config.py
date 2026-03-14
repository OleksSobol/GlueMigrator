from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    itglue_base_url:str = "https://api.itglue.com"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
