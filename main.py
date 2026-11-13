
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="投稿審查系統")

from starlette.middleware.sessions import SessionMiddleware
import os

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET"],
    same_site="lax",
    https_only=False
)





@app.get("/")
def home():
    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )




from database import get_connection


@app.get("/test-db")
def test_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM submissions")
            count = cur.fetchone()[0]

    return {
        "message": "PostgreSQL 連線成功",
        "submission_count": count
    }


from fastapi.responses import HTMLResponse
from html import escape


@app.get("/author", response_class=HTMLResponse)
def author_list(request: Request):
    user_id = require_role(request, "author")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, status
                FROM submissions
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))
            submissions = cur.fetchall()


    rows = ""

    for submission in submissions:
        submission_id, author, category, title, status = submission


        edit_link = (
            f'<a href="/edit/{submission_id}">編輯</a>'
            if status == "編輯中"
            else "不可編輯"
        )


        delete_button = (
            f"""
            <form action="/delete/{submission_id}" method="post"
                  style="display:inline;"
                  onsubmit="return confirm('確定要刪除這篇投稿嗎？');">
                <button type="submit">刪除</button>
            </form>
            """
            if status == "編輯中"
            else ""
        )

        review_button = (
            f"""
            <form action="/submit-review/{submission_id}" method="post"
                  style="display:inline;">
                <button type="submit">送出審查</button>
            </form>
            """
            if status == "編輯中"
            else ""
        )



        rows += f"""
        <tr>
            <td>{submission_id}</td>
            <td>{escape(author)}</td>
            <td>{escape(category)}</td>
            <td>{escape(title)}</td>
            <td>{escape(status)}</td>
            <td>{edit_link} {delete_button} {review_button}</td>
        </tr>
        """


    return f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>作者投稿管理</title>
    </head>
    <body>
        <h1>作者投稿管理</h1>

        <table border="1" cellpadding="10">
            <tr>
                <th>編號</th>
                <th>作者</th>
                <th>類別</th>
                <th>標題</th>
                <th>審查狀態</th>
                <th>操作</th>
            </tr>
            {rows}
        </table>

        <p><a href="/">返回首頁</a></p>
    </body>
    </html>
    """


from fastapi import Form
from fastapi.responses import RedirectResponse


@app.get("/submit", response_class=HTMLResponse)
def submit_form(request: Request):
    require_role(request, "author")
    return """
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>新增投稿</title>
    </head>
    <body>
        <h1>新增投稿</h1>

        <form action="/submit" method="post">
            <p>作者：<input name="author" required></p>
            <p>類別：<input name="category" required></p>
            <p>標題：<input name="title" required></p>
            <p>文章內容：</p>
            <textarea name="content" rows="8" cols="50" required></textarea>
            <p><button type="submit">儲存投稿</button></p>
        </form>

        <a href="/author">返回作者投稿清單</a>
    </body>
    </html>
    """



@app.post("/submit")
def create_submission(
    request: Request,
    author: str = Form(...),
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...)
):
    user_id = require_role(request, "author")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO submissions
                (author, category, title, content, user_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (author, category, title, content, user_id))

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )



from fastapi import HTTPException


@app.get("/edit/{submission_id}", response_class=HTMLResponse)
def edit_form(request: Request, submission_id: int):
    user_id = require_role(request, "author")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT author, category, title, content
                FROM submissions
                WHERE id = %s AND status = %s AND user_id = %s
            """, (submission_id, "編輯中", user_id))
            submission = cur.fetchone()

    if submission is None:
        raise HTTPException(
            status_code=404,
            detail="找不到可編輯的稿件"
        )

    author, category, title, content = submission

    return f"""
    <html lang="zh-Hant">
    <head><meta charset="UTF-8"></head>
    <body>
        <h1>編輯投稿</h1>

        <form action="/edit/{submission_id}" method="post">
            <p>作者：
                <input name="author" value="{escape(author, quote=True)}" required>
            </p>
            <p>類別：
                <input name="category" value="{escape(category, quote=True)}" required>
            </p>
            <p>標題：
                <input name="title" value="{escape(title, quote=True)}" required>
            </p>
            <p>文章內容：</p>
            <textarea name="content" rows="8" cols="50" required>{escape(content)}</textarea>

            <p><button type="submit">儲存修改</button></p>
        </form>

        <a href="/author">返回作者投稿清單</a>
    </body>
    </html>
    """




@app.post("/edit/{submission_id}")
def update_submission(
    request: Request,
    submission_id: int,
    author: str = Form(...),
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...)
):
    user_id = require_role(request, "author")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET author = %s,
                    category = %s,
                    title = %s,
                    content = %s
                WHERE id = %s
                  AND status = %s
                  AND user_id = %s
            """, (
                author, category, title, content,
                submission_id, "編輯中", user_id
            ))

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="找不到可編輯的稿件"
                )

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )





@app.post("/delete/{submission_id}")
def delete_submission(
    request: Request,
    submission_id: int
):
    user_id = require_role(request, "author")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM submissions
                WHERE id = %s
                  AND status = %s
                  AND user_id = %s
            """, (submission_id, "編輯中", user_id))

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="找不到可刪除的稿件"
                )

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )




@app.post("/submit-review/{submission_id}")
def submit_review(
    request: Request,
    submission_id: int
):
    user_id = require_role(request, "author")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status = %s
                WHERE id = %s
                  AND status = %s
                  AND user_id = %s
            """, (
                "審查中",
                submission_id,
                "編輯中",
                user_id
            ))

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="找不到可以送審的稿件"
                )

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )




@app.get("/editor", response_class=HTMLResponse)
def editor_list(request: Request):
    require_role(request, "editor")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, status
                FROM submissions
                WHERE status = %s
                ORDER BY id DESC
            """, ("審查中",))
            submissions = cur.fetchall()

    rows = ""

    for submission in submissions:
        submission_id, author, category, title, status = submission


        review_buttons = f"""
        <form action="/review/{submission_id}/approve"
              method="post" style="display:inline;">
            <button type="submit">通過</button>
        </form>

        <form action="/review/{submission_id}/return"
              method="post" style="display:inline;">
            <button type="submit">退回</button>
        </form>
        """


        rows += f"""
        <tr>
            <td>{submission_id}</td>
            <td>{escape(author)}</td>
            <td>{escape(category)}</td>
            <td>{escape(title)}</td>
            <td>{escape(status)}</td>
            <td>{review_buttons}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>編輯審查管理</title>
    </head>
    <body>
        <h1>編輯審查管理</h1>
        <h2>待審查稿件</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>編號</th>
                <th>作者</th>
                <th>類別</th>
                <th>標題</th>
                <th>審查狀態</th>
                <th>操作</th>
            </tr>
            {rows}
        </table>

        <p><a href="/">返回首頁</a></p>
    </body>
    </html>
    """



@app.post("/review/{submission_id}/{action}")
def review_submission(
    request: Request,
    submission_id: int,
    action: str
):
    require_role(request, "editor")

    if action not in ("approve", "return"):
        raise HTTPException(
            status_code=400,
            detail="無效的審查操作"
        )

    new_status = "已通過" if action == "approve" else "編輯中"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status = %s
                WHERE id = %s AND status = %s
            """, (new_status, submission_id, "審查中"))

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="找不到待審查稿件"
                )

    return RedirectResponse(url="/dashboard", status_code=303)


from fastapi import Request
from werkzeug.security import check_password_hash


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>使用者登入</title>
    </head>
    <body>
        <h1>投稿審查系統</h1>
        <h2>使用者登入</h2>

        <form action="/login" method="post">
            <p>
                帳號：
                <input type="text" name="username" required>
            </p>
            <p>
                密碼：
                <input type="password" name="password" required>
            </p>
            <button type="submit">登入</button>
        </form>
    </body>
    </html>
    """


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, password_hash, role
                FROM users
                WHERE username = %s
            """, (username,))
            user = cur.fetchone()

    if user is None or not check_password_hash(user[2], password):
        return HTMLResponse(
            "<h2>帳號或密碼錯誤</h2>"
            '<a href="/login">重新登入</a>',
            status_code=401
        )

    request.session.clear()
    request.session["user_id"] = user[0]
    request.session["username"] = user[1]
    request.session["role"] = user[3]

    return RedirectResponse(url="/dashboard", status_code=303)



@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    username = request.session.get("username")
    role = request.session.get("role")

    if not username:
        return RedirectResponse(
            url="/login", status_code=303
        )

    if role == "author":
        role_name = "作者"
        management_page = author_list(request)
    elif role == "editor":
        role_name = "編輯者"
        management_page = editor_list(request)
    else:
        raise HTTPException(
            status_code=403,
            detail="沒有使用權限"
        )

    return f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>投稿審查系統</title>
    </head>
    <body>
        <h1>投稿審查系統</h1>

        <p>歡迎，{escape(username)}</p>
        <p>登入身分：{role_name}</p>

        <form action="/logout" method="post">
            <button type="submit">登出</button>
        </form>

        <hr>

        {management_page}

    </body>
    </html>
    """



@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)



def require_role(request: Request, allowed_role: str):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="請先登入"
        )

    if role != allowed_role:
        raise HTTPException(
            status_code=403,
            detail="你沒有執行此操作的權限"
        )

    return user_id