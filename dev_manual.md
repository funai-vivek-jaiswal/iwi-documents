[← Back to Index](./README.md)

# IWI Developer Manual

**Services:** PJ_IWI_RECONS (oauth01) · PJ_IWI_USERAUTH (userauth01)  
**Audience:** Development team members integrating with or maintaining IWI authentication services.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Local Development Setup](#3-local-development-setup)
   - [oauth01 (PJ_IWI_RECONS)](#31-oauth01-pj_iwi_recons)
   - [userauth01 (PJ_IWI_USERAUTH)](#32-userauth01-pj_iwi_userauth)
4. [Environment Variables Reference](#4-environment-variables-reference)
5. [Registering an OAuth Client](#5-registering-an-oauth-client)
6. [Integrating Login into a Service Provider](#6-integrating-login-into-a-service-provider)
   - [Standard Browser Redirect Flow](#61-standard-browser-redirect-flow)
   - [XHR/JavaScript Login](#62-xhrjavascript-login)
7. [Integrating User Registration](#7-integrating-user-registration)
   - [User-Initiated Registration](#71-user-initiated-registration)
   - [SFDC-Initiated Registration](#72-sfdc-initiated-registration)
   - [Call-Based Invitation](#73-call-based-invitation)
8. [Token Lifecycle Management](#8-token-lifecycle-management)
9. [Validating Access Tokens (Resource Server)](#9-validating-access-tokens-resource-server)
10. [Password Requirements](#10-password-requirements)
11. [Testing and Development Features](#11-testing-and-development-features)
12. [Deployment](#12-deployment)
13. [Logging and Monitoring](#13-logging-and-monitoring)
14. [Common Mistakes and Gotchas](#14-common-mistakes-and-gotchas)
15. [Service URLs by Environment](#15-service-urls-by-environment)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser / Client App                       │
└───────────────────┬───────────────────┬──────────────────────────┘
                    │                   │
         ┌──────────▼──────┐   ┌────────▼──────────┐
         │  userauth01     │   │   oauth01          │
         │  PJ_IWI_USERAUTH│   │   PJ_IWI_RECONS   │
         │  - Login/logout │   │   - /authorize     │
         │  - Registration │──▶│   - /requesttoken  │
         │  - Pwd reset    │   │   - /refreshtoken  │
         │  - Email change │   │                    │
         └────────┬────────┘   └────────┬───────────┘
                  │                     │
         ┌────────▼─────────────────────▼───────────┐
         │            Cloud Datastore (NDB)           │
         │  AuthUser · AuthMail2ID · AuthSession      │
         │  AuthOAuthCode · AuthOAuthAccessToken      │
         │  AuthOAuthRefreshToken · AuthClient        │
         └────────────────────────────────────────────┘
                  │
         ┌────────▼────────────────────────────────┐
         │  External Services                       │
         │  Salesforce · SendGrid · Google Tasks    │
         └─────────────────────────────────────────┘
```

**Key relationship:** userauth01 handles all user-facing HTML/form interactions and delegates OAuth code generation to oauth01. After login, the browser receives a redirect with an authorization code; the Service Provider (backend) exchanges that code for tokens by calling oauth01 directly.

---

## 2. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.14+ | Service runtime |
| Docker | 24+ | Build and local testing |
| Google Cloud SDK (`gcloud`) | Latest | Deployment and Datastore emulator |
| Cloud Datastore Emulator | Bundled with SDK | Local development |

Install Google Cloud SDK and initialize:

```bash
gcloud init
gcloud components install cloud-datastore-emulator
gcloud components install beta
```

---

## 3. Local Development Setup

### 3.1 oauth01 (PJ_IWI_RECONS)

```bash
cd /home/vivek/project/iwi/PJ_IWI_RECONS

# Install dependencies
pip install -r requirements.txt

# Start Datastore emulator in a separate terminal
gcloud beta emulators datastore start --host-port=localhost:8081

# Set emulator environment variable
export DATASTORE_EMULATOR_HOST=localhost:8081
export GOOGLE_CLOUD_PROJECT=iwi-dev

# Run the service
uvicorn main:app --reload --port 8080
```

The service is now available at `http://localhost:8080`.

**Run tests:**

```bash
# With Datastore emulator running:
pytest tests/ -v

# With coverage:
pytest tests/ --cov=. --cov-report=html
```

### 3.2 userauth01 (PJ_IWI_USERAUTH)

```bash
cd /home/vivek/project/iwi/PJ_IWI_USERAUTH

# Install dependencies
pip install -r requirements.txt

# Start Datastore emulator (if not already running)
gcloud beta emulators datastore start --host-port=localhost:8081

# Set environment variables
export DATASTORE_EMULATOR_HOST=localhost:8081
export GOOGLE_CLOUD_PROJECT=iwi-dev
export IWI_DEV_FEATURES=fake_now,skip_recaptcha,log_mail_body

# Run the service
uvicorn main:app --reload --port 8081
```

**Seed test data:**

```bash
# Seed a test OAuth client and user account
python seed_playwright.py
```

**Run tests:**

```bash
pytest tests/ -v
```

---

## 4. Environment Variables Reference

These variables apply to both services unless noted.

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | `iwi-dev` | GCP project ID |
| `DATASTORE_PROJECT_ID` | *(inherits GOOGLE_CLOUD_PROJECT)* | Datastore project ID (overrides if set) |
| `DATASTORE_EMULATOR_HOST` | *(not set)* | Set to `localhost:8081` to use the local emulator instead of production Datastore |
| `IWI_DEV_FEATURES` | *(not set)* | Comma-separated development feature flags (see [Section 11](#11-testing-and-development-features)) |
| `IWI_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PORT` | `8080` | HTTP listen port |
| `GAE_SERVICE` | *(not set)* | Service name for internal routing; set automatically in Cloud Run |

---

## 5. Registering an OAuth Client

Before a Service Provider can use the IWI login flow, it must have a registered `AuthClient` record in Datastore.

**Required fields:**

| Field | Description |
|-------|-------------|
| `id` | UUID — this is the `client_id` you share with the Service Provider |
| `name` | Human-readable name |
| `secret` | Secret string — share securely with the Service Provider (used in Basic Auth) |
| `services` | Dict of service names the client may access (e.g., `{"all": 1}`) |
| `info.oauth2.known_redirect_hosts` | List of allowed redirect URI hostnames (e.g., `["app.example.com"]`) |
| `info.oauth2.default_redirect_uri` | Default redirect URI (optional — allows omitting `redirect_uri` in requests) |

**Creating a client in the Datastore emulator (dev):**

```python
# run in a Python shell with DATASTORE_EMULATOR_HOST set
import uuid
from google.cloud import ndb

client = ndb.Client(project='iwi-dev')
with client.context():
    from common.auth.datamodel import AuthClient
    AuthClient(
        id=str(uuid.uuid4()),
        name='My Service Provider',
        secret='my-dev-secret',
        services={'all': 1},
        info={
            'oauth2': {
                'known_redirect_hosts': ['localhost:3000', 'app.example.com'],
                'default_redirect_uri': 'http://localhost:3000/callback'
            }
        }
    ).put()
```

---

## 6. Integrating Login into a Service Provider

### 6.1 Standard Browser Redirect Flow

**Step 1 — Redirect the user to the IWI login page:**

```
GET https://<userauth01-host>/login
  ?response_type=code
  &client_id=<your-client-id>
  &redirect_uri=https://your-app.example.com/auth/callback
  &state=<random-unguessable-value>
  &scope=all
```

Generate `state` as a cryptographically random value (e.g., 32-byte hex string). Store it in the user's session.

**Step 2 — Handle the callback:**

After successful login, the user is redirected to:

```
GET https://your-app.example.com/auth/callback
  ?code=<authorization_code>
  &state=<the-state-you-sent>
```

Verify `state` matches what you stored. If it does not match, abort and show an error (CSRF attack).

**Step 3 — Exchange the code for tokens:**

```bash
curl -X POST https://<oauth01-host>/requesttoken \
  -u "<client_id>:<client_secret>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=<authorization_code>" \
  -d "redirect_uri=https://your-app.example.com/auth/callback"
```

**Response:**

```json
{
  "access_token": "550e8400-e29b-41d4-a716-446655440000",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "7c8d9e0f-...",
  "iwi_user_id": "5e87c5bb-..."
}
```

Store `access_token`, `refresh_token`, and `iwi_user_id` securely in your server-side session.

**Python example (using httpx):**

```python
import httpx
import secrets

# Step 1: Build login URL
state = secrets.token_hex(32)
session['oauth_state'] = state

login_url = (
    f"https://{USERAUTH_HOST}/login"
    f"?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&state={state}"
)
return redirect(login_url)

# Step 2: Handle callback
def auth_callback(request):
    code = request.query_params['code']
    state = request.query_params['state']

    if state != session.get('oauth_state'):
        raise ValueError("State mismatch — possible CSRF attack")

    # Step 3: Exchange code for tokens
    response = httpx.post(
        f"https://{OAUTH_HOST}/requesttoken",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    session['access_token'] = tokens['access_token']
    session['refresh_token'] = tokens['refresh_token']
    session['iwi_user_id'] = tokens['iwi_user_id']
```

### 6.2 XHR/JavaScript Login

When the Service Provider hosts its own login form and uses XHR to call IWI:

```javascript
async function login(email, password, oauthParams) {
  const formData = new URLSearchParams({
    mailaddr: email,
    password: password,
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    state: STATE,
  });

  const response = await fetch('https://<userauth01-host>/login', {
    method: 'POST',
    credentials: 'include',           // required for cookie handling
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',   // required for JSON error responses
    },
    body: formData.toString(),
    redirect: 'manual',               // prevent browser from following redirect
  });

  if (response.type === 'opaqueredirect' || response.status === 302) {
    // Login succeeded — the browser was redirected to redirect_uri
    // Your backend callback handler receives the code
    window.location.reload();
  } else {
    const data = await response.json();
    if (data.status === 'ng') {
      showError('Invalid email or password');
    }
  }
}
```

**CORS configuration required at `redirect_uri` server:**

```
Access-Control-Allow-Origin: null
Access-Control-Allow-Credentials: true
```

See [userauth01 API — JavaScript Usage Notes](./userauth01_api_list.md#javascript-xhr-usage-notes) for full details.

---

## 7. Integrating User Registration

### 7.1 User-Initiated Registration

Redirect the user to the registration form with the same OAuth parameters as login:

```
GET https://<userauth01-host>/register
  ?response_type=code
  &client_id=<your-client-id>
  &redirect_uri=https://your-app.example.com/auth/callback
  &state=<random-state>
  &return_path=https://your-app.example.com/welcome
```

The `return_path` is displayed as a link on the registration success page ("Return to application").

After the user completes registration, they are redirected to your `redirect_uri` with an authorization code — exactly the same as after login. Handle the callback identically to the login flow.

### 7.2 SFDC-Initiated Registration

Call this endpoint from a Salesforce workflow or backend service when a Contact is created in Salesforce and an IWI account is needed.

```bash
curl -X POST https://<userauth01-host>/register/sfdc \
  -u "<client_id>:<client_secret>" \
  -H "Content-Type: application/json" \
  -d '{"mailaddr": "user@example.com"}'
```

**Success response:**

```json
{
  "status": true,
  "Id": "5e87c5bb-847e-4bb2-9cbd-c26b6a33a799",
  "Url": "https://<userauth01-host>/invite?k=invitation:abc123"
}
```

Store the `Id` (IWI User ID) in your Salesforce Contact record. The `Url` is included in the invitation email sent automatically by IWI — you do **not** need to send it yourself.

If `status` is `true`, the user will receive an invitation email. They click the link, confirm their email, and set a password. No further action is required from the backend.

### 7.3 Call-Based Invitation

Use this when you need a callback notification after the user completes registration.

```bash
curl -X POST https://<userauth01-host>/call/user \
  -u "<client_id>:<client_secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "mailaddr": "user@example.com",
    "greeting_title": "You are invited!",
    "greeting_body": "Please complete your registration.",
    "greeting_parameters": {},
    "contact_params": {},
    "callback": {
      "url": "https://your-backend.example.com/on-user-registered",
      "method": "POST"
    }
  }'
```

**Callback payload** (sent to `callback.url` after account creation):

```json
{
  "iwi_user_id": "5e87c5bb-...",
  "sfdc_contact_id": "003XX000000XXXXX"
}
```

Your callback endpoint should be idempotent (Cloud Tasks may retry on failure).

---

## 8. Token Lifecycle Management

| Token | Lifetime | Notes |
|-------|----------|-------|
| Authorization code | 10 minutes | Single-use only. Using it twice triggers replay attack response. |
| Access token | 1 hour (3600s) | Include in API calls as `Authorization: Bearer <token>` |
| Refresh token | Long-lived (60s reuse window) | Keep indefinitely; use to get new access tokens |
| Session cookie | 7 days | Refreshed on every request |

**Refreshing an access token:**

```bash
curl -X POST https://<oauth01-host>/refreshtoken \
  -u "<client_id>:<client_secret>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=<your-refresh-token>"
```

**Response:**

```json
{
  "access_token": "new-token-here",
  "token_type": "Bearer",
  "expires_in": 3600,
  "iwi_user_id": "5e87c5bb-..."
}
```

**Important:** The refresh response does **not** include a new `refresh_token`. Keep using the same one.

**Recommended client-side token management:**

```python
def get_valid_access_token(session):
    if is_expired(session['access_token_expires_at']):
        response = refresh_access_token(session['refresh_token'])
        if response.status_code == 400:
            # Refresh token is also invalid — force re-login
            clear_session(session)
            raise NeedsReloginError()
        session['access_token'] = response.json()['access_token']
        session['access_token_expires_at'] = now() + timedelta(seconds=3600)
    return session['access_token']
```

**60-second refresh token reuse window:** If two concurrent requests both try to refresh the same token within 60 seconds, both receive a valid (possibly the same) access token. This prevents lock-in on high-concurrency services.

---

## 9. Validating Access Tokens (Resource Server)

If you are building an IWI resource service (one that accepts IWI access tokens), use the `oauth_guard` module from oauth01.

```python
from common.auth.oauth_guard import ensure_valid_token
from common.error import IWIInvalidToken

async def my_protected_endpoint(request):
    token = request.headers.get('Authorization', '').removeprefix('Bearer ')
    try:
        user_id = await ensure_valid_token(token, CLIENT_ID, now())
    except IWIInvalidToken:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    # user_id is now the authenticated IWI User ID
    ...
```

**What `ensure_valid_token` checks:**

1. Token exists in Datastore
2. Token belongs to the requesting `client_id`
3. Token has not expired (`expired_at >= now`)
4. Token has not been revoked (`revoked_at is null`)
5. Associated session is active (`session.revoked_at is null`)
6. Root authorization code (if present) has not been revoked

All checks must pass. Any failure raises `IWIInvalidToken`.

---

## 10. Password Requirements

| Rule | Value |
|------|-------|
| Minimum length | 8 characters |
| Hashing algorithm | SHA-512 |
| Salt | UUID v4 (random, stored per user) |
| Stretching iterations | 10,000 |
| Legacy algorithm | MD5 (HeartCore migration) — auto-upgraded on next login |

Do not impose additional constraints on password character sets beyond the minimum length. Let users choose strong passwords freely.

---

## 11. Testing and Development Features

Set `IWI_DEV_FEATURES` to a comma-separated list of the following flags:

| Flag | Header to activate | Effect |
|------|--------------------|--------|
| `fake_now` | `X-IWI-Fake-Now: 2025-01-01T00:00:00+00:00` | Fix the server's current time for testing token expiry scenarios |
| `skip_recaptcha` | `X-IWI-Skip-reCAPTCHA: 1` | Bypass Google reCAPTCHA validation — use in tests only |
| `log_mail_body` | *(always active when flag is set)* | Log the full email content to Cloud Logging instead of sending via SendGrid |

**Example test configuration:**

```bash
export IWI_DEV_FEATURES=fake_now,skip_recaptcha,log_mail_body
```

**Testing token expiry with `fake_now`:**

```bash
# Issue a token at time T
curl -H "X-IWI-Fake-Now: 2025-01-01T00:00:00+00:00" ...

# Try to use the token 2 hours later (it should be expired)
curl -H "X-IWI-Fake-Now: 2025-01-01T02:00:00+00:00" \
     -H "Authorization: Bearer <token>" ...
```

**Testing registration without receiving email (`log_mail_body`):**

When `log_mail_body` is active, the verification link is printed to the service log. Check the log output for the `/register/auth?k=...` URL instead of waiting for an email.

```bash
# In another terminal, watch logs:
uvicorn main:app --reload 2>&1 | grep "register/auth"
```

---

## 12. Deployment

Both services are deployed to Google Cloud Run via Cloud Build.

**Deploy to development (iwi-dev):**

```bash
cd /home/vivek/project/iwi/PJ_IWI_RECONS   # or PJ_IWI_USERAUTH
gcloud builds submit --config cloudbuild.dev.yaml
```

**Deploy to production (iwi-stable):**

```bash
gcloud builds submit --config cloudbuild.prod.yaml
```

**Cloud Run configuration:**

| Setting | Development | Production |
|---------|-------------|------------|
| Min instances | 1 | 1 |
| Max instances | 3 | 10 |
| Memory | 512 Mi | 1 Gi |
| CPU | 1 | 1 |
| Request timeout | 30s | 30s |
| Concurrency | 80 | 80 |

**Docker build locally:**

```bash
docker build -t oauth01:local .
docker run -p 8080:8080 \
  -e DATASTORE_EMULATOR_HOST=host.docker.internal:8081 \
  -e GOOGLE_CLOUD_PROJECT=iwi-dev \
  oauth01:local
```

---

## 13. Logging and Monitoring

All services emit structured JSON logs to Google Cloud Logging.

**Standard log fields:**

| Field | Description |
|-------|-------------|
| `request_id` | UUID per request — use to correlate logs for a single request |
| `job_id` | UUID for cross-service trace chains |
| `trace` | Google Cloud Trace context |
| `severity` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `message` | Human-readable log message |

**Key security events to monitor:**

| Event | Severity | What it means |
|-------|----------|----------------|
| `REPLAY ATTACK DETECTED` | CRITICAL | An authorization code was used twice — possible theft |
| `unknown client_id` | ERROR | Unknown client attempting authentication — possible probing |
| `token validation failed` | ERROR | Access token was rejected — check for clock skew or expired tokens |
| `session revoked` | WARNING | A session was invalidated — user logged out or security event |

**Querying logs (Cloud Logging):**

```bash
# Find all CRITICAL events for a service
gcloud logging read "severity=CRITICAL AND resource.labels.service_name=oauth01" \
  --limit=50 --format=json

# Trace a specific request
gcloud logging read 'jsonPayload.request_id="<request-id>"' \
  --limit=100 --format=json
```

---

## 14. Common Mistakes and Gotchas

### State parameter is required — and must be unique

The `state` parameter is required by both `/login` and `/register`. Sending a static or empty state will cause a 400 error. Always generate a fresh random value per request:

```python
import secrets
state = secrets.token_urlsafe(32)
```

### Authorization codes are single-use

Never retry a failed token exchange with the same authorization code. If the exchange fails, redirect the user to the login page to start a new flow. Reusing a code triggers replay attack detection and revokes the code.

### redirect_uri must match exactly

The `redirect_uri` in `/requesttoken` must **exactly** match the one used in `/authorize` (or `/login`). Even a trailing slash difference causes rejection.

### Refresh token reuse — do not rotate

The refresh response does **not** include a new refresh token. Keep using the same refresh token for all future refreshes until it is rejected (session revoked or token expired). Do not discard it after the first use.

### XHR login requires `withCredentials: true`

Without `withCredentials: true`, the browser will not send or store the `iwi-state` session cookie. The user will appear logged out on every XHR request.

### CORS at redirect_uri must allow `null` origin

After XHR login, the browser follows the `302 Found` from a privacy-sensitive context, which sets `Origin: null`. If your `redirect_uri` server does not include `Access-Control-Allow-Origin: null`, the browser will block the response.

### Account creation is asynchronous

After `POST /register/auth`, the IWI account is created asynchronously via Cloud Tasks. The user's session and OAuth code are valid immediately, but the Salesforce Contact may not exist for a few seconds. Do not assume the SFDC Contact is ready synchronously.

### `IN_PROGRESS` emails in SFDC flow

If `POST /register/sfdc` returns `409 Conflict`, the email is in an `IN_PROGRESS` state (a previous account creation or email change is pending). Wait and retry — the state resolves within seconds in the normal case.

### Do not use `IWI_DEV_FEATURES` in production

The `skip_recaptcha` and `fake_now` flags disable security controls. Never set these in production Cloud Run deployments.

---

## 15. Service URLs by Environment

| Environment | userauth01 | oauth01 |
|-------------|-----------|---------|
| Local dev | `http://localhost:8081` | `http://localhost:8080` |
| GCP Dev (`iwi-dev`) | Set via Cloud Run service URL | Set via Cloud Run service URL |
| GCP Prod (`iwi-stable`) | Set via Cloud Run service URL | Set via Cloud Run service URL |

Retrieve the Cloud Run service URL:

```bash
gcloud run services describe userauth01 --region=<region> --format='value(status.url)'
gcloud run services describe oauth01 --region=<region> --format='value(status.url)'
```

---

## Quick Reference

### Login Flow Checklist

- [ ] Generate random `state` and store in session
- [ ] Redirect user to `/login` with OAuth params
- [ ] Receive `code` and `state` at `redirect_uri`
- [ ] Verify `state` matches stored value (CSRF check)
- [ ] POST to `/requesttoken` with `code` (Basic Auth)
- [ ] Store `access_token`, `refresh_token`, `iwi_user_id`
- [ ] Use `access_token` as `Bearer` token for API calls
- [ ] Refresh `access_token` before expiry using `/refreshtoken`

### Registration Integration Checklist

- [ ] User-initiated: redirect to `/register` with OAuth params + `return_path`
- [ ] SFDC-initiated: POST to `/register/sfdc` and store returned `Id`
- [ ] Call-based: POST to `/call/user` and implement `callback` endpoint

### Security Checklist

- [ ] `state` parameter is random and unique per request
- [ ] `redirect_uri` is registered with IWI before deployment
- [ ] Client secret is stored securely (not in frontend code or VCS)
- [ ] `withCredentials: true` set for XHR requests
- [ ] `redirect_uri` server returns `Access-Control-Allow-Origin: null`
- [ ] `IWI_DEV_FEATURES` is never set in production

---

*© Funai Soken Digital — IWI Documentation*
