[← Back to Index](../README.md)

# userauth01 Service — Flow Diagrams

**Service:** PJ_IWI_USERAUTH  
**Service Name:** userauth01  
**Standard:** RFC 6749 — OAuth 2.0 Authorization Code Grant (user-facing flows)

---

## Table of Contents

- [Overview](#overview)
- [Login Flow](#login-flow)
- [User-Initiated Registration Flow](#user-initiated-registration-flow)
- [SFDC-Initiated Invitation Flow](#sfdc-initiated-invitation-flow)
- [Call-Based Invitation Flow](#call-based-invitation-flow)
- [Password Reset Flow](#password-reset-flow)
- [Email Change Flow](#email-change-flow)
- [Session and CSRF State Diagram](#session-and-csrf-state-diagram)
- [Account Activation — Async Two-Phase Commit](#account-activation--async-two-phase-commit)

---

## Overview

The userauth01 service is the **user-facing authentication gateway** for the IWI platform. It bridges the end user (browser), the Service Provider (client application), and the oauth01 authorization service. All successful authentication flows ultimately result in an OAuth 2.0 Authorization Code being delivered to the Service Provider.

**Actors:**

| Actor | Description |
|-------|-------------|
| User (Browser) | End user with a web browser |
| Service Provider | Client application integrating with IWI |
| userauth01 | This service — handles login, registration, password reset |
| oauth01 | OAuth 2.0 token service — issues authorization codes and tokens |
| Salesforce (SFDC) | CRM — Contact records created for new users |
| SendGrid | Email delivery service |
| Cloud Tasks | Async task queue for account creation callbacks |
| Cloud Datastore | Storage for sessions, users, and verification tokens |

---

## Login Flow

The login flow handles two modes: **browser form** (from IWI's own login page) and **XHR** (from a Service Provider's own page using JavaScript).

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant SP as Service Provider
    participant UA as userauth01
    participant OA as oauth01
    participant DS as Cloud Datastore

    User->>SP: Access protected resource
    SP->>User: Redirect to login
    User->>UA: GET /login?response_type=code&client_id=...&state=...&redirect_uri=...

    UA->>DS: Check iwi-state cookie (AuthSession)

    alt Session exists and user_id is set (already logged in)
        UA->>OA: Request authorization code
        OA->>DS: Create AuthOAuthCode
        UA-->>User: 302 Found → redirect_uri?code=...&state=...
    else No session or not logged in
        UA-->>User: 200 OK (login form HTML with hidden OAuth params)
    end

    User->>UA: POST /login (mailaddr + password + OAuth params)
    UA->>DS: Look up AuthMail2ID by mailaddr
    UA->>DS: Look up AuthUser by user_id

    alt Credentials valid
        UA->>DS: Create/update AuthSession (user_id = authenticated user)
        UA->>OA: Request authorization code (X-IWI-UserID = user_id)
        OA->>DS: Create AuthOAuthCode (10 min expiry)
        OA-->>UA: auth code

        alt Browser form POST (from IWI login page)
            UA-->>User: 302 Found → redirect_uri?code=...&state=...\nSet-Cookie: iwi-state=...
        else XHR from Service Provider page
            UA-->>User: 302 Found → redirect_uri?code=...&state=...\nSet-Cookie + CORS headers
        end

        User->>SP: GET redirect_uri?code=...&state=...
        SP->>SP: Validate state (CSRF check)
        SP->>OA: POST /requesttoken (code, redirect_uri)
        OA-->>SP: {access_token, refresh_token, iwi_user_id}
        SP-->>User: Access granted

    else Credentials invalid
        alt Browser form POST
            UA-->>User: 200 OK (login form re-displayed with error)
        else XHR from Service Provider
            UA-->>User: 200 OK Content-Type: application/json\n{"status": "ng"}
        end
    end
```

**Note on legacy passwords:** If an account was migrated from HeartCore (MD5 hash), the password is automatically re-hashed to SHA-512 on the first successful login.

---

## User-Initiated Registration Flow

New users register themselves by providing their email address and setting a password.

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant SP as Service Provider
    participant UA as userauth01
    participant SG as SendGrid (Email)
    participant CT as Cloud Tasks
    participant DS as Cloud Datastore
    participant SF as Salesforce (SFDC)

    SP->>User: Redirect to registration
    User->>UA: GET /register?response_type=code&client_id=...&state=...&return_path=...
    UA-->>User: 200 OK (email entry form with CSRF token + reCAPTCHA)

    User->>UA: POST /register (mailaddr, csrf_token, g-recaptcha-response, OAuth params)
    UA->>UA: Validate CSRF token
    UA->>UA: Verify reCAPTCHA (HTTP → Google API)
    UA->>DS: Check AuthMail2ID — email must not be in use

    alt Email already registered
        UA-->>User: 409 Conflict (email already used message)
    else Email available
        UA->>DS: Create UserAuthRegister (verification token, 1 hour expiry)
        UA->>SG: Send verification email with link\n/register/auth?k=register:<UUID>
        UA-->>User: 200 OK (email sent — check your inbox)
    end

    User->>UA: GET /register/auth?k=register:<UUID>
    UA->>DS: Look up UserAuthRegister by key
    UA-->>User: 200 OK (password creation form)

    User->>UA: POST /register/auth (key, password, password2)
    UA->>UA: Validate password match (min 8 chars)
    UA->>DS: Mark UserAuthRegister.registered_at = now (consume token)

    Note over UA,CT: Account creation is asynchronous (two-phase commit)
    UA->>CT: Enqueue _add_new_account task

    UA->>DS: Create AuthSession (user_id set)
    UA->>OA: Request authorization code
    UA-->>User: 302 Found → redirect_uri?code=...&state=...

    Note over CT,SF: Async account creation (Cloud Task)
    CT->>DS: Create AuthUser (IN_PROGRESS)
    CT->>DS: Create AuthMail2ID (IN_PROGRESS)
    CT->>SF: Create Salesforce Contact (Composite API)
    alt SFDC success
        CT->>DS: Clear IN_PROGRESS on AuthMail2ID (account active)
    else SFDC failure
        CT->>DS: Invalidate AuthMail2ID (account rollback)
    end
```

---

## SFDC-Initiated Invitation Flow

An external Salesforce workflow creates an IWI account on behalf of a user. The user is then invited to set their password.

```mermaid
sequenceDiagram
    autonumber
    participant SFDC as Salesforce Workflow
    participant UA as userauth01
    participant SG as SendGrid (Email)
    actor User as User (Browser)
    participant DS as Cloud Datastore

    Note over SFDC: Salesforce business event triggers user creation

    SFDC->>UA: POST /register/sfdc\nAuthorization: Basic ...\n{"mailaddr": "user@example.com"}

    UA->>DS: Check AuthMail2ID — is email in use?

    alt Email already valid
        UA->>DS: Retrieve existing AuthUser
        UA-->>SFDC: 200 OK {status: true, Id: <existing_user_id>, Url: <invite_url>}
    else Email IN_PROGRESS
        UA-->>SFDC: 409 Conflict {error: CONFLICTED_STATE}
    else Email available
        UA->>DS: Create AuthUser (stub, no password yet)
        UA->>DS: Create UserAuthRegister (invitation code, long-lived)
        UA->>SG: Send invitation email\n/invite?k=invitation:<UUID>
        UA-->>SFDC: 200 OK {status: true, Id: <new_user_id>, Url: /invite?k=invitation:<UUID>}
    end

    Note over SFDC: SFDC stores the IWI User ID in the Contact record

    User->>UA: GET /invite?k=invitation:<UUID>
    UA->>DS: Look up UserAuthRegister (invitation code)
    UA-->>User: 200 OK (confirmation page showing email)

    User->>UA: POST /invite (key=invitation:<UUID>)
    UA->>DS: Create second UserAuthRegister (completion code, shorter expiry)
    UA->>SG: Send completion email\n/invite/auth?k=completion:<UUID>
    UA-->>User: 200 OK (check your email)

    User->>UA: GET /invite/auth?k=completion:<UUID>
    UA->>DS: Look up UserAuthRegister (completion code)
    UA-->>User: 200 OK (password creation form)

    User->>UA: POST /invite/auth (key, password, password2)
    UA->>UA: Validate password
    UA->>DS: Update AuthUser.password (SHA-512 hash)
    UA->>DS: Activate AuthMail2ID
    UA-->>User: 200 OK (account activated — success page)
```

---

## Call-Based Invitation Flow

An alternative invitation flow for external systems that need a callback notification after the user completes registration.

```mermaid
sequenceDiagram
    autonumber
    participant ExtSys as External System
    participant UA as userauth01
    participant SG as SendGrid (Email)
    actor User as User (Browser)
    participant DS as Cloud Datastore
    participant CT as Cloud Tasks
    participant CB as Callback URL

    Note over ExtSys: External system wants to invite a user\nand be notified when they register

    ExtSys->>UA: POST /call/user\nAuthorization: Basic ...\n{mailaddr, greeting_title, greeting_body, callback: {url, method}}

    UA->>DS: Check AuthMail2ID — email must not be in use
    alt Email already in use
        UA-->>ExtSys: 409 Conflict
    else Email available
        UA->>DS: Create UserAuthRegister (invitation code, 20-year expiry)
        UA->>SG: Send greeting/invitation email\n/call?k=invitation:<UUID>
        UA-->>ExtSys: 200 OK {status: true, invitation_code: "invitation:<UUID>"}
    end

    User->>UA: GET /call?k=invitation:<UUID>
    UA->>DS: Look up UserAuthRegister
    UA-->>User: 200 OK (confirmation page)

    User->>UA: POST /call (key=invitation:<UUID>)
    UA->>DS: Create completion code UserAuthRegister
    UA->>SG: Send completion email\n/call/auth?k=completion:<UUID>
    UA-->>User: 200 OK

    User->>UA: GET /call/auth?k=completion:<UUID>
    UA->>DS: Look up UserAuthRegister
    UA-->>User: 200 OK (password creation form)

    User->>UA: POST /call/auth (key, password, password2)
    UA->>UA: Validate password

    Note over UA,SF: Async account creation (Cloud Task)
    UA->>CT: Enqueue account creation task

    CT->>DS: Create AuthUser (SHA-512 password hash)
    CT->>DS: Create/activate AuthMail2ID
    CT->>SF: Create Salesforce Contact

    alt Callback configured
        CT->>CB: POST callback.url\n{iwi_user_id, sfdc_contact_id}
        Note over CB: External system receives user IDs\nand can link the new user to its data
    end

    UA-->>User: 200 OK (success page)
```

---

## Password Reset Flow

Users who forgot their password can reset it via their registered email address.

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant SP as Service Provider
    participant UA as userauth01
    participant SG as SendGrid (Email)
    participant DS as Cloud Datastore
    participant OA as oauth01

    SP->>User: Redirect to password reset
    User->>UA: GET /reset?response_type=code&client_id=...&state=...&return_path=...
    UA-->>User: 200 OK (email entry form with CSRF token + reCAPTCHA)

    User->>UA: POST /reset (mailaddr, csrf_token, g-recaptcha-response, OAuth params)
    UA->>UA: Validate CSRF token
    UA->>UA: Verify reCAPTCHA
    UA->>DS: Look up AuthMail2ID by mailaddr

    Note over UA: Whether email exists or not,\nresponse is always "email sent"\n(prevents email enumeration)

    alt Email registered
        UA->>DS: Create UserAuthRegister (reset code, 1 hour expiry)
        UA->>SG: Send reset email with link\n/reset/auth?k=reset:<UUID>
    end

    UA-->>User: 200 OK (check your email)

    User->>UA: GET /reset/auth?k=reset:<UUID>
    UA->>DS: Look up UserAuthRegister by key
    UA-->>User: 200 OK (new password form)

    User->>UA: POST /reset/auth (key, password, password2)
    UA->>UA: Validate password match (min 8 chars)
    UA->>DS: Look up AuthUser
    UA->>DS: Update AuthUser.password (new SHA-512 hash)
    UA->>DS: Mark UserAuthRegister as consumed

    UA->>DS: Create AuthSession (user_id set)
    UA->>OA: Request authorization code
    UA-->>User: 302 Found → redirect_uri?code=...&state=...\n(user is now logged in)
```

---

## Email Change Flow

Authenticated users can change their primary email address. The flow verifies the new address and blocks changes for paid NewsPicks subscribers.

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Browser)
    participant UA as userauth01
    participant NP as NewsPicks API
    participant SF as Salesforce API
    participant SG as SendGrid (Email)
    participant DS as Cloud Datastore
    participant U1 as user01 service

    Note over User: User must be logged in (iwi-state cookie with user_id)

    User->>UA: GET /user/email
    UA->>DS: Verify AuthSession.user_id is set
    UA-->>User: 200 OK (email change form with CSRF token)

    User->>UA: POST /user/email (mailaddr=new@example.com, csrf_token)
    UA->>UA: Validate CSRF token
    UA->>DS: Check AuthMail2ID — new email must not be in use

    UA->>SF: Query Contact by user_id (check NPAddress__c field)

    alt NPAddress__c is set (NewsPicks linked)
        UA->>NP: Query NewsPicks account status
        alt Paid subscriber
            UA-->>User: 400 Bad Request (email change blocked for paid accounts)
        end
    end

    UA->>DS: Create UserAuthRegister (email change code, 1 hour expiry)
    UA->>SG: Send verification email to NEW address\n/user/email/auth?k=emailchange:<UUID>
    UA-->>User: 200 OK (verification email sent to new address)

    User->>UA: GET /user/email/auth?k=emailchange:<UUID>
    UA->>DS: Verify AuthSession.user_id (still logged in)
    UA->>DS: Look up UserAuthRegister by key
    UA-->>User: 200 OK (confirmation page)

    User->>UA: POST /user/email/auth (key=emailchange:<UUID>)
    UA->>DS: Consume UserAuthRegister token
    UA->>U1: Call user01 service to apply email change\n(update AuthMail2ID mapping)
    U1->>DS: Update old AuthMail2ID (invalidate)
    U1->>DS: Create new AuthMail2ID
    UA-->>User: 200 OK (email changed successfully)
```

---

## Session and CSRF State Diagram

```mermaid
flowchart TD
    START([No iwi-state cookie\nFirst Request])
    START --> CREATE[Create AuthSession\nSet-Cookie: iwi-state\nuser_id = null]
    CREATE --> ANON

    ANON[Anonymous Session\nuser_id = null\nCSRF = SHA256 of session_id\nEmbedded as hidden field in forms\nValidated on every POST]

    ANON -- GET pages --> ANON
    ANON -- Login or Register or Reset success --> LI

    LI[Logged In\nuser_id = set\nMax-Age refreshed to 7 days on every request\nRequired for email-change endpoints]

    LI -- Any request --> LI
    LI -- POST /logout --> LO[Logged Out\nuser_id = null]
    LO -- POST /login success --> LI

    style START  fill:#DFE1E6,stroke:#97A0AF,color:#172B4D
    style CREATE fill:#DEEBFF,stroke:#0052CC,color:#172B4D
    style ANON   fill:#F4F5F7,stroke:#97A0AF,color:#172B4D
    style LI     fill:#E3FCEF,stroke:#36B37E,color:#006644
    style LO     fill:#FFFAE6,stroke:#FF8B00,color:#172B4D
```

---

## Account Activation — Async Two-Phase Commit

New account creation uses a Cloud Tasks-based two-phase commit to ensure consistency between the IWI Datastore and Salesforce.

```mermaid
flowchart TD
    A[POST /register/auth or /call/auth received] --> B[Validate password]
    B --> C[Consume verification token]
    C --> D[Create AuthSession + issue OAuth code]
    D --> E[Enqueue Cloud Task: _add_new_account]
    E --> F[Return 302 to user immediately]

    subgraph "Cloud Task — async execution"
        G[Phase 1: Create AuthUser in Datastore]
        G --> H[Phase 1: Create AuthMail2ID with IN_PROGRESS flag]
        H --> I[Phase 2: Create Contact in Salesforce via Composite API]
        I --> J{SFDC success?}
        J -- Yes --> K[Phase 3: Clear IN_PROGRESS on AuthMail2ID\nAccount is now fully active]
        J -- No --> L[Invalidate AuthMail2ID\nSend error alert\nAccount creation rolled back]
    end

    E --> G

    style K fill:#d4edda,stroke:#28a745
    style L fill:#f8d7da,stroke:#dc3545
```

**Why async?** Salesforce API calls can take several seconds. By creating the IWI session and issuing the OAuth code immediately, the user is never blocked waiting for Salesforce. The account is functional for authentication within milliseconds.

---

## Registration Flow Decision Tree

```mermaid
flowchart TD
    A[New user needs IWI account] --> B{Who initiates?}

    B --> C[User themselves]
    B --> D[Salesforce workflow]
    B --> E[External system]

    C --> F[User goes to /register\non Service Provider site]
    F --> G[Email verification email]
    G --> H[Set password at register/auth]
    H --> I[Account active + logged in]

    D --> J[SFDC calls POST /register/sfdc]
    J --> K{Email in use?}
    K -- Valid existing --> L[Return existing IWI ID]
    K -- IN_PROGRESS --> M[409 Conflict]
    K -- Not found --> N[Send invitation email /invite]
    N --> O[User confirms /invite]
    O --> P[Completion email /invite/auth]
    P --> Q[Set password]
    Q --> R[Account active]

    E --> S[External system calls POST /call/user\nwith callback URL]
    S --> T[Send greeting email /call]
    T --> U[User confirms /call]
    U --> V[Completion email /call/auth]
    V --> W[Set password]
    W --> X[Account created + callback fired]
    X --> Y[External system receives IWI ID]

    style I fill:#d4edda,stroke:#28a745
    style R fill:#d4edda,stroke:#28a745
    style Y fill:#d4edda,stroke:#28a745
    style M fill:#f8d7da,stroke:#dc3545
```

---

*© Funai Soken Digital — IWI Documentation*
