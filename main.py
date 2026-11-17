import os
import re
import secrets
from psycopg.errors import UniqueViolation
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_connection

app = FastAPI(title="布丁投稿室")
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"], same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def require_role(request: Request, allowed_role: str):
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="請先登入")
    if request.session.get("role") != allowed_role:
        raise HTTPException(status_code=403, detail="你沒有執行此操作的權限")
    return user_id

# Existing editor1 account is the demo administrator by default.
# Set ADMIN_USERNAME to the username of a different existing editor if desired.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "editor1")

def is_admin(request: Request):
    return (request.session.get("role") == "editor"
            and request.session.get("username") == ADMIN_USERNAME)

def require_admin(request: Request):
    require_role(request, "editor")
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="只有管理員可以建立編輯者")

def csrf_token(request: Request):
    if "account_csrf" not in request.session:
        request.session["account_csrf"] = secrets.token_urlsafe(24)
    return request.session["account_csrf"]

def check_account_csrf(request: Request, token: str):
    expected = request.session.get("account_csrf")
    if not expected or not secrets.compare_digest(expected, token):
        raise HTTPException(status_code=403, detail="表單已失效，請重新開啟頁面")

def account_error(username: str, password: str, confirm_password: str):
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
        return "帳號限 3～32 字元，只能使用英文字母、數字與底線"
    if len(password) < 8 or len(password) > 128:
        return "密碼長度須介於 8～128 字元"
    if password != confirm_password:
        return "兩次輸入的密碼不一致"
    return None

def insert_account(username: str, password: str, role: str):
    # Parameterized SQL, and avoid overwriting existing accounts.
    # For full concurrency safety, users.username should have a UNIQUE constraint.
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO users (username, password_hash, role)
                    SELECT %s, %s, %s
                    WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = %s)""",
                    (username, generate_password_hash(password), role, username))
                return cur.rowcount == 1
    except UniqueViolation:
        return False

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    return render(request, "register.html", csrf=csrf_token(request))

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...),
             confirm_password: str = Form(...), csrf: str = Form(...),
             role: str = Form("author")):
    check_account_csrf(request, csrf)
    username = username.strip()
    error = account_error(username, password, confirm_password)

    # Only the two known roles are accepted. Do not trust client-side controls.
    if not error and role not in ("author", "editor"):
        error = "請選擇有效的註冊身分"
    # Reserve the demo administrator username: registration must never create an admin.
    if not error and username == ADMIN_USERNAME:
        error = "此帳號名稱保留給管理員，請使用其他名稱"

    if not error and not insert_account(username, password, role):
        error = "此帳號已有人使用，請換一個帳號"
    if error:
        return render(request, "register.html", csrf=csrf_token(request),
                      error=error, username=username, selected_role=role)
    return RedirectResponse(url="/login?registered=1", status_code=303)

@app.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request):
    require_admin(request)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users ORDER BY id DESC")
            users = cur.fetchall()
    return render(request, "admin_users.html", users=users, csrf=csrf_token(request))

@app.post("/admin/users", response_class=HTMLResponse)
def admin_create_editor(request: Request, username: str = Form(...),
                        password: str = Form(...), confirm_password: str = Form(...),
                        csrf: str = Form(...)):
    require_admin(request)
    check_account_csrf(request, csrf)
    username = username.strip()
    error = account_error(username, password, confirm_password)
    if not error and not insert_account(username, password, "editor"):
        error = "此帳號已有人使用，請換一個帳號"
    if error:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, role FROM users ORDER BY id DESC")
                users = cur.fetchall()
        return render(request, "admin_users.html", users=users,
                      csrf=csrf_token(request), error=error, username=username)
    return RedirectResponse(url="/admin/users?created=1", status_code=303)

def render(request, name, **kwargs):
    return templates.TemplateResponse(request=request, name=name, context={**kwargs, "is_admin": is_admin(request)})

@app.get("/")
def home():
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/test-db")
def test_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM submissions")
            count = cur.fetchone()[0]
    return {"message": "PostgreSQL 連線成功", "submission_count": count}

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    return render(request, "login.html", registered=request.query_params.get("registered") == "1")

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
    if user is None or not check_password_hash(user[2], password):
        return render(request, "login.html", error="帳號或密碼錯誤")
    request.session.clear()
    request.session.update({"user_id": user[0], "username": user[1], "role": user[3]})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if request.session.get("user_id") is None:
        return RedirectResponse(url="/login", status_code=303)
    role = request.session.get("role")
    if role == "author":
        return author_list(request)
    if role == "editor":
        return editor_list(request)
    raise HTTPException(status_code=403, detail="沒有使用權限")

@app.get("/author", response_class=HTMLResponse)
def author_list(request: Request):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, author, category, title, status FROM submissions WHERE user_id = %s ORDER BY id DESC", (user_id,))
            submissions = cur.fetchall()
    stats = {"all": len(submissions), "draft": sum(x[4] == "編輯中" for x in submissions), "review": sum(x[4] == "審查中" for x in submissions), "approved": sum(x[4] == "已通過" for x in submissions)}
    return render(request, "author.html", submissions=submissions, stats=stats)

@app.get("/submit", response_class=HTMLResponse)
def submit_form(request: Request):
    require_role(request, "author")
    return render(request, "submission_form.html", mode="create", submission=None)

@app.post("/submit")
def create_submission(request: Request, author: str = Form(...), category: str = Form(...), title: str = Form(...), content: str = Form(...)):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO submissions (author, category, title, content, user_id) VALUES (%s, %s, %s, %s, %s)", (author, category, title, content, user_id))
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/edit/{submission_id}", response_class=HTMLResponse)
def edit_form(request: Request, submission_id: int):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT author, category, title, content FROM submissions WHERE id = %s AND status = %s AND user_id = %s", (submission_id, "編輯中", user_id))
            submission = cur.fetchone()
    if submission is None:
        raise HTTPException(status_code=404, detail="找不到可編輯的稿件")
    return render(request, "submission_form.html", mode="edit", submission=submission, submission_id=submission_id)

@app.post("/edit/{submission_id}")
def update_submission(request: Request, submission_id: int, author: str = Form(...), category: str = Form(...), title: str = Form(...), content: str = Form(...)):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE submissions SET author = %s, category = %s, title = %s, content = %s WHERE id = %s AND status = %s AND user_id = %s", (author, category, title, content, submission_id, "編輯中", user_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="找不到可編輯的稿件")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/delete/{submission_id}")
def delete_submission(request: Request, submission_id: int):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM submissions WHERE id = %s AND status = %s AND user_id = %s", (submission_id, "編輯中", user_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="找不到可刪除的稿件")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/submit-review/{submission_id}")
def submit_review(request: Request, submission_id: int):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE submissions SET status = %s WHERE id = %s AND status = %s AND user_id = %s", ("審查中", submission_id, "編輯中", user_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="找不到可以送審的稿件")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/editor", response_class=HTMLResponse)
def editor_list(request: Request):
    require_role(request, "editor")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, author, category, title, status FROM submissions WHERE status = %s ORDER BY id DESC", ("審查中",))
            submissions = cur.fetchall()
    return render(request, "editor.html", submissions=submissions)

@app.get("/editor/submission/{submission_id}", response_class=HTMLResponse)
def editor_submission_detail(request: Request, submission_id: int):
    require_role(request, "editor")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT author, category, title, content, status FROM submissions WHERE id = %s AND status = %s", (submission_id, "審查中"))
            submission = cur.fetchone()
    if submission is None:
        raise HTTPException(status_code=404, detail="找不到待審查稿件")
    return render(request, "detail.html", submission=submission, submission_id=submission_id)

@app.post("/review/{submission_id}/{action}")
def review_submission(request: Request, submission_id: int, action: str):
    require_role(request, "editor")
    if action not in ("approve", "return"):
        raise HTTPException(status_code=400, detail="無效的審查操作")
    new_status = "已通過" if action == "approve" else "編輯中"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE submissions SET status = %s WHERE id = %s AND status = %s", (new_status, submission_id, "審查中"))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="找不到待審查稿件")
    return RedirectResponse(url="/dashboard", status_code=303)
