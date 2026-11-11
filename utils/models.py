from dataclasses import dataclass

@dataclass
class Context:
    user_id:str

@dataclass
class ResponseFormat:
    answer:str
    tool_used:str | None = None
    legal_references:str | None = None
    search_results:str | None = None
    sql_results:str | None = None
    confidence:float | None = None