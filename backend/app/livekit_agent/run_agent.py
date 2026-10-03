"""CLI runner to start the LiveKitRunner.

Usage:
    python -m app.livekit_agent.run_agent
"""
import os
import logging
from app.livekit_agent.runner import LiveKitRunner

logging.basicConfig(level=logging.INFO)

def main():
    runner = LiveKitRunner()
    init_errors = runner.init_sdks()
    if init_errors:
        logging.warning("Provider SDKs/imports reported issues: %s", init_errors)
        # still exit non-zero to indicate limited functionality
    result = runner.start()
    logging.info("Runner result: %s", result)

if __name__ == '__main__':
    main()
