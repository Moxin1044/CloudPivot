import random
import string
import uuid
import time
import io
import base64
import threading
from fastapi import APIRouter, HTTPException
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Captcha"])

# In-memory captcha store: captcha_id -> {code, expires_at}
_captcha_store: dict = {}
_store_lock = threading.Lock()

CAPTCHA_CHARS = string.ascii_uppercase + string.digits
# Remove confusable characters
CAPTCHA_CHARS = CAPTCHA_CHARS.translate(str.maketrans("", "", "0IO1L"))


def _cleanup_expired():
    """Remove expired captchas."""
    now = time.time()
    expired = [k for k, v in _captcha_store.items() if v["expires_at"] < now]
    for k in expired:
        del _captcha_store[k]


def generate_captcha_code(length: int = 4) -> str:
    """Generate a random captcha code."""
    return "".join(random.choices(CAPTCHA_CHARS, k=length))


def _generate_svg(text: str) -> str:
    """Generate an SVG captcha image with noise lines and dots."""
    width = 130
    height = 48

    chars = list(text)
    char_count = len(chars)
    char_width = width // (char_count + 1)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#f5f7fa" rx="4"/>',
    ]

    # Add noise dots
    for _ in range(30):
        x = random.randint(5, width - 5)
        y = random.randint(5, height - 5)
        r = random.uniform(0.5, 1.5)
        color = random.choice(["#bbb", "#ccc", "#ddd", "#aaa"])
        svg_parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    # Add noise lines
    for _ in range(3):
        x1 = random.randint(0, width // 3)
        y1 = random.randint(5, height - 5)
        x2 = random.randint(2 * width // 3, width)
        y2 = random.randint(5, height - 5)
        color = random.choice(["#d0d5dd", "#c0c5cd", "#e0e5ed"])
        svg_parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>'
        )

    # Add characters with rotation and color variation
    colors = ["#1a56db", "#e02424", "#047857", "#b45309", "#7c3aed", "#be123c"]
    fonts = ["Arial", "Helvetica", "Georgia", "Courier New", "Times New Roman"]

    for i, ch in enumerate(chars):
        x = char_width * (i + 1) - char_width // 3
        y = random.randint(28, 38)
        rotation = random.randint(-25, 25)
        color = random.choice(colors)
        font = random.choice(fonts)
        size = random.randint(22, 28)

        svg_parts.append(
            f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
            f'fill="{color}" transform="rotate({rotation}, {x}, {y})" '
            f'font-weight="bold" text-anchor="middle">{ch}</text>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


@router.get("/captcha", summary="获取验证码")
async def get_captcha():
    """Generate a new captcha image and return its ID and SVG data."""
    with _store_lock:
        _cleanup_expired()
        captcha_id = str(uuid.uuid4())
        code = generate_captcha_code()
        _captcha_store[captcha_id] = {
            "code": code.upper(),
            "expires_at": time.time() + settings.CAPTCHA_EXPIRE_SECONDS,
        }

    svg = _generate_svg(code)
    svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    return {
        "captcha_id": captcha_id,
        "captcha_image": f"data:image/svg+xml;base64,{svg_b64}",
    }


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    """Verify a captcha code. Returns True if valid."""
    if not settings.CAPTCHA_ENABLED:
        return True
    if not captcha_id or not captcha_code:
        return False
    with _store_lock:
        entry = _captcha_store.get(captcha_id)
        if not entry:
            return False
        if entry["expires_at"] < time.time():
            del _captcha_store[captcha_id]
            return False
        if entry["code"] != captcha_code.strip().upper():
            return False
        # One-time use: delete after verification
        del _captcha_store[captcha_id]
        return True
