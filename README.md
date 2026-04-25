# notes-app

A personal notes app with markdown support, tags, and auth. Built with FastAPI and SQLite.

## Stack
- Python 3.11+
- FastAPI — REST API + auth
- SQLAlchemy — ORM
- SQLite — local persistent storage
- JWT (python-jose) — authentication
- bcrypt — password hashing
- HTML/CSS/JS — frontend, no framework
- marked.js — markdown rendering (CDN)

## Project Structure
```
notes-app/
├── static/
│   └── index.html     # frontend
├── main.py            # API routes + auth
├── models.py          # User, Note, Tag models
├── database.py        # DB connection
└── requirements.txt
```

## API Routes
| Method | Route          | Description           |
|--------|----------------|-----------------------|
| POST   | /register      | Create account        |
| POST   | /login         | Get JWT token         |
| GET    | /me            | Current user info     |
| GET    | /notes         | Get notes (search/tag filter) |
| POST   | /notes         | Create note           |
| PATCH  | /notes/{id}    | Update note           |
| DELETE | /notes/{id}    | Delete note           |
| GET    | /tags          | Get all tags          |
| POST   | /tags          | Create tag            |
| DELETE | /tags/{id}     | Delete tag            |

## Run Locally
```bash
# Create and activate venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
uvicorn main:app --reload

# Visit
http://localhost:8000
```
