from langchain_openai import ChatOpenAI

class LlamaConfig:
    BASE_URL = "https://openrouter.ai/api/v1"
    API_KEY = "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"
    MODEL = "meta-llama/llama-4-maverick:free"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.2
    
    @classmethod
    def get_chat(cls):
        return ChatOpenAI(
            base_url=cls.BASE_URL,
            api_key=cls.API_KEY,
            model=cls.MODEL,
            max_tokens=cls.MAX_TOKENS,
            temperature=cls.TEMPERATURE
        )

class Settings:
    LLM_PROVIDER = "llama"
    LLM = type('LLMConfig', (), {'LLAMA': LlamaConfig})

settings = Settings()