from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,field_validator
from langchain_core.messages import HumanMessage
from logging_config import logger
from fastapi import Request
from fastapi.responses import JSONResponse

from agent import agent

app = FastAPI(title="Finance Tracker Agent")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"reply": "Something went wrong on our end. Please try again."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://finance-tracker-ui-iota.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("message cannot be empty")
        return v.strip()

    @field_validator("thread_id")
    @classmethod
    def thread_id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("thread_id cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    reply: str


def extract_answer_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(f"Incoming message on thread {request.thread_id}: {request.message}")

    config = {"configurable": {"thread_id": request.thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )

    final_message = result["messages"][-1]
    reply_text = extract_answer_text(final_message.content)

    logger.info(f"Reply on thread {request.thread_id}: {reply_text}")

    return ChatResponse(reply=reply_text)