from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from security_agent.agent import build_agent_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Security DeepAgent from CLI.")
    parser.add_argument("message", help="用户问题")
    parser.add_argument("--thread-id", default="cli-thread-1")
    parser.add_argument("--user-id", default="ops_001")
    args = parser.parse_args()

    service = build_agent_service()
    response = service.chat(args.message, thread_id=args.thread_id, user_id=args.user_id)
    print(response.answer)
    if response.needs_review:
        print(f"\n[需要人工确认] review_id={response.review_id}, risk_level={response.risk_level}")


if __name__ == "__main__":
    main()

