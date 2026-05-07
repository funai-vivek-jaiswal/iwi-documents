[← Back to Index](../README.md)

# userauth01 — Screen Transition Diagram

**Service:** PJ_IWI_USERAUTH  
**Templates:** `PJ_IWI_USERAUTH/template/*.html.jinja2`

---

## Table of Contents

- [Overview Diagram](#overview-diagram)
- [Flow A — User-Initiated Registration (新規登録)](#flow-a--user-initiated-registration)
- [Flow B — Password Reset (パスワード再設定)](#flow-b--password-reset)
- [Flow C — KK Call Invitation](#flow-c--kk-call-invitation)
- [Flow D — SFDC Invitation (Salesforce 招待)](#flow-d--sfdc-invitation)
- [Flow E — Email Address Change (メールアドレス変更)](#flow-e--email-address-change)
- [Shared Screens](#shared-screens)
- [Screen Index](#screen-index)

---

## Overview Diagram

All five user-facing flows — colour-coded by flow.

![Screen Transition Overview](../Screen_Design_Document/images/00_screen_transition_diagram.png)

---

## Flow A — User-Initiated Registration

A new user registers by entering their email, verifying it via email link, and setting a password.

**Screens in order:**

| Step | Screenshot | Template | Route |
|------|-----------|----------|-------|
| 1. Entry | ![Login](../Screen_Design_Document/images/01_login.png) | `login.html.jinja2` | `GET /login` |
| 2. Enter email | ![Register](../Screen_Design_Document/images/02_register.png) | `register.html.jinja2` | `GET/POST /register` |
| 3. Email sent | ![Message](../Screen_Design_Document/images/17_message.png) | `message.html.jinja2` | `REGISTER-M001` |
| 4. Set password | ![Register Password](../Screen_Design_Document/images/03_register_password.png) | `register_password.html.jinja2` | `GET /register/auth` |
| 5. Complete | ![Register Success](../Screen_Design_Document/images/04_register_success.png) | `register_success.html.jinja2` | `POST /register/auth` |

**Transition:**

```
Login ──[新規登録 click]──▶ /register ──[POST + reCAPTCHA]──▶ message(REGISTER-M001)
  ──[📧 email link click]──▶ /register/auth ──[POST password]──▶ register_success
  ──▶ MyPage / return_path
```

---

## Flow B — Password Reset

A registered user who forgot their password requests a reset email and sets a new password.

**Screens in order:**

| Step | Screenshot | Template | Route |
|------|-----------|----------|-------|
| 1. Entry | ![Login](../Screen_Design_Document/images/01_login.png) | `login.html.jinja2` | `GET /login` |
| 2. Enter email | ![Reset](../Screen_Design_Document/images/05_reset.png) | `reset.html.jinja2` | `GET/POST /reset` |
| 3. Email sent | ![Message](../Screen_Design_Document/images/17_message.png) | `message.html.jinja2` | `RESET-M001` |
| 4. New password | ![Reset Password](../Screen_Design_Document/images/06_reset_password.png) | `reset_password.html.jinja2` | `GET /reset/auth` |
| 5. Complete | ![Reset Success](../Screen_Design_Document/images/07_reset_success.png) | `reset_success.html.jinja2` | `POST /reset/auth` |

**Transition:**

```
Login ──[パスワード忘れ click]──▶ /reset ──[POST + reCAPTCHA]──▶ message(RESET-M001)
  ──[📧 email link click]──▶ /reset/auth ──[POST password]──▶ reset_success
  ──▶ Login / return_path
```

---

## Flow C — KK Call Invitation

An external system (KK Call) invites a user. The user confirms their address and sets a password. A callback is fired to the external system on completion.

**Screens in order:**

| Step | Screenshot | Template | Route |
|------|-----------|----------|-------|
| 1. Admin sends invite | *(external system — POST /call/user)* | — | `POST /call/user` |
| 2. Confirm email | ![Call](../Screen_Design_Document/images/08_call.png) | `call.html.jinja2` | `GET /call?k=...` |
| 3. Email sent | ![Message](../Screen_Design_Document/images/17_message.png) | `message.html.jinja2` | `CALL-M001` |
| 4. Set password | ![Call Password](../Screen_Design_Document/images/09_call_password.png) | `call_password.html.jinja2` | `GET /call/auth` |
| 5. Complete | ![Call Success](../Screen_Design_Document/images/10_call_success.png) | `call_success.html.jinja2` | `POST /call/auth` |

**Transition:**

```
ExtSys POST /call/user ──[📧 invite email]──▶ /call?k=... ──[POST confirm]──▶ message(CALL-M001)
  ──[📧 completion email]──▶ /call/auth ──[POST password]──▶ call_success ──▶ MyPage
```

---

## Flow D — SFDC Invitation

A Salesforce workflow creates an IWI account stub and invites the user to set their password.

**Screens in order:**

| Step | Screenshot | Template | Route |
|------|-----------|----------|-------|
| 1. SFDC sends invite | *(POST /register/sfdc)* | — | `POST /register/sfdc` |
| 2. Confirm email | ![Invite SFDC](../Screen_Design_Document/images/11_invite_sfdc.png) | `invite_sfdc.html.jinja2` | `GET /invite?k=...` |
| 3. Email sent | ![Message](../Screen_Design_Document/images/17_message.png) | `message.html.jinja2` | `INVITE-M001` |
| 4. Set password | ![Invite Password](../Screen_Design_Document/images/12_invite_sfdc_password.png) | `invite_sfdc_password.html.jinja2` | `GET /invite/auth` |
| 5. Complete | ![Invite Success](../Screen_Design_Document/images/13_invite_sfdc_success.png) | `invite_sfdc_success.html.jinja2` | `POST /invite/auth` |

**Transition:**

```
SFDC POST /register/sfdc ──[📧 invite email]──▶ /invite?k=... ──[POST confirm]──▶ message(INVITE-M001)
  ──[📧 completion email]──▶ /invite/auth ──[POST password]──▶ invite_sfdc_success ──▶ MyPage
```

---

## Flow E — Email Address Change

A logged-in user changes their primary login email address. The new address is verified before the change is applied.

**Screens in order:**

| Step | Screenshot | Template | Route |
|------|-----------|----------|-------|
| 1. Entry | *(MyPage — logged in)* | — | `GET /user/email` |
| 2. Enter new email | ![Update Email](../Screen_Design_Document/images/14_update_email.png) | `update_email.html.jinja2` | `GET/POST /user/email` |
| 3. Email sent | ![Message](../Screen_Design_Document/images/17_message.png) | `message.html.jinja2` | `UPDATE-EMAIL-M001` |
| 4. Confirm change | ![Update Confirm](../Screen_Design_Document/images/15_update_email_confirm.png) | `update_email_confirm.html.jinja2` | `GET /user/email/auth` |
| 5. Complete | ![Update Success](../Screen_Design_Document/images/16_update_email_success.png) | `update_email_success.html.jinja2` | `POST /user/email/auth` |

**Transition:**

```
MyPage ──▶ /user/email ──[POST new email + CSRF]──▶ message(UPDATE-EMAIL-M001)
  ──[📧 email to NEW address]──▶ /user/email/auth ──[POST confirm]──▶ update_email_success
  ──▶ MyPage
```

---

## Shared Screens

These templates are used across multiple flows.

### login.html.jinja2

![Login Screen](../Screen_Design_Document/images/01_login.png)

Entry point for all flows. Provides links to Register (Flow A) and Password Reset (Flow B).

---

### message.html.jinja2

![Message Screen](../Screen_Design_Document/images/17_message.png)

Multi-state screen controlled by `message_id`. Used in all flows after email dispatch and for error states.

| `message_id` | Displayed for |
|---|---|
| `REGISTER-M001` | Flow A — registration email sent |
| `RESET-M001` | Flow B — password reset email sent |
| `CALL-M001` / `INVITE-M001` | Flows C/D — invitation completion email sent |
| `UPDATE-EMAIL-M001` | Flow E — email change verification sent |
| `*-E003` / `*-E004` / `*-E005` | Email send failure / token not found |

---

### error.html.jinja2

![Error Screen](../Screen_Design_Document/images/18_error.png)

System error page. Rendered when any unhandled backend exception occurs.

---

## Screen Index

| # | Template | Page Title (JA) | Route | Flow |
|---|----------|-----------------|-------|------|
| 01 | `login.html.jinja2` | ログイン | `GET/POST /login` | All |
| 02 | `register.html.jinja2` | 新規登録 — メールアドレス入力 | `GET/POST /register` | A |
| 03 | `register_password.html.jinja2` | 新規登録 — パスワード設定 | `GET /register/auth` | A |
| 04 | `register_success.html.jinja2` | 新規登録 完了 | `POST /register/auth` | A |
| 05 | `reset.html.jinja2` | パスワード再設定 — メール入力 | `GET/POST /reset` | B |
| 06 | `reset_password.html.jinja2` | パスワード再設定 — 新PW設定 | `GET /reset/auth` | B |
| 07 | `reset_success.html.jinja2` | パスワード再設定 完了 | `POST /reset/auth` | B |
| 08 | `call.html.jinja2` | 新規会員登録のご案内 — メール確認 | `GET /call?k=...` | C |
| 09 | `call_password.html.jinja2` | 新規登録 — パスワード登録 | `GET /call/auth` | C |
| 10 | `call_success.html.jinja2` | パスワード登録 完了 | `POST /call/auth` | C |
| 11 | `invite_sfdc.html.jinja2` | 新規会員登録のご案内 — メール確認 (SFDC) | `GET /invite?k=...` | D |
| 12 | `invite_sfdc_password.html.jinja2` | 新規登録 — パスワード登録 (SFDC) | `GET /invite/auth` | D |
| 13 | `invite_sfdc_success.html.jinja2` | パスワード登録 完了 (SFDC) | `POST /invite/auth` | D |
| 14 | `update_email.html.jinja2` | メールアドレス変更 — 新メール入力 | `GET/POST /user/email` | E |
| 15 | `update_email_confirm.html.jinja2` | メールアドレス変更 — 確認 | `GET /user/email/auth` | E |
| 16 | `update_email_success.html.jinja2` | メールアドレス変更 完了 | `POST /user/email/auth` | E |
| 17 | `message.html.jinja2` | ご確認ください (multi-state) | `/message?id=...` | All (shared) |
| 18 | `error.html.jinja2` | システムエラー | `/error` | All (shared) |

---

*© Funai Soken Digital — IWI Documentation*
