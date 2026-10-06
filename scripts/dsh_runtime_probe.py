"""Exercise the actual installed DSH handshake, without LLM calls or user-home changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def probe(installation, timeout=45):
    installation = Path(installation).resolve()
    asar = installation / "resources/app.asar"
    executable = installation / "DeepSeek Harness.exe"
    cli = asar / "dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
    if not asar.is_file() or not executable.is_file():
        raise ValueError("Installed DSH executable/archive absent")
    before = hashlib.sha256(asar.read_bytes()).hexdigest()
    env = {**os.environ, "ELECTRON_RUN_AS_NODE": "1",
           "DSH_HOME": str(ROOT / "research_data/dsh-probe-home")}
    # This diagnostic must not discover/use a live credential or make a paid call.
    for name in tuple(env):
        if name.endswith("API_KEY") or name in ("GH_TOKEN", "GITHUB_TOKEN"):
            env.pop(name)
    proc = subprocess.Popen([str(executable), "--expose-internals", str(cli),
                             "--profile", "sdk-minimal", "--patch",
                             str(ROOT / "dsh/macro-readonly.patch.yml")],
                            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    frames = queue.Queue()
    errors = []

    def reader():
        for line in proc.stdout:
            try:
                frames.put(json.loads(line))
            except ValueError:
                frames.put({"invalid_frame": True})

    def stderr_reader():
        for line in proc.stderr:
            # Count only: diagnostic text can contain machine paths or credentials.
            errors.append(True)

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=stderr_reader, daemon=True).start()

    def request(identity, method, params):
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": identity,
                                    "method": method, "params": params}) + "\n")
        proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                frame = frames.get(timeout=min(1, max(.01, deadline-time.monotonic())))
            except queue.Empty:
                if proc.poll() is not None:
                    raise RuntimeError("DSH process exited before response")
                continue
            if frame.get("invalid_frame"):
                raise RuntimeError("DSH stdout is not pure JSON-RPC")
            if frame.get("id") == identity:
                return frame
        raise TimeoutError("DSH handshake timed out")

    try:
        init = request("probe-init", "initialize", {"cwd": str(ROOT),
                       "provider": "deepseek-official", "model": "deepseek-chat", "maxTokens": 256})
        # Preserve codes but never print provider-controlled error messages.
        result = {"handshake": "available" if "result" in init else "rejected",
                  "server_info": init.get("result", {}).get("serverInfo"),
                  "error_code": init.get("error", {}).get("code"),
                  "llm_requests": 0, "shell_tools_disabled": True,
                  "isolated_home": "research_data/dsh-probe-home"}
        shutdown = request("probe-stop", "shutdown", {})
        result["shutdown"] = "available" if "result" in shutdown else "rejected"
        proc.wait(timeout=10)
        result["exit_code"] = proc.returncode
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()
    result["diagnostic_lines"] = len(errors)
    result["installation_sha256"] = before
    result["installation_unchanged"] = hashlib.sha256(asar.read_bytes()).hexdigest() == before
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", default="F:/DSH")
    args = parser.parse_args()
    print(json.dumps(probe(args.installation), ensure_ascii=False))
