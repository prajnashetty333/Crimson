# OvaCare — Smart Menstrual Wellness & Prediction System

OvaCare is a smart menstrual wellness tracking and prediction application featuring cycle forecasting, daily symptom and mood logging, wellness analytics, and secure patient authentication.

---

## 🔒 Security & Deployment Configuration

### How environment mode works

Authentication secrets are enforced based on a **single, explicit variable**:

| `APP_ENV` value | Behaviour |
|---|---|
| `development` | Dev fallback secret permitted locally; no `SECRET_KEY` required |
| `production` | Strong `SECRET_KEY` **required**; startup aborts if missing or weak |
| *(unset / anything else)* | Same enforcement as `production` — fail-safe default |

The development fallback is **never silently applied** in an unspecified environment.

### 1. Local development setup

Copy the example file and set `APP_ENV=development`:

```bash
cp backend/.env.example backend/.env
# The file already contains APP_ENV=development
# SECRET_KEY can be left empty — a local dev fallback is applied automatically
```

### 2. Generating a production `SECRET_KEY`

Run once, then set the output as an environment variable in your hosting provider:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The value must be **≥ 32 characters** and must not match any placeholder.

### 3. Production environment variables

Set these in your hosting provider's dashboard (Render, Railway, Heroku, etc.).  
**Do NOT put real secrets in `.env.example` or `README.md`.**

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Strong random secret (≥ 32 chars) |
| `CORS_ORIGINS` | Yes | Your frontend URL(s), comma-separated |
| `AUTH_TOKEN_MAX_AGE` | No | Token TTL in seconds (default: 604800) |

#### Example: Docker

```bash
docker run -d \
  -e APP_ENV=production \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e CORS_ORIGINS="https://ovacare.app" \
  -p 5000:5000 \
  ovacare-backend
```

### 4. Protecting Secrets & Environment Files
- Real `.env` files contain sensitive credentials and **must never be committed to source control**.
- The project's `.gitignore` explicitly excludes all `.env` files:
  ```gitignore
  # Environments
  .env
  .env.*
  !.env.example
  ```
- Use `backend/.env.example` as a template for local development.

---

## 🧪 Testing & Verification

### Running Backend Security Tests
```bash
cd backend
venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

### Running Frontend Production Build
```bash
cd frontend
npm run build
```
