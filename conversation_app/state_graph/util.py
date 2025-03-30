from ..logging import logger 

from typing import TypedDict, List, Annotated, Literal, Optional
from pydantic import BaseModel

class State(BaseModel):
    messages: List[str] = []
    solution: Optional[Literal["accepted", "rejected", "negotiating"]] = None
    sale: Optional[Literal[20, 30]] = None
    blogger_price: Optional[float] = None
    price: Optional[float] = None
    format: Optional[Literal["fix", "cpm"]] = None
    cpm: Optional[float] = None
    views: Optional[List[int]] = None
    fixprice: Optional[int] = None

    def init_state(self):
        return {
            "messages": [],
            "solution": None,
            "sale": None, 
            "blogger_price": None,
            "price": None,
            "format": None,
            "cpm": None,
            "views": None,
            "fixprice": None
        }

    async def add_message(self, text: str):
        self.messages.append(text)
        logger.info(f"Added message to context: {text}")
        logger.info(f"Now message context: {list(self.messages)}")
        return self

    async def get_average_price(self):
        return ((self.cpm * (((self.views[0] + self.views[-1]) / 2) + self.views[-1]) / 2) / 1000)

    async def get_min_price(self):
        return float(self.cpm * self.views[0]) / 1000
    