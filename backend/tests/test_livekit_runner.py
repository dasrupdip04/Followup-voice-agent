from app.livekit_agent.runner import LiveKitRunner


def test_runner_init_sdks():
    runner = LiveKitRunner()
    errors = runner.init_sdks()
    # errors may be non-empty in CI; ensure it returns a dict
    assert isinstance(errors, dict)


def test_runner_handle_transcript_no_sdks(monkeypatch):
    runner = LiveKitRunner()
    # monkeypatch GeminiService.generate_reply to return a simple dict
    class Dummy:
        def generate_reply(self, prompt_text: str):
            return {"text": "OK, thanks"}

    runner.gemini = Dummy()
    # avoid DB modifications in unit test by patching start_call_for_session/append_turn
    import app.livekit_agent.tools as tools
    monkeypatch.setattr(tools, "start_call_for_session", lambda customer_id: {"call_id": 999})
    monkeypatch.setattr(tools, "append_turn", lambda call_id, role, text: None)

    res = runner.handle_deepgram_final_transcript(session_room="r1", customer_id=1, transcript="I can't pay")
    assert "reply" in res
