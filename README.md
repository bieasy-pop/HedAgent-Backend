# Academic Intervention — Backend API

FastAPI backend for the academic intervention mobile application.

## Stack
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL via SQLAlchemy + Alembic
- **Auth**: Firebase Authentication
- **AI**: OpenAI GPT-4o
- **Files**: Cloudinary
- **Push**: OneSignal
- **Hosting**: Render

---

## Local Setup

### 1. Clone and install
```bash
git clone <your-repo>
cd academic-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in all values in .env
```

For `FIREBASE_CREDENTIALS_JSON`, open your Firebase serviceAccountKey.json and
paste the entire JSON as a single-line string:
```
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

### 3. Run database migrations
```bash
alembic upgrade head
```

### 4. Start the server
```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## Generate a new migration
After changing any model:
```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

## Deploy to Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → New → Blueprint.
3. Connect your GitHub repo — Render reads `render.yaml` automatically.
4. In the Render dashboard, set all `sync: false` environment variables.
5. Deploy. Alembic runs automatically during the build step.

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register after Firebase sign-up |
| POST | /api/auth/login | Login + refresh device token |
| GET  | /api/auth/me | Get current user profile |
| GET  | /api/students/ | List all students (educator/admin) |
| GET  | /api/students/{id} | Get student profile |
| PATCH| /api/students/{id} | Update student data + regenerate AI insight |
| POST | /api/students/{id}/avatar | Upload avatar |
| GET  | /api/interventions/ | List interventions |
| POST | /api/interventions/ | Create intervention + AI plan + notify |
| PATCH| /api/interventions/{id} | Update status/assignee |
| POST | /api/interventions/{id}/attachment | Upload document |
| GET  | /api/ai/insight/{student_id} | Generate fresh AI insight |
| POST | /api/ai/chat | Multi-turn educator AI chat |
| POST | /api/notifications/send | Push to specific users |
| POST | /api/notifications/broadcast | Broadcast to segment (admin) |

