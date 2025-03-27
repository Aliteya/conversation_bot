from langchain_openai import ChatOpenAI
from .settings import settings

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.get_llm_key())