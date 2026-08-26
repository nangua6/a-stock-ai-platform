"""Authentication, authorization, and RBAC for the trading platform."""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Set

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import get_settings

# ── Password Hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── JWT Secret (sourced from env in production) ──────────────────────────────
JWT_SECRET_KEY = "dev-secret-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours


class Role(str, Enum):
    """RBAC roles with increasing privilege levels."""
    ADMIN = "ADMIN"
    RESEARCH = "RESEARCH"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_VIEW = "LIVE_VIEW"
    LIVE_TRADE = "LIVE_TRADE"
    AUTO_TRADE = "AUTO_TRADE"


# Role hierarchy: each role inherits permissions from roles below it (transitively)
ROLE_HIERARCHY: dict[Role, list[Role]] = {
    Role.ADMIN: [Role.RESEARCH, Role.PAPER_TRADING, Role.LIVE_VIEW, Role.LIVE_TRADE, Role.AUTO_TRADE],
    Role.RESEARCH: [],
    Role.PAPER_TRADING: [Role.RESEARCH],
    Role.LIVE_VIEW: [Role.PAPER_TRADING, Role.RESEARCH],
    Role.LIVE_TRADE: [Role.LIVE_VIEW, Role.PAPER_TRADING, Role.RESEARCH],
    Role.AUTO_TRADE: [Role.LIVE_TRADE, Role.LIVE_VIEW, Role.PAPER_TRADING, Role.RESEARCH],
}


def _collect_permissions(role: Role, visited: Optional[Set[Role]] = None) -> Set[Role]:
    """Recursively collect all permissions for a role."""
    if visited is None:
        visited = set()
    if role in visited:
        return visited
    visited.add(role)
    for child in ROLE_HIERARCHY.get(role, []):
        _collect_permissions(child, visited)
    return visited


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: Role, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def has_permission(user_role: Role, required_role: Role) -> bool:
    """Check if user_role has at least the privileges of required_role (transitive)."""
    if user_role == Role.ADMIN:
        return True
    permissions = _collect_permissions(user_role)
    return required_role in permissions
