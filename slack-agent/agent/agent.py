#agent/agent.py
"""
Strands Agent — store operations assistant.

Model: Amazon Nova Pro via Amazon Bedrock (us-east-1)
Tools:
  - update_business_hours  → PostgreSQL business_hours table
  - mark_item_sold_out     → Square Catalog API
"""
from datetime import datetime, timedelta
from strands import Agent
from strands.models import BedrockModel
import re
from agent.tools.business_hours import update_business_hours, get_business_hours
from agent.tools.square_inventory import mark_item_sold_out, mark_item_back_in_stock
from agent.tools.policy import list_policies, get_policy, update_policy


def _build_system_prompt() -> str:
    today = datetime.now().strftime("%A").lower()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A").lower()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%A").lower()
    print(f"[agent] Building system prompt — today={today}, tomorrow={tomorrow}, yesterday={yesterday}")

    return f"""
You are a helpful store operations assistant integrated into Slack.
You help staff manage the store without logging into any dashboards.

TODAY is {today}. TOMORROW is {tomorrow}. YESTERDAY is {yesterday}.
The valid values for day_of_week are exactly:
  monday, tuesday, wednesday, thursday, friday, saturday, sunday

You have access to these tools:

1. update_business_hours — use this when someone says the store is open/closed
   for a particular day, or wants to change the opening or closing time.
   Examples:
     - "the store is closed today"
     - "change Friday open time to 8am"  → open_time="08:00"
     - "Saturday closes at 10pm"         → close_time="22:00"
     - "Sunday hours are 11am to 5pm"    → open_time="11:00", close_time="17:00"
   Always resolve today/tomorrow/yesterday to the correct day name.
   Always convert 12-hour times (9am, 9:30pm) to 24-hour HH:MM before calling.

2. get_business_hours — use this when someone asks about store hours.
   Examples:
     - "what are our hours?"
     - "are we open Saturday?"
     - "show me today's hours"
   Pass day_of_week to get a single day, or omit it to get the full week.
   Always resolve today/tomorrow/yesterday to the correct day name first.
   
3. mark_item_sold_out — use this when someone says an item ran out, is sold out,
   or is no longer available. Extract the SKU or item name from their message.

4. mark_item_back_in_stock — use this when someone says an item is back, restocked,
   or available again. Extract the SKU or item name from their message.

5. list_policies — use this when the user wants to see all available policies.

6. get_policy — use this when the user picks a specific policy to view. If the user
   picks a number (e.g. "3"), resolve it to the correct policy name by calling
   list_policies first, then get_policy with that name.

7. update_policy — use this when the user provides new text to replace a policy
   description. Always confirm the policy name and new text before updating.
   If the user says "update it to: <text>" after viewing a policy, use the last
   policy name from context.

Always confirm what action you took. Be concise — this is Slack, not an essay.
If you're unsure what the user wants, ask one short clarifying question.
"""


print("[agent] Initializing BedrockModel (Nova Pro)…")
model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    region_name="us-east-1",
)
print("[agent] BedrockModel ready")

# One agent instance per Slack user so conversation history is isolated
_agents: dict[str, Agent] = {}

def _strip_thinking(text: str) -> str:
    """Remove <thinking>...</thinking> blocks that Nova Pro emits."""
    return re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()

def _sanitize_messages(agent: Agent) -> None:
    """
    Bedrock requires messages to alternate user/assistant and start with a user.
    After a tool-use turn, Strands can leave the history ending on an assistant
    message with no following user turn, which corrupts the next request.
    Drop any leading non-user messages so the array always starts with 'user'.
    """
    messages = getattr(agent, "messages", None)
    if not messages:
        return

    removed = 0
    while messages and messages[0].get("role") != "user":
        messages.pop(0)
        removed += 1

    if removed:
        print(f"[agent] Sanitized {removed} leading non-user message(s) from history")


def _get_agent(user_id: str) -> Agent:
    if user_id not in _agents:
        print(f"[agent] Creating new agent for user={user_id}")
        _agents[user_id] = Agent(
            model=model,
            system_prompt=_build_system_prompt(),
            tools=[update_business_hours, get_business_hours, mark_item_sold_out, mark_item_back_in_stock, list_policies, get_policy, update_policy],
        )
    else:
        print(f"[agent] Reusing existing agent for user={user_id}")

    agent = _agents[user_id]
    _sanitize_messages(agent)
    return agent

print("[agent] Agent factory ready")

def handle_message(user_id: str, user_message: str) -> str:
    print(f"[agent] user={user_id} message={user_message!r}")
    try:
        response = _get_agent(user_id)(user_message)
        result = _strip_thinking(str(response))
    except Exception as e:
        if "conversation must start with a user message" in str(e).lower():
            print(f"[agent] History corrupt for user={user_id}, resetting and retrying")
            del _agents[user_id]
            response = _get_agent(user_id)(user_message)
            result = _strip_thinking(str(response))
        else:
            raise
    print(f"[agent] user={user_id} response={result!r}")
    return result