# test_battle_service — JWT Auth Microservice PRD

## Overview
A standalone FastAPI microservice with JWT-based authentication. Five endpoints covering the full auth lifecycle: registration, login, profile, token refresh, and token verification.

## Tech Stack
- **Framework**: FastAPI (latest)
- **ORM**: SQLAlchemy 2.0 async with aiosqlite
- **Database**: SQLite (file: `data.db`)
- **Validation**: Pydantic v2
- **JWT**: python-jose[cryptography]
- **Password hashing**: passlib[bcrypt]
- **Server**: uvicorn

## Project Structure
```
src/
├── main.py           # FastAPI app, lifespan, include router
├── config.py         # Settings via pydantic-settings (JWT secret, DB URL, token TTL)
├── database.py       # async engine, sessionmaker, Base, get_db dependency
├── models.py         # SQLAlchemy User model
├── schemas.py        # Pydantic request/response schemas
├── auth.py           # JWT encode/decode, password hash/verify helpers
├── dependencies.py   # get_current_user dependency (extracts user from Bearer token)
└── routes.py         # APIRouter with 5 endpoints
requirements.txt
```

## Database Model

### User
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| email | String(255) | unique, not null, indexed |
| hashed_password | String(255) | not null |
| is_active | Boolean | default True |
| created_at | DateTime | default utcnow |

## API Endpoints

### 1. POST /auth/register
**Request body:**
```json
{"email": "user@example.com", "password": "strongpass123"}
```
**Response 201:**
```json
{"id": 1, "email": "user@example.com", "is_active": true, "created_at": "2026-01-31T12:00:00"}
```
**Errors:**
- 409 Conflict: email already registered
- 422 Validation: invalid email or password < 8 chars

### 2. POST /auth/login
**Request body:**
```json
{"email": "user@example.com", "password": "strongpass123"}
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```
**Errors:**
- 401 Unauthorized: invalid email or password

### 3. GET /auth/me
**Headers:** `Authorization: Bearer <access_token>`
**Response 200:**
```json
{"id": 1, "email": "user@example.com", "is_active": true, "created_at": "2026-01-31T12:00:00"}
```
**Errors:**
- 401 Unauthorized: missing/invalid/expired token

### 4. POST /auth/refresh
**Request body:**
```json
{"refresh_token": "eyJ..."}
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```
**Errors:**
- 401 Unauthorized: invalid/expired refresh token

### 5. POST /auth/token/verify
**Request body:**
```json
{"token": "eyJ..."}
```
**Response 200:**
```json
{"valid": true, "email": "user@example.com", "exp": 1706745600}
```
**Response 200 (invalid token):**
```json
{"valid": false, "email": null, "exp": null}
```

## JWT Configuration
- **Algorithm**: HS256
- **Access token TTL**: 15 minutes
- **Refresh token TTL**: 7 days
- **Secret key**: from environment variable `JWT_SECRET` (default: `super-secret-key-change-me`)
- **Token payload**: `{"sub": "user@example.com", "type": "access"|"refresh", "exp": <timestamp>}`

## Non-Functional Requirements
- All endpoints use async/await
- Database created automatically on startup (create_all)
- Proper HTTP status codes
- Input validation via Pydantic
- Password never returned in any response
- CORS middleware enabled (allow all origins for dev)

## How to Run
```bash
pip install -r requirements.txt
cd src && uvicorn main:app --reload
# or: python -m uvicorn src.main:app --reload
```
