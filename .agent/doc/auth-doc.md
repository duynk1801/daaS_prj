# Auth Feature — Documentation

> **Feature:** Authentication & Authorization  
> **Status:** 🔄 Planned (Phase 2)  
> **Last Updated:** 2026-06-17

---

## Overview

JWT-based authentication with RBAC. Access token (15 min) + refresh token (7 days, server-side revocation).

---

## Planned API

```
POST /api/v1/auth/login         # Email + password → tokens
POST /api/v1/auth/refresh       # Refresh token → new access token
POST /api/v1/auth/logout        # Invalidate refresh token
POST /api/v1/auth/register      # New user registration
```

---

## Security Requirements

- Passwords: bcrypt/argon2 hashing, min 8 chars
- JWT: HS256 only, reject `none` algorithm
- Refresh tokens: stored in DB (allow revocation)
- Rate limit: 5 login attempts/min per IP
- TODO(security): MFA implementation
- TODO(security): OAuth2 provider (Google, VNPT SSO)
- TODO(security): Leaked password detection

---

## RBAC Roles

| Role | Permissions |
|------|-------------|
| `user` | Own bookings, own profile, own wallet |
| `operator` | Confirm bookings, view assigned missions |
| `admin` | All resources, user management, reports |
| `pilot` | View assigned missions, update mission status |

---

## Implementation Plan

```
features/auth/
  api/
    controller.py       # login, refresh, logout, register
    schemas.py          # LoginRequest, TokenResponse, RegisterRequest
  domain/
    entity.py           # UserEntity
    rules.py            # validate_password_strength()
  application/
    login.py            # LoginUseCase
    refresh_token.py    # RefreshTokenUseCase
    register.py         # RegisterUseCase
    auth_service.py     # Facade
  infrastructure/
    repository.py       # UserRepository, RefreshTokenRepository
    password_hasher.py  # bcrypt wrapper
```
