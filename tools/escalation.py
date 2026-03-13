# tools/escalation.py

import os
import httpx
import json
from mcp.server.fastmcp import FastMCP

def _post_to_slack(blocks: list, text: str) -> dict:
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}",
            "Content-Type": "application/json",
        },
        json={
            "channel": os.getenv("SLACK_ESCALATION_CHANNEL", "#manager-alerts"),
            "text": text,
            "blocks": blocks,
        },
        timeout=10.0,
    )
    return resp.json()


def _refund_blocks(
    contact_name: str,
    phone: str,
    order_number: str,
    reason: str,
    pos_provider: str,
) -> list:
    """Slack Block Kit message for refund escalations."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "💳 Refund Request", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Customer:*\n{contact_name}"},
                {"type": "mrkdwn", "text": f"*Phone:*\n{phone}"},
                {"type": "mrkdwn", "text": f"*Order #:*\n{order_number}"},
                {"type": "mrkdwn", "text": f"*POS:*\n{pos_provider}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Reason:*\n{reason}"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": "refund_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Issue Refund", "emoji": True},
                    "style": "primary",
                    "action_id": "issue_refund",
                    "value": json.dumps({
                        "order_number": order_number,
                        "contact_name": contact_name,
                        "phone": phone,
                        "pos_provider": pos_provider,
                    }),
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Issue refund?"},
                        "text": {"type": "plain_text", "text": f"This will refund order {order_number} via {pos_provider}."},
                        "confirm": {"type": "plain_text", "text": "Yes, refund"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
            ],
        },
    ]


def _general_blocks(contact_name: str, phone: str, issue: str, order_number: str | None) -> list:
    fields = [
        {"type": "mrkdwn", "text": f"*Customer:*\n{contact_name}"},
        {"type": "mrkdwn", "text": f"*Phone:*\n{phone}"},
    ]
    if order_number:
        fields.append({"type": "mrkdwn", "text": f"*Order #:*\n{order_number}"})

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔔 Customer Escalation", "emoji": True},
        },
        {"type": "section", "fields": fields},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Issue:*\n{issue}"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": "general_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✔ Mark Completed", "emoji": True},
                    "style": "primary",
                    "action_id": "mark_completed",
                    # ↓ all the details baked into the button right here
                    "value": json.dumps({
                        "contact_name": contact_name,
                        "phone": phone,
                        "issue": issue,
                        "order_number": order_number or "N/A",
                    }),
                },
            ],
        },
    ]

def register(mcp: FastMCP):

    @mcp.tool()
    def escalate_to_manager(
        contact_name: str,
        phone: str,
        issue: str,
        escalation_type: str = "general",
        order_number: str = "",
        pos_provider: str = "",
    ) -> dict:
        """
        Escalate an unresolvable customer issue to the restaurant manager via Slack.

        Use this tool when:
        - The customer asks something you cannot answer
        - The customer has a complaint or problem
        - The customer requests a refund
        - Any situation requiring human intervention

        Always collect contact_name and phone first.
        For order-related issues, also collect order_number.
        For refunds, also collect pos_provider (e.g. 'square' or 'clover').

        Args:
            contact_name:    Customer's full name
            phone:           Customer's phone number
            issue:           Brief description of the issue or question
            escalation_type: 'refund' or 'general' (default: 'general')
            order_number:    Order ID if applicable (required for refunds)
            pos_provider:    POS system: 'square' or 'clover' (required for refunds)
        """
        if not os.getenv("SLACK_BOT_TOKEN"):
            return {"success": False, "error": "SLACK_BOT_TOKEN is not configured."}

        if escalation_type == "refund":
            if not order_number:
                return {"success": False, "error": "order_number is required for refund escalations."}
            blocks = _refund_blocks(contact_name, phone, order_number, issue, pos_provider)
            fallback_text = f"Refund request from {contact_name} ({phone}) — Order #{order_number}"
        else:
            blocks = _general_blocks(contact_name, phone, issue, order_number or None)
            fallback_text = f"Escalation from {contact_name} ({phone}): {issue}"

        result = _post_to_slack(blocks, fallback_text)

        if not result.get("ok"):
            return {"success": False, "error": result.get("error", "Slack API error")}

        return {
            "success": True,
            "message": "Your request has been escalated to our manager. They will follow up with you shortly.",
            "slack_ts": result.get("ts"),
        }