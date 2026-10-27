# SecureVision AI — Security & Penetration Testing Report

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Auditor:** Senior Cybersecurity & Application Security Reviewer  
**Target:** SecureVision AI Application (`backend/`, `models/`, `frontend/`)

---

## 1. Executive Summary

A comprehensive application security and defensive boundary audit of **SecureVision AI** was conducted across static code analysis, dynamic API testing, input sanitization boundaries, and dependency inspection. 

**Key Findings:**
1. **Remediated Vulnerability (Moderate):** Discovered an unhandled dynamic attribute lookup vulnerability in `GET /api/v1/alerts` where non-column query parameters (e.g. `?sort_by=__table__`) caused unhandled Python attribute resolution leading to HTTP 500 crashes. **Fixed** by implementing a strict whitelist dictionary (`ALLOWED_SORT_COLUMNS`) that safely defaults to `Alert.anomaly_score`.
2. **SQL Injection Resistance (Verified Pass):** All database operations across scans, alerts, and model metadata utilize SQLAlchemy parameterized queries. Fuzzing with SQL injection payloads (`' OR '1'='1`, `1; DROP TABLE scans; --`) confirmed zero database compromise or query syntax errors.
3. **CSV Formula Injection / DDE Defense (Verified Pass):** The CSV export endpoint (`GET /api/v1/alerts/export`) implements proactive cell sanitization, neutralizing cells starting with `=`, `+`, `-`, or `@` by prepending `'`.
4. **Path Traversal & File System Isolation (Verified Pass):** Static file serving is restricted to `frontend/`, and documentation download is strictly bound to `BASE_DIR / "PROJECT_REPORT.md"`. Traversal attacks (`../../etc/passwd`, `..\..\windows\win.ini`) are rejected.
5. **Denial of Service & File Boundaries (Verified Pass):** 50 MB file size limit and 500,000 row cap are strictly enforced in `validate_file_size()`. Empty payloads and malformed non-CSV files return clean HTTP 400/422 responses without leaking internal stack traces.

---

## 2. Security Test Matrix & Detailed Findings

| Test ID | Vulnerability / Threat Class | Target Endpoint / Component | Test Vector / Payload | Expected Behavior | Actual Behavior | Severity | Status |
|---|---|---|---|---|---|:---:|:---:|
| `SEC-01` | **Arbitrary Attribute Lookup / 500 Crash** | `GET /api/v1/alerts?sort_by=...` | `?sort_by=__table__` | Safe fallback or clean 400 | Previously raised HTTP 500. Remediated with whitelist dictionary. | Medium | **Fixed & Verified** |
| `SEC-02` | **SQL Injection (SQLi)** | `GET /api/v1/alerts?search=...` | `' OR '1'='1`, `1; DROP TABLE scans; --` | Parameterized escaping, no syntax errors | Returned HTTP 200 with 0 matches or literal match; SQLite schema intact. | High | **Passed** |
| `SEC-03` | **CSV Formula Injection (DDE)** | `GET /api/v1/alerts/export` | Cells with `=cmd\|' /C calc'!A0`, `@SUM(...)` | Formulas neutralized with prepended quote `'` | Formulas neutralized; safe for Microsoft Excel / LibreOffice opening. | Medium | **Passed** |
| `SEC-04` | **Path Traversal / Local File Inclusion** | `GET /api/v1/report/download` | `?path=../../etc/passwd`, `..\..\win.ini` | Fixed file path, reject parameter traversal | Hardcoded file reference to `PROJECT_REPORT.md`; no user parameter accepted. | High | **Passed** |
| `SEC-05` | **Unrestricted File Upload** | `POST /api/v1/scans` | Files with `.exe`, `.sh`, `.bin`, empty bytes | Reject non-CSV formats with HTTP 400/422 | Non-CSV rejected (HTTP 400); empty file rejected (HTTP 422). | High | **Passed** |
| `SEC-06` | **Denial of Service (Oversized Upload)** | `POST /api/v1/scans` | Payloads $> 50$ MB | Enforce memory threshold and reject upload | `validate_file_size` aborts processing before memory exhaustion. | Medium | **Passed** |
| `SEC-07` | **Information Disclosure (Stack Traces)** | All Endpoints | Malformed binary headers, unexpected query values | Generic error messages; no stack traces | Structured JSON `{detail: "..."}` returned; no Python tracebacks exposed. | Low | **Passed** |
| `SEC-08` | **CORS Configuration** | FastAPI CORS Middleware | Cross-origin requests from arbitrary domains | Whitelist restricted to local origins | `CORS_ORIGINS` defaults to `http://localhost:8000,http://127.0.0.1:8000`. | Low | **Passed** |

---

## 3. Remediation Details: Dynamic Sort Attribute Vulnerability (`SEC-01`)

### Vulnerability Mechanics
In `backend/routes/api.py`, the `list_alerts` endpoint dynamically resolved the sort column using:
```python
# VULNERABLE CODE:
sort_column = getattr(Alert, sort_by, Alert.anomaly_score)
```
When an attacker supplied `?sort_by=__table__`, Python resolved `Alert.__table__` (a `Table` object, not an `InstrumentedAttribute`). When SQLAlchemy attempted `.order_by(sort_column)`, it raised `CompileError / ArgumentError`, returning an internal HTTP 500 error and exposing unhandled execution states.

### Remediation Applied
Replaced unchecked `getattr()` with an explicit whitelist dictionary mapping:
```python
# REMEDIATED CODE:
ALLOWED_SORT_COLUMNS = {
    "id": Alert.id,
    "event_index": Alert.event_index,
    "timestamp": Alert.timestamp,
    "prediction": Alert.prediction,
    "anomaly_score": Alert.anomaly_score,
    "severity": Alert.severity,
    "source_ip": Alert.source_ip,
    "dest_ip": Alert.dest_ip,
    "protocol": Alert.protocol,
}
sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, Alert.anomaly_score)
```
Any unsupported or malicious input now safely and deterministically defaults to `Alert.anomaly_score`, maintaining full API stability. Automated regression test [test_invalid_sort_by_defaults_safely](file:///n:/rohit%20project/log%20analyzer/backend/tests/test_api.py#L583-L596) enforces this guarantee.

---

## 4. Hardening Recommendations for Production Deployment

1. **Authentication & Role-Based Access Control (RBAC):** The current API operates in an academic/local context without authentication. For multi-tenant production use, integrate JWT bearer tokens (e.g. OAuth2 with Password Flow).
2. **Rate Limiting:** Implement token-bucket rate limiting (e.g., via `slowapi` or Redis) on `POST /api/v1/scans` to prevent brute-force upload exhaustion.
3. **Debug Flag Enforcement:** Ensure `DEBUG=false` in production environment variables (`backend/config.py`).
