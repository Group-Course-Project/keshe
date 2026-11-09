# -*- coding: utf-8 -*-
"""账号与会话：只用 Python 标准库，不引入新的第三方依赖。

- 密码：PBKDF2-HMAC-SHA256 + 每账号随机盐，存储格式为
  ``pbkdf2_sha256$迭代次数$盐(hex)$派生值(hex)``。
- 会话：服务端随机 token 存 auth_session 表，登出即删除，可吊销。
- 兼容：所有业务接口的登录都是「可选」的，未登录仍可按原来的匿名方式使用。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import AppUser, AuthSession

_ITERATIONS = 120_000
_SESSION_DAYS = 30
_TOKEN_HEADER = "X-Auth-Token"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def create_session(db: Session, user_id: int) -> tuple[str, datetime]:
    db.execute(
        delete(AuthSession).where(AuthSession.expires_at < datetime.now())
    )
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=_SESSION_DAYS)
    db.add(AuthSession(token=token, user_id=user_id, expires_at=expires_at))
    db.commit()
    return token, expires_at


def revoke_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token == token))
    db.commit()


def user_out(user: AppUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "created_at": user.created_at.isoformat(sep=" ", timespec="seconds")
        if user.created_at
        else "",
    }


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get(_TOKEN_HEADER) or None


def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> tuple[AppUser | None, str | None]:
    """返回 (用户, token)：未登录或令牌无效时用户为 None，不抛异常。"""
    token = _extract_token(request)
    if not token:
        return None, None
    session = db.get(AuthSession, token)
    if session is None or session.expires_at < datetime.now():
        return None, token
    user = db.get(AppUser, session.user_id)
    return user, token


def require_user(
    identity: tuple[AppUser | None, str | None] = Depends(get_optional_user),
) -> AppUser:
    user, _ = identity
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再使用该功能",
        )
    return user


def find_user_by_username(db: Session, username: str) -> AppUser | None:
    return db.scalar(select(AppUser).where(AppUser.username == username))
