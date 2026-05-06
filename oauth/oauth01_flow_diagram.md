[← Back to Index](../README.md)

# oauth01 Service — Flow Diagrams

**Service:** PJ_IWI_RECONS  
**Standard:** RFC 6749 — OAuth 2.0 Authorization Code Grant

---

## Table of Contents

- [Overview](#overview)
- [Full Authorization Code Grant Flow](#full-authorization-code-grant-flow)
- [Token Refresh Flow](#token-refresh-flow)
- [Token Validation Flow (Resource Server Side)](#token-validation-flow-resource-server-side)
- [Session Lifecycle](#session-lifecycle)
- [Security Event Flow — Replay Attack Detection](#security-event-flow--replay-attack-detection)
- [Token Expiry Timeline](#token-expiry-timeline)

---

## Overview

The oauth01 service implements the OAuth 2.0 Authorization Code Grant (RFC 6749 §4.1). It sits between the user's browser, the client application (Service Provider), and protected resource servers.

| Actor | Role |
|-------|------|
| **User (Browser)** | End user operating a web browser |
| **Service Provider** | Client application requesting access on behalf of the user |
| **userauth01** | Handles user login / authentication (user-facing) |
| **oauth01** | This service — issues authorization codes and tokens |
| **Resource Server** | Downstream IWI service that validates access tokens |
| **Cloud Datastore** | Persistent storage for sessions, codes, and tokens |

---

## Full Authorization Code Grant Flow

The flow is divided into three phases: **User Authentication**, **Code Exchange**, and **API Access**.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant SP as Service Provider
    participant UA as userauth01
    participant OA as oauth01
    participant RS as Resource Server
    participant DS as Datastore

    Note over User,DS: ══════════════════ PHASE 1 · User Authentication ══════════════════

    User->>SP: Access protected resource
    SP->>User: Redirect to /login
    User->>UA: GET /login?response_type=code&client_id=...&state=...
    Note over UA: Check iwi-state session cookie

    alt 🟢 Session already active (already logged in)
        UA->>OA: Forward request (X-IWI-UserID set)
        OA->>DS: Create AuthOAuthCode — expires +10 min
        UA-->>User: 302 Found → redirect_uri?code=...&state=...
    else 🔵 No session — first login
        UA-->>User: 200 OK — Login form
        User->>UA: POST /login (email + password + OAuth params)
        UA->>DS: Validate credentials (AuthUser, AuthMail2ID)
        alt ✅ Login success
            UA->>DS: Create AuthSession (user_id assigned)
            UA->>OA: Forward request (X-IWI-UserID=user_id)
            OA->>DS: Create AuthOAuthCode — expires +10 min
            UA-->>User: 302 → redirect_uri?code=...&state=... + Set-Cookie: iwi-state
        else ❌ Login failure
            UA-->>User: 200 OK — Login form (credentials rejected)
        end
    end

    Note over User,DS: ══════════════════ PHASE 2 · Code Exchange ══════════════════

    User->>SP: GET redirect_uri?code=...&state=...
    SP->>SP: ✔ Validate state parameter (CSRF check)

    rect rgb(254, 243, 199)
        SP->>OA: POST /requesttoken (grant_type=authorization_code, code=...)
        Note over OA: Authenticate client — Basic Auth (client_id:client_secret)
        OA->>DS: Look up AuthOAuthCode
    end

    alt ✅ Code valid (exists · not expired · not used)
        OA->>DS: Create AuthOAuthAccessToken — expires +1 hr
        OA->>DS: Create AuthOAuthRefreshToken
        OA->>DS: Mark AuthOAuthCode as consumed
        OA-->>SP: 200 OK {access_token, refresh_token, expires_in, iwi_user_id}
    else ❌ Code invalid or expired
        OA-->>SP: 400 Bad Request {error: invalid_grant}
    else ⚠️ Code already used — replay attack
        OA->>DS: Revoke AuthOAuthCode immediately
        OA-->>SP: 400 Bad Request {error: invalid_grant}
    end

    Note over User,DS: ══════════════════ PHASE 3 · API Access ══════════════════

    rect rgb(237, 233, 254)
        SP->>SP: Store access_token + refresh_token securely
        SP->>RS: GET /resource  Authorization: Bearer <access_token>
        RS->>OA: validate token (internal call)
        OA->>DS: Verify token + session validity
        OA-->>RS: ✅ user_id (authorized)
        RS-->>SP: 200 OK — resource data
        SP-->>User: Display resource
    end
```

---

## Token Refresh Flow

When the access token expires, the Service Provider uses the refresh token to obtain a new access token — no user interaction required.

```mermaid
sequenceDiagram
    autonumber
    participant SP as Service Provider
    participant OA as oauth01
    participant DS as Datastore

    Note over SP: ⏰ Access token expired (expires_in = 3600 s)

    rect rgb(219, 234, 254)
        Note over SP,DS: ── Step 1 · Submit Refresh Request ──
        SP->>OA: POST /refreshtoken (grant_type=refresh_token, refresh_token=...)
        Note over OA: Authenticate client — Basic Auth
        OA->>DS: Look up AuthOAuthRefreshToken
    end

    rect rgb(254, 243, 199)
        Note over OA,DS: ── Step 2 · Validation Checks ──
        OA->>DS: Check AuthSession.revoked_at is null
        OA->>DS: Check root AuthOAuthCode.revoked_at is null
    end

    alt ✅ All checks pass
        rect rgb(220, 252, 231)
            Note over OA,DS: ── Step 3 · Issue New Token ──
            OA->>DS: Create new AuthOAuthAccessToken — expires +1 hr
            OA->>DS: Update AuthOAuthRefreshToken.access_token reference
            OA-->>SP: 200 OK {access_token, expires_in, iwi_user_id}
        end
        Note over SP: ✔ Replace old access_token with new one<br/>✔ Keep the same refresh_token for next time
    else ❌ Refresh token expired or revoked
        OA-->>SP: 400 Bad Request {error: invalid_grant}
    else ❌ Session revoked (user logged out)
        OA-->>SP: 400 Bad Request {error: invalid_grant}
    end
```

> **Note:** The refresh response does **not** include a new `refresh_token`. Keep using the same one.

---

## Token Validation Flow (Resource Server Side)

This flowchart shows every check the `oauth_guard` module runs when a Resource Server validates a Bearer token. All six checks must pass — the first failure returns `401 Unauthorized`.

```mermaid
flowchart TD
    START([🔑 Bearer token received\nfrom Service Provider])

    START --> A[Look up token\nin Datastore]

    A --> B{Token\nexists?}
    B -- ❌ Not found --> F1([401 Unauthorized\nUnknown token])

    B -- ✅ Found --> C{client_id\nmatches?}
    C -- ❌ Mismatch --> F2([401 Unauthorized\nClient mismatch])

    C -- ✅ Match --> D{Token\nexpired?}
    D -- ❌ Expired --> F3([401 Unauthorized\nToken expired])

    D -- ✅ Valid --> E{Token\nrevoked?}
    E -- ❌ Revoked --> F4([401 Unauthorized\nToken revoked])

    E -- ✅ Active --> G[Look up AuthSession\nfrom Datastore]

    G --> H{Session\nrevoked?}
    H -- ❌ Revoked --> F5([401 Unauthorized\nSession revoked])

    H -- ✅ Active --> I{root_code\npresent?}

    I -- Yes --> J[Look up\nAuthOAuthCode]
    J --> K{root_code\nrevoked?}
    K -- ❌ Revoked --> F6([401 Unauthorized\nOrigin code revoked])
    K -- ✅ Valid --> OK

    I -- No --> OK([✅ Return user_id\nRequest authorized])

    style START fill:#0052CC,color:#fff,stroke:#0052CC
    style OK    fill:#36B37E,color:#fff,stroke:#36B37E
    style F1    fill:#FF5630,color:#fff,stroke:#DE350B
    style F2    fill:#FF5630,color:#fff,stroke:#DE350B
    style F3    fill:#FF5630,color:#fff,stroke:#DE350B
    style F4    fill:#FF5630,color:#fff,stroke:#DE350B
    style F5    fill:#FF5630,color:#fff,stroke:#DE350B
    style F6    fill:#FF5630,color:#fff,stroke:#DE350B
    style A     fill:#DEEBFF,stroke:#0052CC
    style G     fill:#DEEBFF,stroke:#0052CC
    style J     fill:#DEEBFF,stroke:#0052CC
    style B     fill:#F4F5F7,stroke:#97A0AF
    style C     fill:#F4F5F7,stroke:#97A0AF
    style D     fill:#F4F5F7,stroke:#97A0AF
    style E     fill:#F4F5F7,stroke:#97A0AF
    style H     fill:#F4F5F7,stroke:#97A0AF
    style I     fill:#F4F5F7,stroke:#97A0AF
    style K     fill:#F4F5F7,stroke:#97A0AF
```

---

## Session Lifecycle

The `iwi-state` cookie tracks the user's session state. Each state has distinct behavior for token operations.

```mermaid
flowchart TD
    ENTRY([No Cookie\nFirst Request])

    ENTRY --> CREATE[Create AuthSession\nSet-Cookie: iwi-state\nuser_id = null]

    CREATE --> ANON[⬜ Anonymous\nSession active\nuser_id = null]

    ANON -- POST /login success --> LOGGEDIN

    LOGGEDIN[🟢 Logged In\nuser_id = set\nTokens bound to session]

    LOGGEDIN -- Any request --> REFRESH[Cookie Max-Age reset\n7 days from now]
    REFRESH --> LOGGEDIN

    LOGGEDIN -- POST /requesttoken --> TOKEN[AuthOAuthAccessToken\ncreated + bound to session]
    TOKEN --> LOGGEDIN

    LOGGEDIN -- POST /logout --> LOGGEDOUT[🟡 Logged Out\nuser_id = null\nSession preserved]

    LOGGEDOUT -- POST /login success --> LOGGEDIN

    LOGGEDIN -- Replay attack detected\nor admin revocation --> REVOKED[🔴 Session Revoked\nrevoked_at = now]

    REVOKED --> DEAD([All linked tokens invalid\nRe-authentication required])

    style ENTRY   fill:#DFE1E6,stroke:#97A0AF,color:#172B4D
    style CREATE  fill:#DEEBFF,stroke:#0052CC,color:#172B4D
    style ANON    fill:#F4F5F7,stroke:#97A0AF,color:#172B4D
    style LOGGEDIN fill:#E3FCEF,stroke:#36B37E,color:#006644
    style REFRESH fill:#E3FCEF,stroke:#36B37E,color:#006644
    style TOKEN   fill:#E3FCEF,stroke:#36B37E,color:#006644
    style LOGGEDOUT fill:#FFFAE6,stroke:#FF8B00,color:#172B4D
    style REVOKED fill:#FFEBE6,stroke:#FF5630,color:#BF2600
    style DEAD    fill:#FFEBE6,stroke:#FF5630,color:#BF2600
```

| State | Color | user_id | Tokens valid? |
|-------|-------|---------|---------------|
| Anonymous | ⬜ Gray | `null` | — |
| Logged In | 🟢 Green | set | Yes |
| Logged Out | 🟡 Yellow | `null` | Existing tokens invalid on next check |
| Revoked | 🔴 Red | — | No — all tokens rejected immediately |

---

## Security Event Flow — Replay Attack Detection

If a client attempts to reuse an authorization code that was already exchanged, the service treats it as a replay attack, revokes the code immediately, and logs a `CRITICAL` event.

```mermaid
sequenceDiagram
    autonumber
    participant Attacker as ⚠️ Attacker
    participant OA as oauth01
    participant DS as Datastore
    participant Log as Cloud Logging

    Note over Attacker,OA: The authorization code was already exchanged for a token once.

    Attacker->>OA: POST /requesttoken (code = <already used code>)

    rect rgb(255, 235, 230)
        Note over OA,DS: ── DETECTION ──
        OA->>DS: Look up AuthOAuthCode
        OA->>DS: Read AuthOAuthCode.access_token field
        Note over OA: ⚠ access_token is already set on this code<br/>→ code was previously consumed<br/>→ REPLAY ATTACK DETECTED
    end

    rect rgb(255, 200, 180)
        Note over OA,Log: ── RESPONSE & REVOCATION ──
        OA->>DS: SET revoked_at = now  on AuthOAuthCode
        OA->>Log: 🚨 CRITICAL — Replay attack detected {code, client_id, user_id}
        OA-->>Attacker: 400 Bad Request {error: invalid_grant}
    end

    Note over DS: All future token validations using<br/>this code as root_code will now fail.<br/>All derived tokens are effectively voided.
```

---

## Token Expiry Timeline

| Token | Lifetime | Notes |
|-------|----------|-------|
| **Authorization Code** | 10 minutes | Single-use. Reusing it triggers replay attack detection and immediate revocation. |
| **Access Token** | 1 hour (3600 s) | Passed as `Authorization: Bearer <token>` on every API call. |
| **Refresh Token** | Long-lived | 60-second reuse window for concurrent requests. Same token reused for all future refreshes. |
| **Session Cookie** (`iwi-state`) | 7 days | Max-Age is reset to 7 days on every active request. |

```mermaid
gantt
    title Token Lifetime Overview (minutes)
    dateFormat  X
    axisFormat  %s min

    section Auth Code
    Valid — 10 min         : 0, 10

    section Access Token
    Valid — 60 min         : 0, 60

    section Refresh Token
    Reuse window — 1 min   : crit, 0, 1
    Long-lived             : 1, 60

    section Session Cookie
    Active — refreshed per request (shown as 60 min) : active, 0, 60
```

---

*Reference: RFC 6749 — The OAuth 2.0 Authorization Framework*  
*© Funai Soken Digital — IWI Documentation*
