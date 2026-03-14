"""
Tools: list_policies, get_policy, update_policy
Manage the policy_information table in PostgreSQL.

Errors are raised as-is so they propagate back to Slack.
"""
import os
import psycopg2
from strands import tool


def _get_conn():
    print("[policy] Connecting to PostgreSQL…")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    print("[policy] Connection established")
    return conn


@tool
def list_policies() -> str:
    """
    Return all available policy names from the policy_information table.

    Use this when the user says things like:
      - "list policies"
      - "what policies do you have?"
      - "show me all policies"

    Returns:
        A numbered list of policy names the user can pick from.
    """
    print("[policy] list_policies called")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT policy_name FROM policy_information ORDER BY policy_name")
            rows = cur.fetchall()

    print(f"[policy] Found {len(rows)} policies")
    names = [r[0] for r in rows]
    numbered = "\n".join(f"{i+1}. {name}" for i, name in enumerate(names))
    return f"Here are the available policies:\n{numbered}\n\nWhich one would you like to view or update?"


@tool
def get_policy(policy_name: str) -> str:
    """
    Fetch the description of a single policy by name.

    Use this when the user picks a policy from the list or asks about a specific policy.
    Examples:
      - "show me the reservations policy"
      - "what is the dress code?"
      - user picks "3" after listing → resolve to the 3rd policy name then call this

    Args:
        policy_name: The exact policy name (e.g. 'reservations', 'dress_code').

    Returns:
        The current description of the policy.
    """
    print(f"[policy] get_policy called — policy_name={policy_name!r}")
    policy_name = policy_name.strip().lower()

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT description FROM policy_information WHERE policy_name = %s",
                (policy_name,),
            )
            row = cur.fetchone()

    if not row:
        raise RuntimeError(
            f"No policy found with name '{policy_name}'. "
            "Use list_policies to see all available policy names."
        )

    print(f"[policy] Found policy: {policy_name!r}")
    return f"*{policy_name}* policy:\n{row[0]}\n\nWould you like to update this description?"


@tool
def update_policy(policy_name: str, new_description: str) -> str:
    """
    Update the description of an existing policy.

    Use this when the user provides a new description for a policy.
    Examples:
      - "update the dress_code policy to: Smart casual only, no shorts."
      - "change reservations to: Bookings accepted up to 60 days in advance."
      - user says "yes update it to <new text>" after viewing a policy

    Args:
        policy_name: The exact policy name to update (e.g. 'dress_code').
        new_description: The full new description text to save.

    Returns:
        A confirmation message showing what was updated.
    """
    print(f"[policy] update_policy called — policy_name={policy_name!r}")
    print(f"[policy] New description: {new_description!r}")
    policy_name = policy_name.strip().lower()

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE policy_information SET description = %s WHERE policy_name = %s",
                (new_description, policy_name),
            )
            print(f"[policy] Rows affected: {cur.rowcount}")
            if cur.rowcount == 0:
                raise RuntimeError(
                    f"No policy found with name '{policy_name}'. "
                    "Use list_policies to see all available policy names."
                )

    result = f"✅ Updated *{policy_name}* policy:\n{new_description}"
    print(f"[policy] Done — {result}")
    return result