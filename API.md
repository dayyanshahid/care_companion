# Care Companion — Backend API Reference

Everything the frontend needs to integrate with the Care Companion enrollment
backend. There is no authentication on any endpoint, CORS is open to all
origins, and every request/response body is JSON. Every `/api/chat/` request
must name its tenant — see section 2.

---

## 1. Base URL

| Environment | Base URL |
|---|---|
| Local | `http://localhost:8000` |
| Deployed | whatever host the backend is served from |

All routes are prefixed with `/api/`.

```js
const API_BASE = "http://localhost:8000";
const API = `${API_BASE}/api`;
```

**Headers for every request that has a body:**

```
Content-Type: application/json
```

---

## 2. Choosing the tenant

The backend serves every practice on the platform, and each one keeps its
patients in its own database. Which database to read is decided per request,
from one header:

```
X-Tenant: https://primecare.ran-ai.co
```

It is **required on every `/api/chat/` endpoint**. There is no default tenant
— without the header nothing is served, because guessing one would read
another practice's patients.

**What to send.** The subdomain the frontend is running on. The backend looks
it up in the central admin portal's `tenants` collection and reads that
tenant's `dbUri`. Matching is forgiving, so all of these find Prime Care:

| Sent | |
|---|---|
| `https://primecare.ran-ai.co` | a whole URL — usually just `location.origin` |
| `primecare.ran-ai.co` | a bare host |
| `primecare` | the tenant's short key |

A port is significant, since several tenants are served from `localhost`:
`http://localhost:3009` and `http://localhost:3003` are different tenants.

**Failures**

| Code | When | Message |
|---|---|---|
| `400` | header absent or empty | `The X-Tenant header is required.` |
| `404` | no tenant serves that subdomain | `No tenant is served at '…'.` |
| `502` | the tenant registry cannot be read | `The tenant registry is unavailable right now. Please try again.` |

**The patient chat link.** `chat_link` is built on the tenant's **own
subdomain**, taken from its registry record, so a patient lands on their own
practice's site:

```
https://primecare.ran-ai.co/chat/conv_6a96659bf5ac8194af7881a4…
└────── tenant subdomain ─────┘└chat┘└──────── conv_id ────────┘
```

The host comes from the tenant and the route from the `FRONTEND_PATH` setting
(`/chat` by default). There is no fallback host: a tenant whose record names
no subdomain is not served at all — it is skipped by the registry, and naming
it returns `404` like any unknown tenant.

Nothing rides in the query string, because the host already says which tenant
it is. Route `/chat/:conv_id`, read the conversation off the path, and send
`location.origin` as `X-Tenant`.

`POST /api/knowledge/search` needs no tenant: the FAQ is one shared knowledge
base, not per-practice.

---

## 3. Scripted replies

Some replies are not generated. The assistant decides which situation applies
and the backend substitutes wording reviewed by legal
(`Care_Companion_AI_Enrollment_Scripts_Refined_8.28.26`), so the patient always
sees the approved text rather than a paraphrase of it.

| Situation | What the patient gets | Effect on the record |
|---|---|---|
| Opening message | Template 1, sent by `/chat/start` | — |
| Ready to enroll | The seven consent points | — |
| Agrees to all seven | Welcome + care-manager promise | `status: enrolled`, `consented_at`, `consent_version` |
| Declines | Decline close, no further contact | `status: declined` |
| Wants a call | Callback acknowledgement | `status: callback` |
| Says STOP | Opt-out acknowledgement | `status: optedout` |
| Reports a symptom | 911 / emergency-room script | **`alert_at` set** |
| Mentions self-harm | 988 Suicide and Crisis Lifeline script | **`alert_at` set** |

**`alert_at` needs a human.** It is stamped the moment a patient describes a
clinical symptom, at any hour, and the assistant stops selling the programme
for the rest of that conversation. Nothing pages anyone yet, so poll
`GET /api/chat/conversations` for records with a non-null `alert_at` and work
that queue.

**STOP is handled without the model.** A message that is only `STOP`,
`UNSUBSCRIBE`, `CANCEL`, `QUIT` or `END` opts the patient out immediately and
never reaches OpenAI.

---

## 4. The response envelope

**Every** response — success or failure — comes back in the same shape. Read
`success` to branch, `result` for the payload, `message` for something you can
show the user.

### Success

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Conversations retrieved successfully.",
  "result": {}
}
```

### Error

```json
{
  "response_code": 404,
  "success": false,
  "status_code": 404,
  "message": "Chat not found.",
  "result": null,
  "error_message": "optional technical detail, may be null"
}
```

### Validation error (400)

Here `result` carries the per-field errors from the serializer:

```json
{
  "response_code": 400,
  "success": false,
  "status_code": 400,
  "message": "Validation failed.",
  "result": { "patient_id": ["This field is required."] },
  "error_message": null
}
```

### Status codes used

| Code | Meaning |
|---|---|
| `200` | OK |
| `201` | Created (chat started) |
| `400` | Validation failed / bad id / missing `X-Tenant` |
| `404` | Chat, patient, tenant or route not found |
| `405` | Wrong HTTP method for that route |
| `500` | Unhandled server error |
| `502` | Upstream unavailable (tenant registry, patient portal, OpenAI) |

> An empty list is **not** an error. `GET /chat/patients` with no patients
> returns `success: true`, `result: []`, and the message
> `"No remote patients found."`

### Suggested fetch helper

```js
const TENANT = location.origin;  // or "primecare", or the ?tenant= param

async function call(path, { method = "GET", body } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      "X-Tenant": TENANT,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await res.json();

  if (!payload.success) {
    throw new Error(payload.message || "Request failed");
  }

  return payload.result;
}
```

---

## 5. Endpoint summary

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | `GET`  | `/api/chat/patients` | List every remote patient from the portal |
| 2 | `POST` | `/api/chat/start` | Open a chat for a patient (sends the email link) |
| 3 | `POST` | `/api/chat/message` | Send a patient message, get the assistant's reply |
| 4 | `GET`  | `/api/chat/conversations` | List enrollment records (optionally per patient) |
| 5 | `GET`  | `/api/chat/conversations/{ident}` | Read a transcript, or one patient's records |
| 6 | `POST` | `/api/knowledge/search` | Search the FAQ knowledge base (RAG, for testing) |

Endpoints 1–5 require the `X-Tenant` header; 6 does not.

---

## 6. Chat endpoints

### 6.1 — List patients

Every remote patient held in the tenant's portal, newest capture first. This is
what you populate the "pick a patient" screen with.

```
GET /api/chat/patients
X-Tenant: https://primecare.ran-ai.co
```

**Request:** no body, no query params.

**Response — 200**

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Patients retrieved successfully.",
  "result": [
    {
      "patient_id": "665f1c2a9b4e7d0012ab34cd",
      "name": "Jane Doe",
      "practice": "Prime Care Clinic",
      "provider": "Dr. Alan Smith",
      "programs": ["CCM"],
      "latest_appointment_date": "2025-07-14T00:00:00Z"
    }
  ]
}
```

**Result fields**

| Field | Type | Notes |
|---|---|---|
| `patient_id` | string | 24-char Mongo ObjectId. Pass this to `/chat/start` |
| `name` | string | First + last name, may be `""` |
| `practice` | string | May be `""` |
| `provider` | string | May be `""` |
| `programs` | string[] | May be `[]` |
| `latest_appointment_date` | string | Date string, may be `""` |

**Other responses**

| Code | When | `message` |
|---|---|---|
| `200` | No patients | `"No remote patients found."` (`result: []`) |
| `502` | Portal Mongo unreachable | `"The patient portal is unavailable right now. Please try again."` |

---

### 6.2 — Start a chat

Opens a new conversation for one patient. This does several things at once:
creates/refreshes the enrollment record, opens an OpenAI conversation, writes
the opening message, and **emails the patient their chat link**.

```
POST /api/chat/start
X-Tenant: https://primecare.ran-ai.co
```

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `patient_id` | string | yes | Max 64 chars. The `patient_id` from `/chat/patients` |

```json
{ "patient_id": "665f1c2a9b4e7d0012ab34cd" }
```

**Response — 201 Created**

```json
{
  "response_code": 201,
  "success": true,
  "status_code": 201,
  "message": "Chat started.",
  "result": {
    "conv_id": "conv_abc123",
    "conv_ids": ["conv_older", "conv_abc123"],
    "patient_id": "665f1c2a9b4e7d0012ab34cd",
    "patient_name": "Jane Doe",
    "status": "active",
    "chat_link": "https://primecare.ran-ai.co/chat/conv_abc123",
    "email": "jane@example.com",
    "email_sent": true,
    "email_error": "",
    "messages": [
      {
        "role": "assistant",
        "text": "Hi Jane Doe, this is the Care Companion team's secure AI assistant, texting on behalf of Dr. Alan Smith at Prime Care Clinic. ...",
        "created_at": "2025-08-30T10:15:02.311Z"
      }
    ]
  }
}
```

**Result fields**

| Field | Type | Notes |
|---|---|---|
| `conv_id` | string | **The id you send every subsequent message with** |
| `conv_ids` | string[] | Every conversation ever opened for this patient, oldest first |
| `patient_id` | string \| null | The portal capture id |
| `patient_name` | string | |
| `status` | string | `"active"` \| `"enrolled"` \| `"declined"` \| `"callback"` \| `"optedout"` |
| `chat_link` | string | `<tenant subdomain>/chat/<conv_id>` — the link mailed to the patient |
| `email` | string | Patient's email, `""` if none on file |
| `email_sent` | boolean | `false` if the mail failed; **the chat is still valid** |
| `email_error` | string | Why it failed, `""` when it went. No address on file, or a malformed one |
| `practice_phone` | string | The practice's number, as the emergency script gives it |
| `consented_at` | string \| null | When the patient agreed to all seven consent points |
| `consent_version` | string | Which wording they agreed to, e.g. `"2026-08-28"` |
| `alert_at` | string \| null | **Set when the patient reported a clinical symptom.** A human owes them a follow-up |
| `messages` | Message[] | The transcript so far — one assistant opener |

**Message object** (used here and in 6.5)

| Field | Type | Notes |
|---|---|---|
| `role` | string | `"assistant"` or `"user"` (patient) |
| `text` | string | The message body |
| `created_at` | string | ISO 8601 UTC timestamp |

**Other responses**

| Code | When | `message` |
|---|---|---|
| `400` | `patient_id` missing/blank | `"Validation failed."` |
| `404` | No remote patient with that id | `"No remote patient with that id."` |
| `502` | Portal unreachable | `"The patient portal is unavailable right now. Please try again."` |
| `502` | OpenAI failed | `"The assistant is unavailable right now. Please try again."` |

> Calling `start` again for the same patient does **not** create a second
> record — it appends a fresh `conv_id` to the same patient's `conv_ids` and
> resets `status` to `active`.

---

### 6.3 — Send a message

Sends one patient message and returns the assistant's reply. This is the main chat loop.

```
POST /api/chat/message
X-Tenant: https://primecare.ran-ai.co
```

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `conv_id` | string | yes | From `/chat/start`, or the `?conv=` query param on the chat link |
| `text` | string | yes | The patient's message. Must be non-empty |

```json
{ "conv_id": "conv_abc123", "text": "How much does it cost?" }
```

**Response — 200**

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Message sent.",
  "result": {
    "conv_id": "conv_abc123",
    "response": "There's usually a small copay depending on your plan...",
    "status": "active"
  }
}
```

**Result fields**

| Field | Type | Notes |
|---|---|---|
| `conv_id` | string | Echoed back |
| `response` | string | The assistant's reply — render this as the assistant bubble |
| `status` | string | The chat status after this turn |

**Status values**

| Value | Meaning |
|---|---|
| `active` | Still talking — patient is undecided, asking questions, or thinking it over |
| `enrolled` | Patient agreed to all five consent points |
| `declined` | Patient clearly said no |

Use `status` to drive the UI — e.g. show a success banner on `enrolled`, a
closing note on `declined`. A patient who is undecided or wants to talk to
family first stays `active`, so keep the composer open until the status
actually changes.

> The assistant emits internal tags like `<<ENROLLED>>` in its raw output — these are
> **stripped server-side**. `response` is always clean text, safe to render.

**Other responses**

| Code | When | `message` |
|---|---|---|
| `400` | `conv_id` or `text` missing/blank | `"Validation failed."` |
| `404` | No chat holds that `conv_id` | `"Chat not found."` |
| `502` | OpenAI or the FAQ retrieval failed | `"The assistant is unavailable right now. Please try again."` |

---

### 6.4 — List conversations

Every enrollment record that has at least one conversation opened. Use it for an
admin/dashboard list, or filter to one patient to read their current status.

```
GET /api/chat/conversations
GET /api/chat/conversations?patient_id=665f1c2a9b4e7d0012ab34cd
X-Tenant: https://primecare.ran-ai.co
```

**Query params**

| Param | Type | Required | Notes |
|---|---|---|---|
| `patient_id` | string | no | Must be a valid 24-char ObjectId if supplied |

**Response — 200**

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Conversations retrieved successfully.",
  "result": [
    {
      "conv_id": "conv_abc123",
      "conv_ids": ["conv_older", "conv_abc123"],
      "patient_id": "665f1c2a9b4e7d0012ab34cd",
      "patient_name": "Jane Doe",
      "provider": "Dr. Alan Smith",
      "practice": "Prime Care Clinic",
      "recency": "year",
      "status": "active",
      "created_at": "2025-08-30T10:15:00.001Z",
      "updated_at": "2025-08-30T10:22:41.882Z"
    }
  ]
}
```

**Result fields**

| Field | Type | Notes |
|---|---|---|
| `conv_id` | string | The **newest** conversation — the live one |
| `conv_ids` | string[] | All conversations for this patient, oldest first |
| `patient_id` | string | Portal capture id |
| `patient_name` | string | |
| `provider` | string | May be `""` |
| `practice` | string | May be `""` |
| `recency` | string | `"onemonth"` or `"year"` — how long since the last visit |
| `status` | string | `active` \| `enrolled` \| `declined` |
| `created_at` / `updated_at` | string | ISO 8601 UTC |

> There is exactly **one record per patient**. Filtering by `patient_id`
> therefore returns an array of 0 or 1 items.

**Other responses**

| Code | When | `message` |
|---|---|---|
| `200` | None found | `"No conversations found."` (`result: []`) |
| `400` | `patient_id` is not a valid ObjectId | `"Not a valid patient id."` |

---

### 6.5 — Read a conversation (transcript)

One route, two behaviours, decided by what `{ident}` looks like:

```
GET /api/chat/conversations/{ident}
X-Tenant: https://primecare.ran-ai.co
```

| `{ident}` is… | You get back | `message` |
|---|---|---|
| An OpenAI conversation id (e.g. `conv_abc123`) | The **transcript** — an array of messages | `"Transcript retrieved successfully."` |
| A 24-char Mongo ObjectId (a `patient_id`) | The same array as 6.4, filtered to that patient | `"Conversations retrieved successfully."` |

**Response — 200 (transcript form)**

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Transcript retrieved successfully.",
  "result": [
    {
      "role": "assistant",
      "text": "Hi Jane Doe, this is the Care Companion team's secure AI assistant...",
      "created_at": "2025-08-30T10:15:02.311Z"
    },
    {
      "role": "user",
      "text": "How much does it cost?",
      "created_at": "2025-08-30T10:16:40.102Z"
    },
    {
      "role": "assistant",
      "text": "There's usually a small copay depending on your plan...",
      "created_at": "2025-08-30T10:16:44.775Z"
    }
  ]
}
```

Messages are ordered oldest first, so render them top-to-bottom as-is.

**Other responses**

| Code | When | `message` |
|---|---|---|
| `200` | Nothing matches that id | `"Nothing found for that id."` (`result: []`) |

> This is how the patient's chat page bootstraps: read `?conv=` from the URL,
> `GET /api/chat/conversations/<conv>` to load history, then post to
> `/api/chat/message` from there on.

---

## 7. Knowledge endpoint

### 7.1 — Search the FAQ

Semantic search over the Care Companion FAQ (embeddings, stored in MongoDB). The assistant calls
this internally on every turn; the endpoint is exposed mainly for testing and
for any "browse the FAQ" UI.

```
POST /api/knowledge/search
```

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | The search text |
| `top_k` | integer | no | 1–20. Defaults to the server's `RAG_TOP_K` (4) |

```json
{ "query": "is there a copay?", "top_k": 3 }
```

**Response — 200**

```json
{
  "response_code": 200,
  "success": true,
  "status_code": 200,
  "message": "Search completed successfully.",
  "result": [
    {
      "id": "12",
      "category": "Financial Coverage",
      "question": "Will I have to pay anything for this program?",
      "answer": "Most plans cover it in full; a small copay may apply...",
      "score": 0.8123
    }
  ]
}
```

**Result fields**

| Field | Type | Notes |
|---|---|---|
| `id` | string | Chunk id |
| `category` | string | FAQ section it came from |
| `question` | string | |
| `answer` | string | May still contain placeholders such as `[Provider name]` — those are only filled in when the assistant uses the chunk, not here |
| `score` | number | Cosine similarity, rounded to 4dp. Higher is more relevant |

**Other responses**

| Code | When | `message` |
|---|---|---|
| `200` | Nothing matched | `"No matching FAQ entries found."` (`result: []`) |
| `400` | `query` missing, or `top_k` out of 1–20 | `"Validation failed."` |
| `502` | The embedding call failed, or the FAQ has not been ingested | `"Search is unavailable right now. Please try again."` |

---

## 8. Typical frontend flows

### A. Staff dashboard — start a chat

```
GET  /api/chat/patients      → pick a patient_id
POST /api/chat/start         → { patient_id }
                             → keep result.conv_id, render result.messages
                             → show result.chat_link, warn if !result.email_sent
```

### B. Patient chat page (opened from the emailed link)

The emailed link is `<subdomain>/chat/<conv_id>` — the conversation is in the
path, and the host is the tenant.

```js
const conv = location.pathname.split("/").pop();
const TENANT = location.origin;        // send this as X-Tenant

// 1. load history
const history = await call(`/chat/conversations/${conv}`);

// 2. each turn
const turn = await call("/chat/message", {
  method: "POST",
  body: { conv_id: conv, text: input.value },
});
// append turn.response as an assistant bubble; check turn.status
```

### C. Watching the outcome

```
GET /api/chat/conversations?patient_id={id}   → result[0].status
                                              → "enrolled" | "declined" | "callback"
                             → "optedout" | "active"
```

---

## 9. Integration notes / gotchas

1. **No auth, but `X-Tenant` is mandatory.** No tokens and no cookies, and
   CORS is wide open (`CORS_ALLOW_ALL_ORIGINS = True`), so browser calls work
   from any origin — but every `/api/chat/` call must carry `X-Tenant`, or it
   is refused with `400`. See section 2.
2. **Tenants are isolated.** A `conv_id` or `patient_id` belonging to one
   tenant is invisible under another — the same id sent with the wrong
   `X-Tenant` returns `404`, not somebody else's data.
3. **Always check `success`, not just the HTTP code.** Some "empty" cases come
   back as `200` with `success: true` and an empty `result`.
4. **`conv_id` is the chat key, `patient_id` is the person key.** Don't mix
   them — except in 6.5, which deliberately accepts either.
5. **`/chat/message` is slow.** It does an embedding call, a FAQ search and
   an OpenAI completion. Budget several seconds and show a typing indicator;
   disable the send button while a request is in flight.
6. **`email_sent: false` is not a failure.** The chat opened fine — the mail
   just didn't go, so it is still a `201`. The `message` changes to *"Chat
   started, but the link could not be emailed to the patient. Share the chat
   link with them instead."* and `email_error` says which: no address on
   file, or a malformed one. Show `chat_link` so staff can pass it on.
7. **Timestamps are ISO 8601 UTC.** Convert to local time in the UI.
8. **Unknown routes return JSON, not HTML** — `404` with
   `"That endpoint does not exist."`. A wrong method returns `405` in the same
   envelope.
9. **The assistant's reply is plain text**, possibly multi-line. Render newlines
   (`white-space: pre-wrap`), and escape it — do not inject it as HTML.
