[← Back to Index](../README.md)

# oauth01 Service — API Reference

**Service:** PJ_IWI_RECONS  
**Service Name:** oauth01  
**Purpose:** OAuth 2.0 Authorization Server — implements the Authorization Code Grant flow (RFC 6749) for issuing access tokens and refresh tokens to registered client applications.

---

## Table of Contents

- [Common Standards](#common-standards)
- [GET /](#get-)
- [POST /requesttoken](#post-requesttoken)
- [POST /refreshtoken](#post-refreshtoken)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Common Standards

### Authorization Header

Internal client authentication uses HTTP Basic Authentication (RFC 7617).

```
Authorization: Basic <base64(client_id:client_secret)>
```

### Content-Type

Token endpoints accept `application/x-www-form-urlencoded` request bodies.

### Token Format

All tokens (authorization codes, access tokens, refresh tokens) are UUID v4 strings.  
Example: `550e8400-e29b-41d4-a716-446655440000`

---

## GET /

Health check endpoint. Returns service identity and status.

**Response Example (Success):**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "service": "oauth01"
}
```

**Response JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `$.status` | string | Always `"ok"` |
| `$.service` | string | Service name identifier |

**Status Codes:**

| Code | Meaning |
|------|---------|
| `200 OK` | Service is running normally |

---

## POST /requesttoken

**Access Token Request** — corresponds to the Access Token Request defined in RFC 6749 §4.1.3.

Exchanges a valid authorization code for an access token and a refresh token.

**Request Example:**

```http
POST /requesttoken HTTP/1.1
Host: oauth.example.com
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=550e8400-e29b-41d4-a716-446655440000&redirect_uri=https://app.example.com/callback
```

**Response Example (Success):**

```http
HTTP/1.1 200 OK
Content-Type: application/json;charset=UTF-8
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "2YotnFZFEjr1zCsicMWpAA",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "iwi_user_id": "5e87c5bb-847e-4bb2-9cbd-c26b6a33a799"
}
```

**Response Example (Failure):**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json;charset=UTF-8
Cache-Control: no-store
Pragma: no-cache

{
  "error": "invalid_grant",
  "error_description": "The authorization code is invalid or has expired.",
  "state": "xyz"
}
```

For `error` and `error_description` details, refer to RFC 6749 §5.2 Error Response.

**Client Authentication:**

Either HTTP Basic Authentication or form body parameters. Basic Auth is preferred.

| Method | Description |
|--------|-------------|
| Basic Auth | `Authorization: Basic base64(client_id:client_secret)` |
| Form body | Include `client_id` and `client_secret` as form fields |

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `grant_type` | string | Must be `authorization_code` (required) |
| `code` | string | Authorization code received from the userauth01 `/login` redirect (required) |
| `redirect_uri` | string | Must exactly match the `redirect_uri` used in the userauth01 login request (required if provided at login time) |
| `client_id` | string | OAuth client UUID. Required if not using Basic Auth. |
| `client_secret` | string | OAuth client secret. Required if not using Basic Auth. |

**Response JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `$.access_token` | string | Bearer token representing the user's authorization |
| `$.token_type` | string | Always `"Bearer"` |
| `$.expires_in` | integer | Token validity period in seconds (3600 = 1 hour) |
| `$.refresh_token` | string | Token used for future access token refresh |
| `$.iwi_user_id` | string | IWI User ID of the authorizing user |
| `$.error` | string | Error identifier string (on failure only) |
| `$.error_description` | string | Error detail message (on failure only, may be omitted) |
| `$.state` | string | State value from the authorization request (on failure only, may be omitted) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Token issued successfully |
| `400 Bad Request` | Invalid code, expired code, redirect_uri mismatch, or replay detected |
| `401 Unauthorized` | Missing or invalid client credentials |

**Business Logic Notes:**

- Access token lifetime: **1 hour** (3600 seconds).
- Refresh token has a **60-second reuse window** — within this window, the same access token is returned for concurrent refresh requests.
- If the authorization code has already been used once, it is immediately revoked and the request is rejected (replay attack prevention).
- Access tokens are bound to the issuing client. A token cannot be used with a different `client_id`.
- Access tokens are bound to the session. Revoking the session invalidates all associated tokens.

---

## POST /refreshtoken

**Access Token Refresh** — corresponds to the Refreshing an Access Token operation defined in RFC 6749.

Exchanges a valid refresh token for a new access token. The refresh token itself is **not** rotated — the same refresh token continues to be valid for future refreshes (within its validity period).

**Request Example:**

```http
POST /refreshtoken HTTP/1.1
Host: oauth.example.com
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=tGzv3JOkF0XG5Qx2TlKWIA
```

**Response Example (Success):**

```http
HTTP/1.1 200 OK
Content-Type: application/json;charset=UTF-8
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "3ZpuoGAGFks2aDtjdNLXBB",
  "token_type": "Bearer",
  "expires_in": 3600,
  "iwi_user_id": "5e87c5bb-847e-4bb2-9cbd-c26b6a33a799"
}
```

**Response Example (Failure):**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json;charset=UTF-8
Cache-Control: no-store
Pragma: no-cache

{
  "error": "invalid_grant",
  "error_description": "Missing refresh token parameter."
}
```

For `error` and `error_description` details, refer to RFC 6749 §5.2 Error Response.

**Client Authentication:**

Same as `/requesttoken` — HTTP Basic Auth (preferred) or form body parameters.

**Form Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `grant_type` | string | Must be `refresh_token` (required) |
| `refresh_token` | string | Refresh token received from the previous token issuance (required) |
| `client_id` | string | OAuth client UUID. Required if not using Basic Auth. |
| `client_secret` | string | OAuth client secret. Required if not using Basic Auth. |

**Response JSON Object:**

| Field | Type | Description |
|-------|------|-------------|
| `$.access_token` | string | New bearer token representing the user's authorization |
| `$.token_type` | string | Always `"Bearer"` |
| `$.expires_in` | integer | Token validity period in seconds (3600 = 1 hour) |
| `$.iwi_user_id` | string | IWI User ID of the authorizing user |
| `$.error` | string | Error identifier string (on failure only) |
| `$.error_description` | string | Error detail message (on failure only, may be omitted) |

**Status Codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | New access token issued successfully |
| `400 Bad Request` | Invalid or expired refresh token |
| `401 Unauthorized` | Missing or invalid client credentials |

**Business Logic Notes:**

- The response does **not** include a new `refresh_token`. The client must continue using the same refresh token for subsequent refreshes.
- The refresh token validates against: token existence, expiry, revocation status, session activity, and root authorization code validity.
- If the session is revoked, the refresh token becomes invalid.

---

## Error Responses

Standard error response shape follows RFC 6749 §5.2:

```http
HTTP/1.1 <4xx> <Status Text>
Content-Type: application/json;charset=UTF-8
Cache-Control: no-store
Pragma: no-cache

{
  "error": "<error_code>",
  "error_description": "<human readable message>",
  "state": "<state from request>"
}
```

**Common Error Codes:**

| Error Code | HTTP Status | Meaning |
|------------|-------------|---------|
| `invalid_request` | 400 | Missing or invalid parameter |
| `invalid_client` | 401 | Unknown client or wrong credentials |
| `invalid_grant` | 400 | Invalid, expired, or already-used authorization code; invalid refresh token |
| `unauthorized_client` | 400 | Client not authorized for the requested grant type |
| `unsupported_grant_type` | 400 | `grant_type` value is not supported |
| `invalid_scope` | 400 | Requested scope is invalid or exceeds the original scope |

---

## Data Models

### AuthClient

Registered OAuth client application.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Client identifier |
| `name` | string | Human-readable client name |
| `secret` | string | Client authentication secret |
| `services` | object | Dict of permitted service names (keys) |
| `info.oauth2.known_redirect_hosts` | array of strings | Allowed redirect URI hosts |
| `info.oauth2.default_redirect_uri` | string | Default redirect URI (used when `redirect_uri` is omitted) |
| `invalidated` | string or null | Timestamp if client is disabled; `null` if active |

### AuthSession

User session managed via `iwi-state` cookie.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Session identifier (value of `iwi-state` cookie) |
| `user_id` | string or null | Logged-in IWI User ID; `null` if not logged in |
| `tokens` | object | Dict of `{client_id: [(token, expired_at), ...]}` |
| `version` | string (UUID) | Concurrency control version |
| `revoked_at` | string or null | Timestamp if session is revoked; `null` if active |

### AuthOAuthCode

Authorization code issued internally by userauth01 (via `/login`).

| Field | Type | Description |
|-------|------|-------------|
| `code` | string (UUID) | The authorization code (key) |
| `user_id` | string | IWI User ID who authorized |
| `client_id` | string | Client that requested the code |
| `scope` | string | Space-separated scopes |
| `redirect_uri` | string | Redirect URI specified at authorization time |
| `expired_at` | string | Expiry timestamp (10 minutes from issuance) |
| `session_id` | string | Associated session ID |
| `access_token` | string or null | Token issued from this code (set on first use) |
| `revoked_at` | string or null | Timestamp if revoked (e.g., replay detected) |

### AuthOAuthAccessToken

Access token issued by `/requesttoken` or `/refreshtoken`.

| Field | Type | Description |
|-------|------|-------------|
| `token` | string (UUID) | The access token (key) |
| `user_id` | string | IWI User ID |
| `client_id` | string | Issuing client |
| `scope` | string | Granted scopes |
| `expired_at` | string | Expiry timestamp (1 hour from issuance) |
| `session_id` | string | Associated session ID |
| `source_type` | string | `"authcode"` or `"refresh_token"` |
| `source_id` | string | ID of the source code or refresh token |
| `root_code` | string or null | Original authorization code |
| `revoked_at` | string or null | Timestamp if revoked |

### AuthOAuthRefreshToken

Refresh token issued alongside an access token.

| Field | Type | Description |
|-------|------|-------------|
| `token` | string (UUID) | The refresh token (key) |
| `user_id` | string | IWI User ID |
| `client_id` | string | Issuing client |
| `scope` | string | Granted scopes |
| `session_id` | string | Associated session ID |
| `expired_at` | string or null | Expiry timestamp (60-second reuse window) |
| `access_token` | string or null | Last access token issued from this refresh token |
| `root_code` | string or null | Original authorization code |
| `revoked_at` | string or null | Timestamp if revoked |

---

*Reference: RFC 6749 — The OAuth 2.0 Authorization Framework*  
*© Funai Soken Digital — IWI Documentation*
