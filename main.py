from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
from jose import JWTError, jwt
import bcrypt
from database import Base, engine, get_db
from models import Note, Tag, User, note_tags

SECRET_KEY = "change-this-to-a-random-secret-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    exc = HTTPException(status_code=401, detail="Invalid credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise exc
    return user


# ── Auth routes ───────────────────────────────────────────────────────────────

class RegisterSchema(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=201)
def register(body: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}

@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username}


# ── Note helpers ──────────────────────────────────────────────────────────────

def note_to_dict(note: Note):
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "is_pinned": note.is_pinned,
        "tags": [{"id": t.id, "name": t.name} for t in note.tags],
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


# ── Note schemas ──────────────────────────────────────────────────────────────

class NoteCreateSchema(BaseModel):
    title: str = "Untitled"
    content: str = ""
    is_pinned: bool = False
    tag_ids: List[int] = []

class NoteUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    tag_ids: Optional[List[int]] = None


# ── Note routes ───────────────────────────────────────────────────────────────

@app.get("/notes")
def get_notes(
    search: Optional[str] = Query(None),
    tag_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Note).filter(Note.user_id == current_user.id)
    if search:
        like = f"%{search}%"
        q = q.filter(Note.title.ilike(like) | Note.content.ilike(like))
    if tag_id:
        q = q.filter(Note.tags.any(Tag.id == tag_id))
    notes = q.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()
    return [note_to_dict(n) for n in notes]

@app.post("/notes", status_code=201)
def create_note(
    body: NoteCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    note = Note(
        title=body.title,
        content=body.content,
        is_pinned=body.is_pinned,
        user_id=current_user.id
    )
    if body.tag_ids:
        tags = db.query(Tag).filter(
            Tag.id.in_(body.tag_ids),
            Tag.user_id == current_user.id
        ).all()
        note.tags = tags
    db.add(note)
    db.commit()
    db.refresh(note)
    return note_to_dict(note)

@app.patch("/notes/{note_id}")
def update_note(
    note_id: int,
    body: NoteUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if body.title is not None:
        note.title = body.title
    if body.content is not None:
        note.content = body.content
    if body.is_pinned is not None:
        note.is_pinned = body.is_pinned
    if body.tag_ids is not None:
        tags = db.query(Tag).filter(
            Tag.id.in_(body.tag_ids),
            Tag.user_id == current_user.id
        ).all()
        note.tags = tags
    note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return note_to_dict(note)

@app.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return None


# ── Tag schemas ───────────────────────────────────────────────────────────────

class TagCreateSchema(BaseModel):
    name: str


# ── Tag routes ────────────────────────────────────────────────────────────────

@app.get("/tags")
def get_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tags = db.query(Tag).filter(Tag.user_id == current_user.id).all()
    return [{"id": t.id, "name": t.name} for t in tags]

@app.post("/tags", status_code=201)
def create_tag(
    body: TagCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Tag).filter(
        Tag.name == body.name,
        Tag.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")
    tag = Tag(name=body.name, user_id=current_user.id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name}

@app.delete("/tags/{tag_id}", status_code=204)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == current_user.id
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return None
