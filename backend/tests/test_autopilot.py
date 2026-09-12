import pytest
from app.autopilot.voice_renamer import extract_speaker_rename
from app.autopilot.action_planner import classify_action_intent, ActionPlan
from app.autopilot.utils import save_base64_image


def test_voice_speaker_renamer_self_intro():
    # Test self-identification patterns
    res1 = extract_speaker_rename("Hi everyone, my name is Alex and I will lead today", "speaker_0")
    assert res1 == ("speaker_0", "Alex")

    res2 = extract_speaker_rename("I am Sarah from design", "speaker_1")
    assert res2 == ("speaker_1", "Sarah")

    res3 = extract_speaker_rename("This is John speaking", "speaker_2")
    assert res3 == ("speaker_2", "John")


def test_voice_speaker_renamer_target():
    # Test explicit target renames
    res1 = extract_speaker_rename("Speaker 1 is Bob", "speaker_0")
    assert res1 == ("speaker_1", "Bob")

    res2 = extract_speaker_rename("Please rename speaker 2 to Charlie", "speaker_0")
    assert res2 == ("speaker_2", "Charlie")


def test_action_intent_classifier_social():
    # Test social media intent detection
    plan = classify_action_intent("Can you please post this update to Twitter saying 'Parley v2 launched!'")
    assert plan is not None
    assert plan.action_type == "social_post"
    assert plan.platform == "Twitter/X"

    plan_linkedin = classify_action_intent("Post this meeting summary to LinkedIn")
    assert plan_linkedin is not None
    assert plan_linkedin.platform == "LinkedIn"


def test_action_intent_classifier_chat_message():
    # Test chat / whatsapp intent detection
    plan = classify_action_intent("Send a WhatsApp message to Alex saying we started the meeting")
    assert plan is not None
    assert plan.action_type == "chat_message"
    assert plan.params["contact"] == "Alex"
    assert plan.params["platform"] == "WhatsApp"


def test_save_base64_image(tmp_path):
    # Test base64 image saving
    import os
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    path = save_base64_image(tiny_png_b64, "png")
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0
