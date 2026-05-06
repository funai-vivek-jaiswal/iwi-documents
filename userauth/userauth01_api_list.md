[← Back to Index](../README.md)

# userauth01 Service — API Reference

**Service:** PJ_IWI_USERAUTH  
**Service Name:** userauth01  
**Purpose:** User Authentication and Registration Service — handles user login, logout, user registration (user-initiated, SFDC-initiated, and invitation-based), password reset, and email address change.

---

## Table of Contents

- [Common Standards](#common-standards)
- [Authentication Endpoints](#authentication-endpoints)
  - [GET /login](#get-login)
  - [POST /login](#post-login)
  - [POST /logout](#post-logout)
- [User-Initiated Registration](#user-initiated-registration)
  - [GET /register](#get-register)
  - [POST /register](#post-register)
  - [GET /register/auth](#get-registerauth)
  - [POST /register/auth](#post-registerauth)
- [SFDC-Initiated Registration (IWI Internal)](#sfdc-initiated-registration-iwi-internal)
  - [POST /register/sfdc](#post-registersfdc)
- [SFDC Invitation Flow](#sfdc-invitation-flow)
  - [GET /invite](#get-invite)
  - [POST /invite](#post-invite)
  - [GET /invite/auth](#get-inviteauth)
  - [POST /invite/auth](#post-inviteauth)
- [Call-Based Invitation (IWI Internal)](#call-based-invitation-iwi-internal)
  - [POST /call/user](#post-calluser)
  - [GET /call](#get-call)
  - [POST /call](#post-call)
  - [GET /call/auth](#get-callauth)
  - [POST /call/auth](#post-callauth)
- [Email Change (Login Required)](#email-change-login-required)
  - [GET /user/email](#get-useremail)
  - [POST /user/email](#post-useremail)
  - [GET /user/email/auth](#get-useremailauth)
  - [POST /user/email/auth](#post-useremailauth)
- [Password Reset](#password-reset)
  - [GET /reset](#get-reset)
  - [POST /reset](#post-reset)
  - [GET /reset/auth](#get-resetauth)
  - [POST /reset/auth](#post-resetauth)
- [JavaScript (XHR) Usage Notes](#javascript-xhr-usage-notes)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Common Standards

### Authorization Header

Endpoints marked **IWI internal use only** require HTTP Basic Authentication (RFC 7617):

```
Authorization: Basic <base64(client_id:client_secret)>
```

Endpoints for browser-based user interaction do **not** require the Authorization header.

### Session Cookie

All browser-facing endpoints manage a session via the `iwi-state` cookie:

| Property | Value |
|----------|-------|
| Cookie name | `iwi-state` |
| Lifetime | 7 days (604800 seconds) |
| Flags | `HttpOnly`, `Secure`, `SameSite=None` (production) |

The cookie is issued on first login and refreshed (Max-Age reset) on every subsequent request.

### CSRF Protection

POST endpoints that display forms include a CSRF token. The token is a SHA256 hash derived from the session ID.

| Parameter | Description |
|-----------|-------------|
| `csrf_token` | CSRF prevention token. Obtained from the hidden field in the GET form response. Required on POST. |

### reCAPTCHA

Registration and password reset POST endpoints require Google reCAPTCHA verification:

| Parameter | Description |
|-----------|-------------|
| `g-recaptcha-response` | Browser-side reCAPTCHA response value (required) |

---

## Authentication Endpoints

### GET /login

**Display login form** — shows the Authorization Request entry point for the OAuth 2.0 Authorization Code Grant (RFC 6749 §4.1.1).

*(Authorization header not required)*

Behavior depends on session state:

| Session State | Behavior |
|---------------|----------|
| Session exists (already logged in) | Issues authorization code → `302 Found` to `redirect_uri` |
| No session, valid parameters | Displays login form HTML → `200 OK` |
| No session, invalid parameters | Displays error message → `400 Bad Request` |

**Request Example:**

```http
GET /login?response_type=code&client_id=abc&redirect_uri=https://app.example.com/callback&state=xyz HTTP/1.1
Host: userauth.example.com
Cookie: iwi-state=<session-id>
```

**Response Example (already logged in):**

```http
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=<auth_code>&state=xyz
```

**Response Example (show login form):**

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-authentication redirect URI. May be omitted if a default is registered with IWI. UTF-8, max 1000 bytes. |
| `scope` | string | Not currently used |
| `state` | string | Unique, unpredictable value issued by the Service Provider for CSRF prevention (required) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `302 Found` | Logged-in session exists — auth code issued |
| `200 OK` | Login form displayed |
| `400 Bad Request` | OAuth parameters invalid |

---

### POST /login

**Authentication** — receives credentials submitted from the login form or via XMLHttpRequest (XHR) from a Service Provider page.

*(Authorization header not required)*

Behavior differs depending on whether the request comes from IWI's own login page (form POST) or from a Service Provider page (XHR).

**Request Example (form POST from IWI login page):**

```http
POST /login HTTP/1.1
Host: userauth.example.com
Content-Type: application/x-www-form-urlencoded
Cookie: iwi-state=<session-id>

mailaddr=user@example.com&password=s3cr3t&response_type=code&client_id=abc&redirect_uri=https://app.example.com/callback&state=xyz
```

**Response — Login Success (form POST):**

```http
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=<auth_code>&state=xyz
Set-Cookie: iwi-state=<session-id>; Path=/; Max-Age=604800; HttpOnly; Secure; SameSite=None
```

**Response — Login Failure (form POST):**

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
```
*(Login form is re-displayed with error message)*

**Response — Login Success (XHR from Service Provider):**

```http
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=<auth_code>&state=xyz
Set-Cookie: iwi-state=<session-id>; Path=/; Max-Age=604800; HttpOnly; Secure; SameSite=None
Access-Control-Allow-Origin: https://origin.example.com
Access-Control-Allow-Credentials: true
Vary: Origin
```

**Response — Login Failure (XHR from Service Provider):**

```http
HTTP/1.1 200 OK
Content-Type: application/json;charset=UTF-8
Access-Control-Allow-Origin: https://origin.example.com
Access-Control-Allow-Credentials: true
Vary: Origin

{"status": "ng"}
```

**Response — Already Logged In (any):**

```http
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=<auth_code>&state=xyz
Access-Control-Allow-Origin: https://origin.example.com  (if XHR)
```

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mailaddr` | string | Email address (login ID) |
| `password` | string | Password |
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-authentication redirect URI |
| `scope` | string | Not currently used |
| `state` | string | Unique CSRF-prevention value from the Service Provider (required) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `302 Found` | Authentication success (including already-logged-in case) |
| `200 OK` | Authentication failure (form: re-display login form; XHR: `{"status": "ng"}`) |
| `400 Bad Request` | OAuth parameters invalid |

---

### POST /logout

**Logout** — invalidates the IWI login session, clearing the logged-in state.

*(Authorization header not required)*

This endpoint is designed to be called from JavaScript (XMLHttpRequest only). Regardless of the current session state, the endpoint always responds with `200 OK`.

**Response Example:**

```http
HTTP/1.1 200 OK
Set-Cookie: iwi-state=; Path=/; Max-Age=0; HttpOnly; Secure
```

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Logout processed (always, even if no active session) |

---

## User-Initiated Registration

### GET /register

**Display email entry form** — initial step of the user-initiated registration flow.

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-registration redirect URI |
| `scope` | string | Not currently used |
| `state` | string | Unique CSRF-prevention value (required) |
| `return_path` | string | URI to navigate to after registration completion (optional). Used to return the user to the originating application page. |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Email entry form displayed (includes `csrf_token` hidden field and reCAPTCHA widget) |

---

### POST /register

**Request verification email** — validates the submitted email address and sends a verification email with a registration link.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mailaddr` | string | Email address to register |
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-registration redirect URI |
| `scope` | string | Not currently used |
| `state` | string | Unique CSRF-prevention value (required) |
| `csrf_token` | string | CSRF prevention token from the form |
| `g-recaptcha-response` | string | Google reCAPTCHA browser response value |
| `return_path` | string | URI to navigate to after registration completion (optional) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Verification email sent — confirmation page displayed |
| `400 Bad Request` | Invalid parameters or CSRF/reCAPTCHA failure |
| `409 Conflict` | Email address already in use |

---

### GET /register/auth

**Display password setting form** — second step after the user clicks the verification link in the email.

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Registration code from the verification email link |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Password creation form displayed |
| `400 Bad Request` | Registration code invalid or expired (1 hour) |

---

### POST /register/auth

**Complete registration** — validates the password, creates the IWI account and Salesforce Contact, and issues an authorization code.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Registration code from the verification email |
| `password` | string | Password (minimum 8 characters) |
| `password2` | string | Password confirmation (must match `password`) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `302 Found` | Account created — redirects to `redirect_uri` with authorization code |
| `200 OK` | Password mismatch or validation failure — form re-displayed |
| `400 Bad Request` | Registration code invalid or expired |

**Business Logic Notes:**

- Account creation is asynchronous (two-phase commit via Cloud Tasks).
- Phase 1: Creates `AuthUser` and `AuthMail2ID` in Datastore (marked `IN_PROGRESS`).
- Phase 2: Creates a Contact in Salesforce via the Composite API.
- Phase 3: Clears `IN_PROGRESS` flag, activating the account.
- Password is hashed with SHA-512, 10,000 iterations, and a random UUID salt.

---

## SFDC-Initiated Registration (IWI Internal)

### POST /register/sfdc

**Salesforce-initiated user creation** — creates an IWI account from a Salesforce trigger and returns an invitation URL.

**IWI internal use only.** Requires HTTP Basic Authentication.

If the email address is already in use by a valid account, the existing user's IWI ID is returned. If the email address is currently being changed or a new account is being created for it, a `409 Conflict` is returned.

**Request Example:**

```http
POST /register/sfdc HTTP/1.1
Host: userauth.example.com
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/json

{
  "mailaddr": "newuser@example.com"
}
```

**Response Example (Success — new account):**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": true,
  "Id": "5e87c5bb-847e-4bb2-9cbd-c26b6a33a799",
  "Url": "https://userauth.example.com/invite?k=invitation:abc123"
}
```

**Response Example (Conflict):**

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "status": false,
  "error": "CONFLICTED_STATE",
  "error_details": ["newuser@example.com"]
}
```

**Request JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `mailaddr` | string | Email address for the new account |

**Response JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `$.status` | boolean | `true` on success, `false` on failure |
| `$.Id` | string | IWI User ID |
| `$.Url` | string | Invitation page URL (send to user to complete registration) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Account created or existing account found |
| `401 Unauthorized` | Missing or invalid client credentials |
| `409 Conflict` | Email is currently in transition (being changed or IN_PROGRESS) |

---

## SFDC Invitation Flow

Two-stage invitation flow initiated by the SFDC-initiated registration above.

### GET /invite

**Display invitation confirmation page** — shows the user their email address and prompts confirmation.

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Invitation code (format: `invitation:<UUID>`) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Confirmation page displayed |
| `400 Bad Request` | Invitation code invalid or expired |

---

### POST /invite

**Confirm invitation and send completion email** — user confirms their email and a second verification email is sent.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Invitation code |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Confirmation page displayed; completion email sent |
| `400 Bad Request` | Invitation code invalid |

---

### GET /invite/auth

**Display password setting form** — shown after user clicks the completion link in the second verification email.

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Completion code (format: `completion:<UUID>`) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Password creation form displayed |
| `400 Bad Request` | Completion code invalid or expired |

---

### POST /invite/auth

**Complete invitation and set password** — sets the user's password and activates the account.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Completion code |
| `password` | string | Password (minimum 8 characters) |
| `password2` | string | Password confirmation |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Account activated — success page displayed |
| `400 Bad Request` | Code invalid, expired, or password mismatch |

---

## Call-Based Invitation (IWI Internal)

An alternative invitation flow for external system integrations, with an optional callback after account creation.

### POST /call/user

**Create a call-based invitation** — sends an invitation email to the specified address.

**IWI internal use only.** Requires HTTP Basic Authentication.

If the email address is already registered to an active account, a `409 Conflict` is returned. Emails that were previously used but are now unlinked (due to email change) are considered available.

**Request Example:**

```http
POST /call/user HTTP/1.1
Host: userauth.example.com
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/json

{
  "mailaddr": "invitee@example.com",
  "greeting_title": "Welcome to Our Service",
  "greeting_body": "Please complete your registration.",
  "greeting_parameters": {},
  "contact_params": {},
  "callback": {
    "url": "https://internal.example.com/on-user-created",
    "method": "POST"
  }
}
```

**Response Example (Success):**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": true,
  "invitation_code": "invitation:550e8400-e29b-41d4-a716-446655440000"
}
```

**Request JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `mailaddr` | string | Invitation target email address |
| `greeting_title` | string | Email subject line |
| `greeting_body` | string | Email body text |
| `greeting_parameters` | object | Template parameters for the greeting email |
| `contact_params` | object | Additional contact metadata |
| `callback` | object | Optional callback task to fire after account creation |
| `callback.url` | string | Callback URL (Cloud Tasks target) |
| `callback.method` | string | HTTP method for callback (`POST`) |

**Response JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `$.status` | boolean | `true` on success |
| `$.invitation_code` | string | Invitation code string (used to track the invitation) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Invitation email sent |
| `401 Unauthorized` | Missing or invalid client credentials |
| `409 Conflict` | Email address already active |

---

### GET /call

**Display call invitation confirmation page.**

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Invitation code |

---

### POST /call

**Confirm call invitation and send completion email.**

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Invitation code |

---

### GET /call/auth

**Display password setting form for call-based invitation.**

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Email verification code |

---

### POST /call/auth

**Complete call-based invitation, set password, and fire optional callback.**

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Email verification code |
| `password` | string | Password (minimum 8 characters) |
| `password2` | string | Password confirmation |

**Business Logic Notes:**

- Upon successful account creation, if a `callback` was provided in `POST /call/user`, a Cloud Tasks task is enqueued with the new user's IWI User ID and Salesforce Contact ID.
- Invitation codes have a 20-year expiry (long-lived for external system integrations).

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Account created — success page displayed |
| `400 Bad Request` | Code invalid or password mismatch |

---

## Email Change (Login Required)

These endpoints require the user to already be logged in (valid `iwi-state` session cookie with user_id set).

### GET /user/email

**Display email change form.**

*(Authorization header not required — session required)*

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Email change form displayed (includes CSRF token) |
| `302 Found` | Not logged in — redirected to login page |

---

### POST /user/email

**Submit new email address** — validates the new address, checks Salesforce and NewsPicks for conflicts, and sends a verification email to the new address.

*(Authorization header not required — session required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mailaddr` | string | New email address |
| `csrf_token` | string | CSRF prevention token from the form |

**Business Logic Notes:**

- If the user's Salesforce Contact has a linked NewsPicks (`NPAddress__c`) account that is a paid subscriber, the email change is blocked.
- The verification email is sent to the **new** address. The change is not applied until the user confirms.

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Verification email sent — confirmation page displayed |
| `400 Bad Request` | Invalid parameters, CSRF failure, or business rule block |
| `302 Found` | Not logged in |
| `409 Conflict` | New email address already in use |

---

### GET /user/email/auth

**Display email change confirmation page** — shown when the user clicks the verification link in the email sent to the new address.

*(Authorization header not required — session required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Email change verification code |

---

### POST /user/email/auth

**Apply email change** — calls the downstream user01 service to update the email mapping.

*(Authorization header not required — session required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Email change verification code |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Email changed successfully — success page displayed |
| `400 Bad Request` | Code invalid or expired |
| `302 Found` | Not logged in |

---

## Password Reset

### GET /reset

**Display password reset email entry form.**

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-reset redirect URI |
| `scope` | string | Not currently used |
| `state` | string | Unique CSRF-prevention value (required) |
| `return_path` | string | URI to navigate to after reset completion (optional) |

---

### POST /reset

**Request password reset email** — sends a reset link to the specified email if it matches a registered account.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mailaddr` | string | Registered email address |
| `response_type` | string | Must be `code` (required) |
| `client_id` | string | IWI-issued UUID for the client (required) |
| `redirect_uri` | string | Post-reset redirect URI |
| `scope` | string | Not currently used |
| `state` | string | Unique CSRF-prevention value (required) |
| `csrf_token` | string | CSRF prevention token from the form |
| `g-recaptcha-response` | string | Google reCAPTCHA browser response value |
| `return_path` | string | URI to navigate to after reset completion (optional) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Reset email sent (or silently ignored if email not found, to prevent enumeration) |
| `400 Bad Request` | CSRF or reCAPTCHA failure |

---

### GET /reset/auth

**Display new password entry form** — after clicking the reset link in the email.

*(Authorization header not required)*

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `k` | string | Password reset code from the email link |

---

### POST /reset/auth

**Apply new password** — validates the reset code and updates the user's password hash.

*(Authorization header not required)*

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Password reset code |
| `password` | string | New password (minimum 8 characters) |
| `password2` | string | Password confirmation |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `302 Found` | Password reset — redirects to `redirect_uri` with authorization code |
| `200 OK` | Password mismatch — form re-displayed |
| `400 Bad Request` | Reset code invalid or expired |

---

## JavaScript (XHR) Usage Notes

When using JavaScript (XMLHttpRequest or Fetch) to call userauth01 from a Service Provider page, the following rules apply.

### Accept Header

Include `Accept: application/json` in the request headers so that IWI responds with JSON (for login failure, etc.) rather than HTML.

### Credentials

The `iwi-state` session cookie must be sent and received by the browser. Enable credentials in your request:

**jQuery example:**

```javascript
$.ajax({
  type: 'POST',
  url: 'https://iwi.userlogin.example.com/login',
  headers: {
    'Accept': 'application/json'
  },
  cache: false,
  dataType: 'text',
  xhrFields: {
    withCredentials: true
  },
  data: form.serialize(),
  success: function(data) {
    // handle response
  }
});
```

**Fetch API example:**

```javascript
fetch('https://iwi.userlogin.example.com/login', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Accept': 'application/json'
  },
  body: new FormData(form)
});
```

### CORS Configuration at redirect_uri

After a successful login, the browser receives a `302 Found` redirect to `redirect_uri`. Because this follows a request from a privacy-sensitive context, the browser sends `Origin: null`. The server at `redirect_uri` must respond with:

```http
Access-Control-Allow-Origin: null
Access-Control-Allow-Credentials: true
```

See RFC 6454 §7.3 for details.

---

## Error Responses

### Standard JSON Error

```http
HTTP/1.1 <4xx> <Status>
Content-Type: application/json

{
  "status": false,
  "error": "<error_code>",
  "error_details": ["<details>"]
}
```

**Error Codes:**

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `PARAMETER_SPEC_ERROR` | 400 | Missing required parameter |
| `PARAMETER_VALUE_ERROR` | 400 | Parameter value is invalid |
| `CONFLICTED_STATE` | 409 | Resource is in a conflicting state (e.g., email already in use, IN_PROGRESS) |
| `RESOURCE_ERROR` | 400/404 | Referenced resource not found or invalid |

### Conflict Response Example

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "status": false,
  "error": "CONFLICTED_STATE",
  "error_details": ["user@example.com"]
}
```

---

## Data Models

### AuthUser

IWI user account stored in Cloud Datastore.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | IWI User ID (primary key) |
| `mailaddr` | string | Primary email address |
| `password` | object | `{algorithm, salt, stretch, hash}` |
| `password.algorithm` | string | `"sha512"` (default) or `"md5"` (legacy) |
| `password.salt` | string | UUID-based random salt |
| `password.stretch` | integer | Number of hash iterations (default: 10000) |
| `password.hash` | string | Derived key hex string |
| `primary_id` | string | ID after account merge/rename |
| `version` | string (UUID) | Optimistic concurrency control |
| `invalidated` | string or null | Timestamp if account is disabled; `null` if active |

### AuthMail2ID

Email-to-IWI-User-ID mapping.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Email address (key) |
| `user_id` | string | Associated IWI User ID |
| `version` | string (UUID) | Optimistic concurrency control |
| `invalidated` | string or null | `null` (active), `"IN_PROGRESS"` (being changed), or timestamp (disabled) |

### AuthSession

User session — tied to the `iwi-state` cookie.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Session ID (value of `iwi-state` cookie) |
| `user_id` | string or null | Logged-in IWI User ID; `null` if not yet logged in |
| `version` | string (UUID) | Optimistic concurrency control |
| `revoked_at` | string or null | Timestamp if session is revoked |

### UserAuthRegister

Email verification token for registration, password reset, and invitation flows.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Verification code (key) |
| `mailaddr` | string | Email address being registered/reset |
| `return_path` | string or null | Post-completion redirect URI |
| `oauth_params` | object | OAuth parameters embedded in the token |
| `expired_at` | string | Expiry timestamp (1 hour for registration/reset) |
| `registered_at` | string or null | When the token was consumed (`null` until used) |

---

*© Funai Soken Digital — IWI Documentation*
