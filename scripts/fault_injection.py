from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen


def post(base: str, path: str) -> dict:
    request = Request(base.rstrip("/") + path, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject a service failure into OpsPilot demo")
    parser.add_argument("service", nargs="?", default="nginx")
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    print(json.dumps(post(args.base, f"/api/services/{args.service}/stop"), ensure_ascii=False, indent=2))
    print(json.dumps(post(args.base, "/api/monitor/tick"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

