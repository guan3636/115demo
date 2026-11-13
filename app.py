
from flask import Flask, request, redirect, url_for
from database import get_connection
from html import escape

app = Flask(__name__)



@app.route("/")
def home():
    author_page = author()
    editor_page = editor()

    return f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <title>投稿審查系統</title>
    </head>
    <body>
        <h1>投稿審查系統</h1>
        <hr>

        <section>
            {author_page}
        </section>

        <hr>

        <section>
            {editor_page}
        </section>
    </body>
    </html>
    """




@app.route("/author")
def author():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, status
                FROM submissions
                ORDER BY id DESC
            """)
            submissions = cur.fetchall()

    html = """
    <h1>作者投稿管理</h1>
    <p><a href="/submit">新增投稿</a></p>

    <table border="1" cellpadding="10">
        <tr>
            <th>編號</th>
            <th>作者</th>
            <th>類別</th>
            <th>標題</th>
            <th>審查狀態</th>
            <th>操作</th>
        </tr>
    """

    for item in submissions:
        id, author, category, title, status = item

        html += f"""
        <tr>
            <td>{id}</td>
            <td>{escape(author)}</td>
            <td>{escape(category)}</td>
            <td><a href="/view/{id}">{escape(title)}</a></td>
            <td>{escape(status)}</td>
            
<td>
    {f'''
    <a href="/edit/{id}">編輯</a>

    <form action="/delete/{id}" method="POST"
          style="display:inline;"
          onsubmit="return confirm('確定要刪除這篇投稿嗎？');">
        <button type="submit">刪除</button>
    </form>

<form action="/send-review/{id}" method="POST"
      style="display:inline;"
      onsubmit="return confirm('確定要送出審查嗎？送出後將無法修改。');">
    <button type="submit">送出審查</button>
</form>

    ''' if status == '編輯中' else '不可編輯'}
</td>

        </tr>
        """

    html += """
    </table>
    
    """

    return html



@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        author = request.form["author"].strip()
        category = request.form["category"].strip()
        title = request.form["title"].strip()
        content = request.form["content"].strip()

        if not all([author, category, title, content]):
            return "所有欄位都必須填寫！", 400

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO submissions
                    (author, category, title, content, status)
                    VALUES (%s, %s, %s, %s, '編輯中')
                """, (author, category, title, content))

        return redirect(url_for("author"))

    return """
    <h1>新增投稿</h1>

    <form method="POST">
        <p>作者：<input name="author" required maxlength="100"></p>
        <p>類別：<input name="category" required maxlength="100"></p>
        <p>標題：<input name="title" required maxlength="200"></p>
        <p>文章內容：</p>
        <textarea name="content" rows="8" cols="50" required></textarea>
        <p><button type="submit">儲存投稿</button></p>
    </form>

    <a href="/author">返回作者介面</a>
    """



@app.route("/editor")
def editor():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, status
                FROM submissions
                WHERE status = '審查中'
                ORDER BY id DESC
            """)
            submissions = cur.fetchall()

    html = """
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
    """

    for item in submissions:
        id, author, category, title, status = item

        html += f"""
        <tr>
            <td>{id}</td>
            <td>{escape(author)}</td>
            <td>{escape(category)}</td>
            <td>
                <a href="/view/{id}">{escape(title)}</a>
            </td>
            <td>{escape(status)}</td>
            
<td>
    <form action="/approve/{id}" method="POST"
          onsubmit="return confirm('確定要通過這篇稿件嗎？');">
        <button type="submit">通過</button>
    </form>

<form action="/reject/{id}" method="POST"
      onsubmit="return confirm('確定要退回這篇稿件嗎？');">
    <button type="submit">退回</button>
</form>

</td>

        </tr>
        """

    html += """
    </table>
    
    """

    return html



@app.route("/edit/<int:submission_id>", methods=["GET", "POST"])
def edit_submission(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, content, status
                FROM submissions
                WHERE id = %s
            """, (submission_id,))
            item = cur.fetchone()

            if item is None:
                return "找不到這篇稿件", 404

            if item[5] != "編輯中":
                return "這篇稿件已送出，無法編輯", 403

            if request.method == "POST":
                category = request.form["category"].strip()
                title = request.form["title"].strip()
                content = request.form["content"].strip()

                if not all([category, title, content]):
                    return "所有欄位都必須填寫", 400

                cur.execute("""
                    UPDATE submissions
                    SET category = %s,
                        title = %s,
                        content = %s
                    WHERE id = %s AND status = '編輯中'
                """, (category, title, content, submission_id))

                return redirect(url_for("author"))

    _, author, category, title, content, status = item

    return f"""
    <h1>編輯投稿</h1>
    <p>作者：{escape(author)}</p>

    <form method="POST">
        <p>類別：
            <input name="category"
                   value="{escape(category, quote=True)}" required>
        </p>

        <p>標題：
            <input name="title"
                   value="{escape(title, quote=True)}" required>
        </p>

        <p>文章內容：</p>
        <textarea name="content" rows="8" cols="50"
                  required>{escape(content)}</textarea>

        <p><button type="submit">儲存修改</button></p>
    </form>

    <a href="/author">返回投稿清單</a>
    """


@app.route("/view/<int:submission_id>")
def view_submission(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, author, category, title, content, status
                FROM submissions
                WHERE id = %s
            """, (submission_id,))

            item = cur.fetchone()

    if item is None:
        return "找不到這篇稿件", 404

    id, author, category, title, content, status = item

    return f"""
    <h1>稿件詳細內容</h1>

    <p><strong>稿件編號：</strong>{id}</p>
    <p><strong>作者：</strong>{escape(author)}</p>
    <p><strong>投稿類別：</strong>{escape(category)}</p>
    <p><strong>文章標題：</strong>{escape(title)}</p>
    <p><strong>審查狀態：</strong>{escape(status)}</p>

    <hr>

    <h2>文章內容</h2>
    <div style="white-space: pre-wrap;">{escape(content)}</div>

    <hr>

    <p><a href="/author">返回作者投稿清單</a></p>
    """


@app.route("/delete/<int:submission_id>", methods=["POST"])
def delete_submission(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM submissions
                WHERE id = %s AND status = '編輯中'
                RETURNING id
            """, (submission_id,))

            deleted = cur.fetchone()

    if deleted is None:
        return "找不到稿件，或稿件已送出審查，無法刪除", 403

    return redirect(url_for("author"))


@app.route("/send-review/<int:submission_id>", methods=["POST"])
def send_review(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status = '審查中'
                WHERE id = %s AND status = '編輯中'
                RETURNING id
            """, (submission_id,))

            updated = cur.fetchone()

    if updated is None:
        return "找不到稿件，或稿件已經送出審查", 400

    return redirect(url_for("author"))


@app.route("/approve/<int:submission_id>", methods=["POST"])
def approve_submission(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status = '已通過'
                WHERE id = %s AND status = '審查中'
                RETURNING id
            """, (submission_id,))

            updated = cur.fetchone()

    if updated is None:
        return "找不到稿件，或稿件目前不在審查中", 400

    return redirect(url_for("editor"))


@app.route("/reject/<int:submission_id>", methods=["POST"])
def reject_submission(submission_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE submissions
                SET status = '編輯中'
                WHERE id = %s AND status = '審查中'
                RETURNING id
            """, (submission_id,))

            updated = cur.fetchone()

    if updated is None:
        return "找不到稿件，或稿件目前不在審查中", 400

    return redirect(url_for("editor"))


if __name__ == "__main__":
    app.run(debug=True)

