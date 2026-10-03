import os
from app.livekit_agent.agent import LiveKitAgent


def test_livekit_agent_smoke():
    agent = LiveKitAgent()
    result = agent.smoke_test()
    assert "gemini" in result
    assert "imports" in result
    # configuration flags should be present (may be False in CI)
    assert "livekit_configured" in result
    assert "deepgram_configured" in result
    assert "cartesia_configured" in result
