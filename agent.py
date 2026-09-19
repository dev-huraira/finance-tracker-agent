from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt
import os
from datetime import date
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
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


@dynamic_prompt
def build_prompt(request) -> str:
    today_str = date.today().isoformat()
    return f"""You are a personal finance tracking assistant.
You help the user log expenses, look up past spending, get budget summaries,
and check how much of their weekly budget remains.

Today's actual date is {today_str}. Use this exact date whenever the user says
'today', 'yesterday', or 'this week' — calculate relative to {today_str}, never guess.

Always confirm the category and amount back to the user after logging an expense.
If the user gives an amount without a category, ask which category it belongs to
rather than guessing.
"""


agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="You are a personal finance tracking assistant.",
    middleware=[build_prompt],
    checkpointer=checkpointer,
)