import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

from tools import add_expense, query_expenses, budget_summary, weekly_limit_check

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)

tools = [add_expense, query_expenses, budget_summary, weekly_limit_check]

DATABASE_URL = os.getenv("DATABASE_URL")


checkpointer_cm = PostgresSaver.from_conn_string(DATABASE_URL)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()

SYSTEM_PROMPT = """
You are a personal finance tracking assistant.
You help the user log expenses, look up past spending, get budget summaries,
and check how much of their weekly budget remains.

Today's date is used for anything the user refers to as 'today', 'yesterday', or 'this week'.
Always confirm the category and amount back to the user after logging an expense.
If the user gives an amount without a category, ask which category it belongs to
rather than guessing.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)