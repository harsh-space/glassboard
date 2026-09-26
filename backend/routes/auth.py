from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from backend.db import SessionLocal
from backend.models import User, Board
from backend.auth import verify_password, hash_password, create_access_token, decode_token
from datetime import date

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token.", "details": {}},
        )
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid token payload.", "details": {}},
        )
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "User not found.", "details": {}},
        )
    return user


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str


class BoardSummary(BaseModel):
    id: int
    name: str
    start_date: date
    task_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CreateBoardRequest(BaseModel):
    name: str
    start_date: date


# ── Auth Endpoints ────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.lower().strip()
    clean_username = payload.username.strip()

    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_EMAIL", "message": "Please enter a valid email address.", "details": {}},
        )
    if not clean_username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_USERNAME", "message": "Username cannot be empty.", "details": {}},
        )
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WEAK_PASSWORD", "message": "Password must be at least 6 characters.", "details": {}},
        )

    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_TAKEN", "message": "This email is already registered.", "details": {}},
        )
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "USERNAME_TAKEN", "message": "This username is already taken.", "details": {}},
        )

    user = User(
        email=clean_email,
        username=clean_username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ident = payload.email.lower().strip()
    user = db.query(User).filter((User.email == ident) | (User.username == payload.email.strip())).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password.", "details": {}},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "Account is inactive.", "details": {}},
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
    )


# OAuth2 token endpoint (for Swagger UI compatibility)
@router.post("/token", response_model=TokenResponse)
def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ident = form_data.username.lower().strip()
    user = db.query(User).filter((User.email == ident) | (User.username == form_data.username.strip())).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password.", "details": {}},
        )
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }


# ── Board Management (per user) ───────────────────────────────────────────────

@router.get("/boards", response_model=list[BoardSummary])
def list_boards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    boards = (
        db.query(Board)
        .filter((Board.owner_id == current_user.id) | (Board.owner_id.is_(None)))
        .order_by(Board.id)
        .all()
    )
    result = []
    for b in boards:
        result.append(BoardSummary(
            id=b.id,
            name=b.name,
            start_date=b.start_date,
            task_count=len(b.tasks),
        ))
    return result


@router.post("/boards", response_model=BoardSummary, status_code=201)
def create_board(
    payload: CreateBoardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = Board(
        name=payload.name,
        start_date=payload.start_date,
        owner_id=current_user.id,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return BoardSummary(id=board.id, name=board.name, start_date=board.start_date, task_count=0)
