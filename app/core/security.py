from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import threading
import time
from app.config import settings

ALGORITHM = "HS256"

# ===== Token Blacklist (in-memory, with expiry cleanup) =====
_token_blacklist: dict[str, float] = {}
_blacklist_lock = threading.Lock()


def blacklist_token(token: str, ttl_seconds: int = None):
    """Add a token to the blacklist with expiry."""
    if ttl_seconds is None:
        ttl_seconds = settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    with _blacklist_lock:
        _token_blacklist[token] = time.time() + ttl_seconds
        # Cleanup expired entries periodically
        if len(_token_blacklist) > 1000:
            now = time.time()
            expired = [k for k, v in _token_blacklist.items() if v < now]
            for k in expired:
                del _token_blacklist[k]


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is in the blacklist."""
    with _blacklist_lock:
        expiry = _token_blacklist.get(token)
        if expiry and expiry > time.time():
            return True
        if expiry:
            del _token_blacklist[token]
        return False


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict, token_version: int = 1, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access", "ver": token_version})
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, token_version: int = 1) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.APP_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "ver": token_version})
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ===== Login Attempt Limiting (in-memory) =====
_login_attempts: dict[str, list[float]] = {}
_attempts_lock = threading.Lock()


def check_login_attempts(key: str) -> bool:
    """Check if login is allowed for this key (username or IP).
    Returns True if allowed, False if locked out."""
    with _attempts_lock:
        attempts = _login_attempts.get(key, [])
        now = time.time()
        window = settings.LOGIN_LOCKOUT_MINUTES * 60
        recent = [t for t in attempts if now - t < window]
        if len(recent) >= settings.LOGIN_MAX_ATTEMPTS:
            return False
        return True


def record_login_attempt(key: str, success: bool):
    """Record a login attempt. On success, clear attempts for this key."""
    with _attempts_lock:
        if success:
            _login_attempts.pop(key, None)
        else:
            now = time.time()
            if key not in _login_attempts:
                _login_attempts[key] = []
            _login_attempts[key].append(now)
            # Keep only recent attempts
            window = settings.LOGIN_LOCKOUT_MINUTES * 60
            _login_attempts[key] = [t for t in _login_attempts[key] if now - t < window]
