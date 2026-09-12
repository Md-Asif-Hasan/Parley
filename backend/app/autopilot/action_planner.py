"""
Autopilot Action Planner & Intent Classifier for Parley.
Parses natural language meeting orders and chat requests into actionable execution blueprints.
"""
import re
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Canonical platform name map — normalizes regex-matched strings to correct branding
PLATFORM_NAMES: Dict[str, str] = {
    "twitter": "Twitter/X",
    "x": "Twitter/X",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "reddit": "Reddit",
    "threads": "Threads",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "slack": "Slack",
    "discord": "Discord",
}


def _normalize_platform(raw: str) -> str:
    """Return canonical platform name (e.g. 'twitter' → 'Twitter/X')."""
    return PLATFORM_NAMES.get(raw.strip().lower(), raw.strip().title())


ACTION_TRIGGERS = [
    # Social media
    r"\b(?:post|tweet|share|publish)\s+(?:this\s+)?(?:on|to)?\s*(twitter|x|linkedin|facebook|reddit|instagram|threads)\b",
    # Chat / Messaging
    r"\b(?:send|message|dm|text)\s+(?:a\s+)?(?:message\s+)?(?:to\s+)?([A-Za-z0-9_]+)\s+(?:on|via)\s+(whatsapp|telegram|slack|discord)\b",
    r"\b(?:send|shoot)\s+(?:a\s+)?(whatsapp|telegram|slack|discord)\s+(?:message\s+)?to\s+([A-Za-z0-9_]+)\b",
    # Email
    r"\b(?:send|draft|write|compose)\s+(?:an?\s+)?email\s+(?:to\s+)?([A-Za-z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[A-Z][a-z]+)?\b",
    # Calendar
    r"\b(?:schedule|book|create|set\s+up)\s+(?:a\s+)?(?:meeting|appointment|call|event)\b",
]


class ActionPlan:
    def __init__(
        self,
        action_type: str,
        platform: str,
        description: str,
        params: Dict[str, Any],
        requires_confirmation: bool = True
    ):
        self.action_type = action_type
        self.platform = platform
        self.description = description
        self.params = params
        self.requires_confirmation = requires_confirmation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "platform": self.platform,
            "description": self.description,
            "params": self.params,
            "requires_confirmation": self.requires_confirmation
        }


def classify_action_intent(text: str, image_base64: Optional[str] = None) -> Optional[ActionPlan]:
    """
    Rapid rule-based and regex intent classifier for meeting orders and chat prompts.
    """
    if not text:
        return None

    cleaned = text.strip()
    lowered = cleaned.lower()

    # 1. Social media post
    match_social = re.search(r"\b(?:post|tweet|share|publish|upload)\b.*?\b(?:on|to)?\s*(twitter|x|linkedin|facebook|reddit|instagram|threads)\b", lowered)
    if match_social:
        platform = _normalize_platform(match_social.group(1))
        # Extract content payload
        content = re.sub(r"^.*?(?:saying|caption|with\s+(?:the\s+)?text|content)?\s*[:\"']?", "", cleaned, flags=re.IGNORECASE).strip(" \"'")
        if not content or len(content) < 3:
            content = "Sharing update from Parley Meeting."

        return ActionPlan(
            action_type="social_post",
            platform=platform,
            description=f"Publish post to {platform}",
            params={"platform": platform, "text": content, "has_image": bool(image_base64)},
            requires_confirmation=True
        )

    # 2. WhatsApp / Telegram message
    match_msg1 = re.search(r"\b(?:send|message|text)\s+(?:a\s+)?(?:message\s+)?(?:to\s+)?([A-Z][a-z]+|\+?\d+)\s+(?:on|via)\s+(whatsapp|telegram)\b", cleaned, re.IGNORECASE)
    match_msg2 = re.search(r"\b(?:send|shoot)\s+(?:a\s+)?(whatsapp|telegram)\s+(?:message\s+)?to\s+([A-Z][a-z]+|\+?\d+)\b", cleaned, re.IGNORECASE)
    
    if match_msg1 or match_msg2:
        contact = match_msg1.group(1) if match_msg1 else match_msg2.group(2)
        platform = _normalize_platform(match_msg1.group(2) if match_msg1 else match_msg2.group(1))
        return ActionPlan(
            action_type="chat_message",
            platform=platform,
            description=f"Send {platform} message to {contact}",
            params={"platform": platform, "contact": contact, "message": cleaned},
            requires_confirmation=True
        )

    # 3. Email
    match_email = re.search(r"\b(?:send|draft|compose)\s+(?:an?\s+)?email\s+(?:to\s+)?([A-Za-z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[A-Z][a-z]+)?\b", cleaned, re.IGNORECASE)
    if match_email:
        to = match_email.group(1) or "team"
        return ActionPlan(
            action_type="email",
            platform="Gmail/Email",
            description=f"Draft & send email to {to}",
            params={"to": to, "body": cleaned},
            requires_confirmation=True
        )

    # 4. Calendar Meeting
    if any(k in lowered for k in ["schedule meeting", "book appointment", "calendar invite", "set up call"]):
        return ActionPlan(
            action_type="calendar",
            platform="Google Calendar",
            description="Schedule meeting on calendar",
            params={"title": "Team Follow-up", "description": cleaned},
            requires_confirmation=True
        )

    return None
