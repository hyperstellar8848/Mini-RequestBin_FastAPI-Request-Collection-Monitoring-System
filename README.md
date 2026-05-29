## 💾 Database Schema Design

### 1. User Table (`users`)
| Field | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Unique internal account identifier |
| `username` | String | Unique, Not Null | Chosen user handle / identification |
| `api_key` | String | Unique, Not Null | Auto-generated UUID string token |
| `created_at` | DateTime | Default: UTC Now | Account timestamp marker |

### 2. Inbox Table (`inboxes`)
| Field | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Unique container identifier |
| `user_id` | Integer | ForeignKey (`users.id`) | Relational link to the owner account |
| `name` | String | Not Null | Display name for management panels |
| `slug` | String | Unique, Not Null | URL tracking key (e.g., `parmida-box`) |
| `is_active` | Boolean | Default: `True` | Toggle to accept or block traffic |
| `created_at` | DateTime | Default: UTC Now | Inbox creation timestamp |

### 3. Entry Table (`entries`)
| Field | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Individual log identifier |
| `inbox_id` | Integer | ForeignKey (`inboxes.id`) | Target collection bin destination |
| `method` | String | Not Null | HTTP method verb (POST, GET, etc.) |
| `query_params`| String (Text) | Not Null | Reconstructed JSON structure of URL tokens |
| `headers` | String (Text) | Not Null | Reconstructed JSON structure of request headers |
| `body` | String (Text) | Nullable | Raw payload content storage string |
| `content_type`| String | Nullable | Content mime-type string attribute |
| `ip_address` | String | Nullable | Client remote sender internet protocol address |
| `user_agent` | String | Nullable | Identifier fingerprint of user browser client |
| `created_at` | DateTime | Default: UTC Now | Exact payload capture timestamp |

---

## 📡 Operational Middlewares & Exception Handlers

### Global Request Tracking
Every operational endpoint automatically triggers a background middleware tracker that completes the following execution sequence:
1. Generates an 8-character unique alphanumeric string identifier (`id_request`).
2. Benchmarks execution timeline processing constraints.
3. Implants response tracking meta-tags (`X-ID-Request` and `X-Time-Process`).
4. Logs an aligned execution string out to the active standard output console:
   ```text
   [abc12def] GET /inboxes/ → 200 (0.0045s)
### Standardized Error Format
Fault operations, missing resources, or access control violations are safely caught by a global exception handler. It formats the server error payload down to this structured format:

```json
{
  "detail": "Inbox not found",
  "error_code": "NOT_FOUND",
  "request_id": "abc12def"
}
```
# 🗺️ API Specification & Endpoints

## 🔑 Authentication / Registration

### Register User
`POST /auth/register/`

### Request Body
```json
{
  "username": "parmida"
}
```

### Response Body
```json
{
  "username": "parmida",
  "api_key": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

# 📦 Inbox Management
> Requires `X-API-Key` Header

## Create Inbox
`POST /inboxes/`

Generates a custom webhook destination box using specific payload keys (`name`, `slug`).

### Request Example
```json
{
  "name": "Main Inbox",
  "slug": "parmida-box"
}
```

---

## List Inboxes
`GET /inboxes/`

Lists all active and inactive collection mailboxes associated with the credential token.

---

## Get Inbox Details
`GET /inboxes/{inbox_id}/`

Returns granular properties for a specific inbox.

---

## Update Inbox
`PATCH /inboxes/{inbox_id}/`

Updates configuration attributes such as:

- `name`
- `is_active`

### Request Example
```json
{
  "name": "Updated Inbox",
  "is_active": true
}
```

---

## Delete Inbox
`DELETE /inboxes/{inbox_id}/`

Destroys an inbox instance along with cascading logs linked to it.

---

# 📥 Webhook Trapper
> Public Endpoint

## Capture Incoming Payloads
`ANY /collect/{slug}/`

Intercepts arbitrary payloads without token validation rules.

The system extracts:

- Structural parameters
- Client states
- Metadata headers
- Request bodies

All collected data is committed directly into the relational database engine.

---

# 🔍 Log Inspection & Diagnostics
> Requires `X-API-Key` Header

## List Request Logs
`GET /inboxes/{inbox_id}/requests/`

Paginated listing interface featuring:

- Customizable page sizes (`page`, `size`)
- Structural filtering (`method`)

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Pagination page number |
| `size` | integer | Number of entries per page |
| `method` | string | Filter by HTTP method |

---

## Get Request Log Details
`GET /inboxes/{inbox_id}/requests/{entry_id}/`

Returns a full payload recreation dashboard including:

- Structured data mappings
- Body contexts
- Header tracking sets

---

## Delete Request Logs
`DELETE /inboxes/{inbox_id}/requests/`

Purges all history tracking structures inside an inbox container.

---

# 📊 Performance Analytics
> Requires `X-API-Key` Header

## Overview Metrics
`GET /stats/overview/`

Metrics hub calculating resource footprints and activity trends over a rolling 24-hour window.

### Example Response
```json
{
  "total_inboxes": 3,
  "active_inboxes": 2,
  "total_requests": 57,
  "last_24h_requests": 11
}
```

---

# 🏁 Installation & Quickstart

## 1. Setup Environment

Ensure Python dependencies are installed globally or within a virtual environment.

### Install Dependencies
```bash
pip install fastapi uvicorn sqlalchemy
```

---

## 2. Start Application Server

Run the ASGI framework runner from the project root.

### Launch Command
```bash
uvicorn main:app --reload
```

---

## 3. Access Dashboards

Once the application starts successfully at:

```text
http://127.0.0.1:8000
```

You can access:

| Service | URL |
|---|---|
| Functional UI | `http://localhost:8000/` |
| Swagger API Docs | `http://localhost:8000/docs` |

---

# 🧪 Terminal Testing Commands

## Account Provisioning Trace

### Windows CMD Example
```cmd
curl -X POST "http://localhost:8000/auth/register/" ^
-H "Content-Type: application/json" ^
-d "{\"username\":\"parmida\"}"
```

---

## Remote Webhook Injection Simulation

### Windows CMD Example
```cmd
curl -X POST "http://localhost:8000/collect/parmida-box/" ^
-H "Content-Type: application/json" ^
-d "{\"message\":\"hello webhook\"}"
```
