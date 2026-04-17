"""
Generate demo screenshots and an animated GIF for the agentic-ai-platform README.

Requirements:
    pip install playwright pillow
    playwright install chromium

Run from repo root (server must be running on port 8000):
    python scripts/generate_demo_assets.py
"""
from __future__ import annotations

import time
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"
SCREENSHOTS_DIR = ASSETS_DIR / "screenshots"
DEMO_DIR = ASSETS_DIR / "demo"

BASE_URL = "http://localhost:8000"


def _ensure_dirs() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)


def _warm_up_server() -> None:
    """Fire a few requests so the dashboard and metrics pages have data."""
    import httpx

    prompts = [
        ("What is 128 * 256?", "demo-session"),
        ("Explain CQRS pattern", "demo-session"),
        ("What is the capital of Japan?", "demo-session"),
        ("latency budget for 3 services at 300ms each", "demo-session"),
    ]
    with httpx.Client(base_url=BASE_URL, timeout=10) as http:
        for prompt, sid in prompts:
            try:
                http.post("/v1/agent/run", json={"prompt": prompt, "session_id": sid})
            except Exception:
                pass
        time.sleep(0.5)


def take_screenshots() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # ── Swagger UI ──────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/docs", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "swagger-ui.png"), full_page=False)
        print("Saved: assets/screenshots/swagger-ui.png")

        # ── Metrics API response ────────────────────────────────────────────
        page.goto(f"{BASE_URL}/v1/metrics/summary", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "metrics-summary.png"), full_page=False)
        print("Saved: assets/screenshots/metrics-summary.png")

        # ── Circuit breaker status ──────────────────────────────────────────
        page.goto(f"{BASE_URL}/v1/circuit-breaker/status", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "circuit-breaker.png"), full_page=False)
        print("Saved: assets/screenshots/circuit-breaker.png")

        browser.close()


def make_agent_flow_gif() -> None:
    """Create a 5-frame GIF showing the agent request/response flow."""
    from PIL import Image, ImageDraw, ImageFont

    WIDTH, HEIGHT = 960, 420
    BG     = (15,  23,  42)   # dark navy
    PANEL  = (30,  41,  59)
    ACCENT = (99,  102, 241)  # indigo
    GREEN  = (34,  197, 94)
    YELLOW = (250, 204, 21)
    WHITE  = (241, 245, 249)
    GRAY   = (148, 163, 184)

    try:
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
        font_xs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except OSError:
        font_lg = font_sm = font_xs = ImageFont.load_default()

    def base_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)
        # Title bar
        draw.rectangle([(0, 0), (WIDTH, 48)], fill=PANEL)
        draw.text((20, 13), "Agentic AI Platform — Request Flow", font=font_lg, fill=WHITE)
        return img, draw

    def box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
            label: str, color=ACCENT, active: bool = False) -> None:
        fill = color if active else PANEL
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, fill=fill, outline=color, width=2)
        draw.text((x + 10, y + h // 2 - 8), label, font=font_sm, fill=WHITE)

    def arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color=GRAY) -> None:
        draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        draw.polygon([(x2, y2), (x2 - 8, y2 - 5), (x2 - 8, y2 + 5)], fill=color)

    # Components: positions
    boxes = [
        (50,  160, 130, 60, "Client",     GRAY),
        (230, 160, 140, 60, "Planner",    ACCENT),
        (430, 160, 140, 60, "Executor",   ACCENT),
        (630, 160, 130, 60, "LLM",        GREEN),
        (810, 160, 110, 60, "Response",   YELLOW),
    ]
    arrows = [
        (180, 190, 228, 190),
        (370, 190, 428, 190),
        (570, 190, 628, 190),
        (760, 190, 808, 190),
    ]

    frames: list[Image.Image] = []

    for active_idx in range(len(boxes)):
        img, draw = base_frame()
        # Draw all boxes
        for idx, (x, y, w, h, label, color) in enumerate(boxes):
            box(draw, x, y, w, h, label, color, active=(idx == active_idx))
        # Draw arrows
        for ax1, ay1, ax2, ay2 in arrows:
            arrow(draw, ax1, ay1, ax2, ay2)
        # Status line
        stage_labels = [
            "1/5  Client sends prompt to /v1/agent/run",
            "2/5  PlannerAgent selects tools based on prompt",
            "3/5  ExecutorAgent runs calculator / search_docs",
            "4/5  LLM provider generates final answer",
            "5/5  Structured response + trace returned to client",
        ]
        draw.text((50, 270), stage_labels[active_idx], font=font_sm, fill=WHITE)

        # Telemetry note on last frame
        if active_idx == len(boxes) - 1:
            draw.text((50, 310), "→ Telemetry event written to SQLite  |"
                      "  X-Request-ID propagated  |  CircuitBreaker updated",
                      font=font_xs, fill=GRAY)

        frames.append(img)

    # Add a hold frame at the end
    frames.append(frames[-1].copy())

    out = DEMO_DIR / "agent-flow.gif"
    frames[0].save(
        str(out),
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=[800, 800, 800, 800, 800, 2000],
        loop=0,
    )
    print(f"Saved: assets/demo/agent-flow.gif  ({len(frames)} frames)")


if __name__ == "__main__":
    _ensure_dirs()
    print("Warming up server with demo requests…")
    _warm_up_server()
    print("Taking screenshots…")
    take_screenshots()
    print("Generating agent-flow GIF…")
    make_agent_flow_gif()
    print("\nDone. Add these paths to README.md:")
    for p in sorted((ASSETS_DIR).rglob("*.*")):
        print(f"  assets/{p.relative_to(ASSETS_DIR)}")
