#!/usr/bin/env python3
import argparse, asyncio, json, os, shutil, sys, time
from pathlib import Path

def _abs(p: str) -> Path: return Path(p).expanduser().resolve()

def build_cmd(alr_mode: str):
    if alr_mode == "yes" and shutil.which("alr"):
        return ["alr", "exec", "--", "ada_language_server", "--stdio"]
    # fallback chain
    return ["ada_language_server", "--stdio"] if shutil.which("ada_language_server") else ["ada_language_server"]

async def send(writer, method, params=None, id=None):
    msg = {"jsonrpc":"2.0","method":method}
    if params is not None: msg["params"]=params
    if id is not None: msg["id"]=id
    data = json.dumps(msg).encode("utf-8")
    writer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")+data)
    await writer.drain()

async def read_msg(reader):
    # minimal header parser
    length = None
    while True:
        line = await reader.readline()
        if not line: return None
        s = line.decode("ascii").strip()
        if s.lower().startswith("content-length:"):
            length = int(s.split(":")[1].strip())
        if s == "":
            break
    body = await reader.readexactly(length)
    return json.loads(body)

async def probe(project_gpr: Path, file: Path|None, init_timeout: float, hover_timeout: float, format_timeout: float, alr_mode: str):
    cmd = build_cmd(alr_mode)
    
    # Find cwd for alr mode
    cwd = None
    if alr_mode == "yes" and shutil.which("alr"):
        # Look for alire workspace
        for p in [project_gpr.parent] + list(project_gpr.parent.parents):
            if (p / "alire.toml").exists() or (p / "alire.lock").exists():
                cwd = str(p)
                break
    
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd)
    r = proc.stdout
    w = proc.stdin

    # initialize
    root_uri = project_gpr.parent.as_uri()
    init_params = {
        "processId": None,
        "rootUri": root_uri,
        "capabilities": {},
        "initializationOptions": {"ada": {"projectFile": str(project_gpr)}}
    }
    await send(w, "initialize", init_params, id=1)
    try:
        resp = await asyncio.wait_for(read_msg(r), timeout=init_timeout)
    except asyncio.TimeoutError:
        print(f"[init] TIMEOUT after {init_timeout}s")
        proc.terminate(); return 2
    if not resp or "result" not in resp:
        print(f"[init] unexpected: {resp}"); proc.terminate(); return 2

    await send(w, "initialized", {})
    print("[init] ok")

    # optional file ops
    if file:
        uri = file.as_uri()
        await send(w, "textDocument/didOpen", {"textDocument":{"uri":uri,"languageId":"ada","version":1,"text":file.read_text(encoding='utf-8')}})
        print("[didOpen] sent")

        # hover
        await send(w, "textDocument/hover", {"textDocument":{"uri":uri},"position":{"line":0,"character":0}}, id=2)
        try:
            hv = await asyncio.wait_for(read_msg(r), timeout=hover_timeout)
            print("[hover] ok" if hv and "result" in hv else f"[hover] unexpected: {hv}")
        except asyncio.TimeoutError:
            print(f"[hover] TIMEOUT after {hover_timeout}s")

        # formatting
        await send(w, "textDocument/formatting", {"textDocument":{"uri":uri},"options":{"tabSize":3,"insertSpaces":True}}, id=3)
        try:
            fmt = await asyncio.wait_for(read_msg(r), timeout=format_timeout)
            print("[formatting] ok" if fmt and "result" in fmt else f"[formatting] unexpected: {fmt}")
        except asyncio.TimeoutError:
            print(f"[formatting] TIMEOUT after {format_timeout}s")

        await send(w, "textDocument/didClose", {"textDocument":{"uri":uri}})

    await send(w, "shutdown", id=99); await read_msg(r)
    await send(w, "exit")
    proc.terminate()
    return 0

if __name__=="__main__":
    ap = argparse.ArgumentParser(description="ALS stdio probe (raw LSP)")
    ap.add_argument("--project-path", required=True)
    ap.add_argument("--file")
    ap.add_argument("--alr-mode", choices=("auto","yes","no"), default="yes")
    ap.add_argument("--init-timeout", type=float, default=180)
    ap.add_argument("--hover-timeout", type=float, default=30)
    ap.add_argument("--format-timeout", type=float, default=45)
    a = ap.parse_args()
    sys.exit(asyncio.run(probe(_abs(a.project_path), _abs(a.file) if a.file else None, a.init_timeout, a.hover_timeout, a.format_timeout, a.alr_mode)))