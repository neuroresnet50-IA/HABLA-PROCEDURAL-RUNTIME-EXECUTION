from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


class DomSnapshot(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: dict[str, dict[str, Any]] = {}
        self.stack: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        element_id = attr_map.get("id")
        if element_id:
            self.elements[element_id] = {"tag": tag, "attrs": attr_map, "text": []}
        self.stack.append(element_id)

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        for element_id in self.stack:
            if element_id and element_id in self.elements:
                self.elements[element_id]["text"].append(data.strip())

    def attrs(self, element_id: str) -> dict[str, str]:
        element = self.elements.get(element_id) or {}
        return dict(element.get("attrs") or {})

    def text(self, element_id: str) -> str:
        element = self.elements.get(element_id) or {}
        return " ".join(element.get("text") or []).strip()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def find_browser() -> str:
    configured = os.environ.get("BROWSER")
    candidates = [configured] if configured else []
    candidates.extend(["google-chrome", "chromium", "chromium-browser"])
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if resolved:
            return resolved
    raise RuntimeError("No headless browser found. Install google-chrome or chromium to validate frontend render.")


@contextlib.contextmanager
def serve_directory(directory: Path):
    port = find_free_port()
    previous_cwd = Path.cwd()
    os.chdir(directory)
    server = ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        os.chdir(previous_cwd)


def run_chrome(url: str, screenshot_path: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    browser = find_browser()
    user_data_dir = Path(tempfile.mkdtemp(prefix="browser-render-smoke-"))
    command = [
        browser,
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1280,720",
        "--virtual-time-budget=8000",
        f"--user-data-dir={user_data_dir}",
        f"--screenshot={screenshot_path}",
        "--dump-dom",
        url,
    ]
    try:
        return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    finally:
        shutil.rmtree(user_data_dir, ignore_errors=True)


def parse_png_rgb(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Screenshot is not a PNG file")
    offset = 8
    width = height = bit_depth = color_type = None
    compressed = b""
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, _interlace = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            compressed += chunk_data
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or color_type not in {0, 2, 6}:
        raise RuntimeError("Unsupported PNG format for smoke analysis")
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    raw = zlib.decompress(compressed)
    stride = width * channels
    rows: list[bytearray] = []
    position = 0
    previous = bytearray(stride)
    for _y in range(height):
        filter_type = raw[position]
        position += 1
        row = bytearray(raw[position:position + stride])
        position += stride
        recon = bytearray(stride)
        for i, value in enumerate(row):
            left = recon[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = paeth(left, up, upper_left)
            else:
                raise RuntimeError(f"Unsupported PNG filter: {filter_type}")
            recon[i] = (value + predictor) & 0xFF
        rows.append(recon)
        previous = recon
    pixels: list[tuple[int, int, int]] = []
    for row in rows:
        for x in range(width):
            start = x * channels
            if color_type == 0:
                gray = row[start]
                pixels.append((gray, gray, gray))
            else:
                pixels.append((row[start], row[start + 1], row[start + 2]))
    return width, height, pixels


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def image_metrics(path: Path) -> dict[str, Any]:
    width, height, pixels = parse_png_rgb(path)
    total = len(pixels)
    non_dark = sum(1 for pixel in pixels if max(pixel) > 35)
    bright = sum(1 for pixel in pixels if max(pixel) > 80)
    central_pixels: list[tuple[int, int, int]] = []
    x0, x1 = int(width * 0.25), int(width * 0.75)
    y0, y1 = int(height * 0.20), int(height * 0.85)
    for y in range(y0, y1):
        row = y * width
        central_pixels.extend(pixels[row + x0:row + x1])
    central_total = max(1, len(central_pixels))
    central_non_dark = sum(1 for pixel in central_pixels if max(pixel) > 35)
    central_bright = sum(1 for pixel in central_pixels if max(pixel) > 80)
    means = [sum(pixel[index] for pixel in pixels) / total for index in range(3)]
    return {
        "width": width,
        "height": height,
        "mean_rgb": [round(value, 2) for value in means],
        "non_dark_ratio": round(non_dark / total, 4),
        "bright_ratio": round(bright / total, 4),
        "central_non_dark_ratio": round(central_non_dark / central_total, 4),
        "central_bright_ratio": round(central_bright / central_total, 4),
    }


def validate_dom(dom: str) -> tuple[dict[str, Any], list[str]]:
    parser = DomSnapshot()
    parser.feed(dom)
    blockers: list[str] = []
    canvas_attrs = parser.attrs("world")
    render_mode = canvas_attrs.get("data-render-mode") or ""
    distance_text = parser.text("distance-value")
    speed_text = parser.text("speed-value")
    event_text = parser.text("event-value")
    if "world" not in parser.elements:
        blockers.append("canvas #world was not found in rendered DOM")
    if "distance-value" not in parser.elements:
        blockers.append("HUD #distance-value was not found in rendered DOM")
    if "distancbbbb" in dom:
        blockers.append("corrupt distance id is still present")
    if render_mode not in {"webgl", "fallback-2d"}:
        blockers.append("canvas did not declare data-render-mode=webgl or fallback-2d")
    if event_text.startswith("error webgl") and render_mode != "fallback-2d":
        blockers.append("WebGL error was shown without fallback canvas")
    if not speed_text or speed_text == "0 m/s":
        blockers.append("HUD speed did not update from its initial value")
    if not distance_text:
        blockers.append("HUD distance text is empty")
    return {
        "render_mode": render_mode,
        "distance_text": distance_text,
        "speed_text": speed_text,
        "event_text": event_text,
    }, blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a frontend canvas render with a real browser.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--frontend", default="frontend")
    parser.add_argument("--mode", default="smoke")
    parser.add_argument("--light", default="day")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--min-central-non-dark", type=float, default=0.04)
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    frontend = (workspace / args.frontend).resolve()
    if not frontend.is_dir():
        print(json.dumps({"ok": False, "blockers": [f"Frontend directory not found: {frontend}"]}, indent=2))
        return 1

    artifacts = workspace / "runtime" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    screenshot = artifacts / "browser_render_smoke.png"
    report_path = artifacts / "browser_render_smoke.json"
    blockers: list[str] = []
    with serve_directory(frontend) as base_url:
        separator = "&" if "?" in base_url else "?"
        url = f"{base_url}{separator}mode={args.mode}&light={args.light}"
        completed = run_chrome(url, screenshot, args.timeout)
    if completed.returncode != 0:
        blockers.append(f"browser exited with return code {completed.returncode}")
    dom_info, dom_blockers = validate_dom(completed.stdout or "")
    blockers.extend(dom_blockers)
    metrics: dict[str, Any] = {}
    if screenshot.exists():
        try:
            metrics = image_metrics(screenshot)
            if metrics["central_non_dark_ratio"] < args.min_central_non_dark:
                blockers.append(
                    "screenshot central area is too dark: "
                    f"{metrics['central_non_dark_ratio']} < {args.min_central_non_dark}"
                )
        except Exception as error:
            blockers.append(f"screenshot analysis failed: {error}")
    else:
        blockers.append("browser did not write screenshot")

    stderr_lines = [line for line in (completed.stderr or "").splitlines() if line.strip()]
    report = {
        "ok": not blockers,
        "blockers": blockers,
        "dom": dom_info,
        "screenshot": str(screenshot),
        "metrics": metrics,
        "browser_stderr_tail": stderr_lines[-12:],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
