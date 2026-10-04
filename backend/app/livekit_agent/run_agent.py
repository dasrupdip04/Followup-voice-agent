"""Start the LiveKit Agents 1.8 voice worker.

Run from ``backend`` with the project virtualenv:
    ../.venv/bin/python -m app.livekit_agent.run_agent dev
"""

from dotenv import load_dotenv

load_dotenv()

from app.livekit_agent.runner import start


if __name__ == "__main__":
    start()
