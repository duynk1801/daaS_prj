# VNPT Drone DaaS Backend — Agent Entry Point

This folder is the **mandatory entry point** for all AI agents working on this backend service.

---

## ⚠️ MANDATORY — Before ANY code change

Every agent **MUST** read these files **in order** before touching any code:

| # | File | Purpose |
|---|------|---------|
| 1 | `.agent/rules.md` | Core rules, protocols, and workflow |
| 2 | `.agent/project_structure.md` | Target architecture and file layout |
| 3 | `.agent/CODING_CONVENTIONS.md` | Code standards, patterns, examples |

Reading is **not optional**. No exceptions for "simple" requests.

---

## 🏗️ Architecture at a Glance

```
FastAPI (API Layer)
    ↓
Use Cases (Application Layer)
    ↓
Domain Entities + Rules (Domain Layer)
    ↓
Repository + Redis + RabbitMQ (Infrastructure Layer)
    ↓
PostgreSQL / Redis / RabbitMQ (Shared Infrastructure)
```

**Stack:** FastAPI · SQLAlchemy 2.0 · PostgreSQL · Redis · RabbitMQ · Alembic · pytest

---

## 🥇 Golden Rules

> **DO NOT CODE until scope is understood and approved.**

1. Always ask clarifying questions before implementation. Never assume.
2. Always create a task checklist **before** writing code.
3. Always present **at least 3 solutions** with pros/cons when ambiguity exists.
4. Sync documentation after every architecture or feature change.

---

## 📁 Directory Layout

```
.agent/
├── README.md                   # This file — entry point
├── rules.md                    # Agent rules and protocols
├── project_structure.md        # Target file structure
├── CODING_CONVENTIONS.md       # Coding standards
├── doc/                        # Feature documentation
│   ├── auth-doc.md
│   ├── booking-doc.md
│   ├── payment-doc.md
│   └── ...
└── plan/                       # Architecture decision records
    └── (ADRs go here)
```

---

## 📐 Architecture Changes

Every **architecture or foundation change** must:
1. Be documented as an ADR in `.agent/plan/`
2. Be approved by the user before implementation
3. Have a migration checklist
4. Update relevant feature docs in `.agent/doc/`
