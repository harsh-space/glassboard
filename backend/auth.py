import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

_secret = os.getenv("JWT_SECRET_KEY")
if not _secret:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. "
        "Copy .env.example to .env and fill in a real secret before starting the app."
    )
SECRET_KEY: str = _secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Optional bearer — auto_error=False so missing token returns None instead of 401
_optional_bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user_optional(token: Optional[str] = Depends(_optional_bearer)):
    """
    Returns the current User if a valid bearer token is present.
    Returns None if no token is present or the token is malformed/expired.
    Never raises — the board-level access check decides the real status code.
    """
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None

    # Lazy import to avoid circular imports (models → db → auth)
    from backend.db import SessionLocal
    from backend.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        return user
    finally:
        db.close()


def require_board_access(board, user) -> None:
    """
    Enforce board-level ownership:
      - board.owner_id is None → public (guest board), always allowed.
      - owner_id set, no token   → 401 UNAUTHORIZED.
      - owner_id set, wrong user → 403 FORBIDDEN.
      - owner_id set, correct user → allowed.
    """
    if board.owner_id is None:
        return  # public / guest board
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Authentication required to access this board.",
                "details": {},
            },
        )
    if user.id != board.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "You do not have permission to access this board.",
                "details": {},
            },
        )
