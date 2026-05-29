# http://127.0.0.1:8000
# http://127.0.0.1:8000/docs

import time, uuid, json, datetime
from typing import Optional, List
from fastapi import FastAPI, Request, Response, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# db setup and db models
DATABASE_URL = "sqlite:///./requestbin.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    api_key = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Inbox(Base):
    __tablename__ = "inboxes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Entry(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False)
    method = Column(String, nullable=False)
    query_params = Column(String, nullable=False)
    headers = Column(String, nullable=False)
    body = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Mini RequestBin")

# middleware and exception
class APIException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code, "request_id": getattr(request.state, "id_request", None)}
    )

@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    request.state.id_request = req_id
    start_time = time.time()
    response: Response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-ID-Request"] = req_id
    response.headers["X-Time-Process"] = f"{process_time:.4f}s"
    print(f"[{req_id}] {request.method} {request.url.path} → {response.status_code} ({process_time:.4f}s)")
    return response

# schema
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(x_api_key: str = Header(..., alias="X-API-Key"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user: raise APIException(401, "Invalid API Key", "UNAUTHORIZED")
    return user

class UserRegister(BaseModel): username: str
class InboxCreate(BaseModel): name: str; slug: str
class InboxUpdate(BaseModel): name: Optional[str] = None; is_active: Optional[bool] = None

# UI
@app.get("/", response_class=HTMLResponse)
def index_ui():
    return """
    <html>
        <head>
            <title>Mini RequestBin UI</title>
            <style>
                body { font-family: sans-serif; margin: 30px; background: #f4f6f9; color: #333; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                input, button, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px; }
                button { background: #0070f3; color: white; border: none; cursor: pointer; font-weight: bold;}
                button:hover { background: #0051a8; }
                pre { background: #272822; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 13px; }
            </style>
        </head>
        <body>
            <h1> Mini RequestBin Dashboard</h1>
            <div class="grid">
                <div class="card">
                    <h3>Step 1: Account & Inboxes</h3>
                    <input id="reg_user" placeholder="Username (e.g. parmida)" value="parmida" />
                    <button onclick="registerUser()">Register User</button>
                    <hr>
                    <input id="api_key_input" placeholder="Paste your API Key here to manage inboxes" />
                    <input id="box_name" placeholder="Inbox Name (e.g. My Box)" />
                    <input id="box_slug" placeholder="Inbox Slug (e.g. parmida-box)" />
                    <button onclick="createInbox()">Create Inbox</button>
                    <button onclick="loadDashboard()" style="background:#22c55e;">Refresh Dashboard Stats & Inboxes</button>
                </div>
                
                <div class="card">
                    <h3>Step 2: Simulate Sending a Request (No API Key Required)</h3>
                    <input id="sim_slug" placeholder="Target Slug (e.g. parmida-box)" value="parmida-box" />
                    <select id="sim_method"><option>POST</option><option>GET</option><option>PUT</option><option>DELETE</option></select>
                    <input id="sim_query" placeholder="Query String (e.g. ?recipe=Pasta&status=cooking)" />
                    <input id="sim_body" placeholder="JSON Body string (e.g. {'chef': 'Parmida'})" value='{"chef": "Parmida"}' />
                    <button onclick="sendSimulatedRequest()" style="background:#eab308; color:black;">Fire HTTP Request to /collect/{slug}/</button>
                </div>
            </div>

            <div class="card" style="margin-top:20px;">
                <h3> Live Dashboard View & Output Logs</h3>
                <div id="stats_view" style="font-weight:bold; margin-bottom:10px; color:#555;"></div>
                <pre id="output">Click 'Register User' above or fill your key to begin tracking requests...</pre>
            </div>

            <script>
                async function registerUser() {
                    const res = await fetch('/auth/register/', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: document.getElementById('reg_user').value})
                    });
                    const data = await res.json();
                    document.getElementById('output').textContent = JSON.stringify(data, null, 2);
                    if(data.api_key) document.getElementById('api_key_input').value = data.api_key;
                }
                async function createInbox() {
                    const key = document.getElementById('api_key_input').value;
                    const res = await fetch('/inboxes/', {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'X-API-Key': key},
                        body: JSON.stringify({name: document.getElementById('box_name').value, slug: document.getElementById('box_slug').value})
                    });
                    document.getElementById('output').textContent = JSON.stringify(await res.json(), null, 2);
                }
                async function sendSimulatedRequest() {
                    const slug = document.getElementById('sim_slug').value;
                    const method = document.getElementById('sim_method').value;
                    const query = document.getElementById('sim_query').value;
                    const bodyVal = document.getElementById('sim_body').value;
                    
                    const options = { method: method, headers: {'Content-Type': 'application/json'} };
                    if (method !== 'GET' && bodyVal) options.body = bodyVal;

                    const res = await fetch(`/collect/${slug}/${query}`, options);
                    document.getElementById('output').textContent = `[Collector Response] Status: ${res.status}\\n` + JSON.stringify(await res.json(), null, 2);
                }
                async function loadDashboard() {
                    const key = document.getElementById('api_key_input').value;
                    if(!key) { alert("Please input your API Key first!"); return; }
                    
                    const statsRes = await fetch('/stats/overview/', { headers: {'X-API-Key': key} });
                    const stats = await statsRes.json();
                    document.getElementById('stats_view').textContent = `Total Inboxes: ${stats.total_inboxes} | Active: ${stats.active_inboxes} | Total Captured Requests: ${stats.total_requests}`;
                    
                    const boxRes = await fetch('/inboxes/', { headers: {'X-API-Key': key} });
                    const boxes = await boxRes.json();
                    
                    let logHTML = "=== YOUR INBOXES ===\\n" + JSON.stringify(boxes, null, 2) + "\\n\\n";
                    for(let b of boxes) {
                        const reqsRes = await fetch(`/inboxes/${b.id}/requests/`, { headers: {'X-API-Key': key} });
                        const reqs = await reqsRes.json();
                        logHTML += `\\n=== CAPTURED ENTRIES FOR INBOX: ${b.name} (id: ${b.id}) ===\\n` + JSON.stringify(reqs, null, 2) + "\\n";
                    }
                    document.getElementById('output').textContent = logHTML;
                }
            </script>
        </body>
    </html>
    """

# endpoints *******
@app.post("/auth/register/", status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise APIException(400, "Username already taken", "BAD_REQUEST")
    user = User(username=data.username)
    db.add(user)
    db.commit()
    return {"username": user.username, "api_key": user.api_key}

@app.post("/inboxes/", status_code=201)
def create_inbox(data: InboxCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.query(Inbox).filter(Inbox.slug == data.slug).first():
        raise APIException(400, "Slug already exists", "ALREADY_EXISTS")
    inbox = Inbox(user_id=user.id, name=data.name, slug=data.slug)
    db.add(inbox)
    db.commit()
    return {"id": inbox.id, "name": inbox.name, "slug": inbox.slug, "is_active": inbox.is_active, "requests_count": 0, "created_at": inbox.created_at}

@app.get("/inboxes/")
def list_inboxes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inboxes = db.query(Inbox).filter(Inbox.user_id == user.id).all()
    return [{"id": i.id, "name": i.name, "slug": i.slug, "is_active": i.is_active, "requests_count": db.query(Entry).filter(Entry.inbox_id == i.id).count(), "created_at": i.created_at} for i in inboxes]

def fetch_inbox(inbox_id: int, db: Session, user_id: int):
    inbox = db.query(Inbox).filter(Inbox.id == inbox_id, Inbox.user_id == user_id).first()
    if not inbox: raise APIException(404, "Inbox not found", "NOT_FOUND")
    return inbox

@app.get("/inboxes/{inbox_id}/")
def get_inbox(inbox_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    return {"id": inbox.id, "name": inbox.name, "slug": inbox.slug, "is_active": inbox.is_active, "requests_count": db.query(Entry).filter(Entry.inbox_id == inbox.id).count(), "created_at": inbox.created_at}

@app.patch("/inboxes/{inbox_id}/")
def update_inbox(inbox_id: int, data: InboxUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    if data.name is not None: inbox.name = data.name
    if data.is_active is not None: inbox.is_active = data.is_active
    db.commit()
    return inbox

@app.delete("/inboxes/{inbox_id}/")
def delete_inbox(inbox_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    deleted_entries = db.query(Entry).filter(Entry.inbox_id == inbox.id).delete()
    db.delete(inbox)
    db.commit()
    return {"message": "Deleted", "requests_deleted": deleted_entries}

@app.api_route("/collect/{slug}/", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def collect_request(slug: str, request: Request, db: Session = Depends(get_db)):
    inbox = db.query(Inbox).filter(Inbox.slug == slug).first()
    if not inbox: raise APIException(404, "Inbox not found", "NOT_FOUND")
    if not inbox.is_active: raise APIException(400, "Inbox is inactive", "INACTIVE_INBOX")
    
    body_bytes = await request.body()
    entry = Entry(
        inbox_id=inbox.id,
        method=request.method,
        query_params=json.dumps(dict(request.query_params)),
        headers=json.dumps({k: v for k, v in request.headers.items()}),
        body=body_bytes.decode("utf-8") if body_bytes else None,
        content_type=request.headers.get("content-type"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(entry)
    db.commit()
    return {"message": "Stored", "slug": slug}

@app.get("/inboxes/{inbox_id}/requests/")
def list_requests(inbox_id: int, page: int = 1, size: int = 20, method: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    query = db.query(Entry).filter(Entry.inbox_id == inbox.id)
    if method: query = query.filter(Entry.method == method.upper())
    total = query.count()
    entries = query.order_by(Entry.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "items": [{"id": e.id, "method": e.method, "content_type": e.content_type, "ip_address": e.ip_address, "created_at": e.created_at} for e in entries],
        "total": total, "page": page, "size": size
    }

@app.get("/inboxes/{inbox_id}/requests/{entry_id}/")
def get_request_detail(inbox_id: int, entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    entry = db.query(Entry).filter(Entry.id == entry_id, Entry.inbox_id == inbox.id).first()
    if not entry: raise APIException(404, "Entry not found", "NOT_FOUND")
    return {
        "id": entry.id, "method": entry.method, "query_params": json.loads(entry.query_params),
        "headers": json.loads(entry.headers), "body": entry.body, "content_type": entry.content_type,
        "ip_address": entry.ip_address, "user_agent": entry.user_agent, "created_at": entry.created_at
    }

@app.delete("/inboxes/{inbox_id}/requests/")
def clear_requests(inbox_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox = fetch_inbox(inbox_id, db, user.id)
    deleted = db.query(Entry).filter(Entry.inbox_id == inbox.id).delete()
    db.commit()
    return {"deleted": deleted}

@app.get("/stats/overview/")
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inbox_ids = [i.id for i in db.query(Inbox.id).filter(Inbox.user_id == user.id).all()]
    total_inboxes = len(inbox_ids)
    active_inboxes = db.query(Inbox).filter(Inbox.user_id == user.id, Inbox.is_active == True).count()
    total_requests = db.query(Entry).filter(Entry.inbox_id.in_(inbox_ids)).count() if inbox_ids else 0
    day_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    last_24h = db.query(Entry).filter(Entry.inbox_id.in_(inbox_ids), Entry.created_at >= day_ago).count() if inbox_ids else 0
    return {"total_inboxes": total_inboxes, "active_inboxes": active_inboxes, "total_requests": total_requests, "last_24h_requests": last_24h}
