# 🍮 布丁投稿室 — FastAPI 投稿審查系統

## 專案介紹

本系統是一套使用 Python FastAPI 開發的網頁投稿審查平台，提供作者與編輯者不同的操作權限，完成從投稿、編輯、送審到審查結果管理的流程。

## 使用技術

- **後端：** Python、FastAPI、Uvicorn
- **前端：** HTML、CSS、JavaScript、Jinja2
- **資料庫：** PostgreSQL
- **資料庫連線：** psycopg
- **密碼驗證：** Werkzeug
- **版本控制：** Git、GitHub

## 專案結構

- `main.py`：FastAPI 主程式，負責路由、登入、註冊、角色權限與投稿審查邏輯。
- `database.py`：PostgreSQL 資料庫連線設定。
- `server_sessions.py`：登入狀態管理，透過 PostgreSQL 保存 Session 紀錄。
- `create_user.py`：透過 Python 建立使用者帳號的輔助程式。
- `templates/`：Jinja2 HTML 網頁模板。
- `static/css/style.css`：奶油布丁風格的 CSS。
- `static/js/main.js`：網頁互動與刪除確認功能。
- `requirements.txt`：Python 套件需求清單。

## 資料庫設計

系統使用 PostgreSQL，資料庫名稱為 `submission_system`。

主要包含三張資料表：

1. `users`：儲存使用者帳號、密碼雜湊值與身分角色。
2. `submissions`：儲存投稿文章、類別、內容、審查狀態及所屬使用者。
3. `web_sessions`：儲存使用者登入狀態及有效期限。

## 系統功能

### 作者

- 註冊及登入帳號
- 新增投稿
- 查看自己的投稿清單
- 編輯、刪除尚未送審的稿件
- 將稿件送出審查
- 查看稿件審查狀態

### 編輯者

- 登入編輯者管理頁面
- 查看待審稿件
- 閱讀稿件完整內容
- 通過或退回稿件

### 管理員

- 查看帳號清單
- 建立編輯者帳號

## 投稿審查流程

1. 作者建立文章，狀態為「編輯中」。
2. 作者送出審查，狀態改為「審查中」。
3. 編輯者閱讀文章並進行審查。
4. 通過後狀態變成「已通過」。
5. 退回後狀態恢復「編輯中」，作者可以重新修改。

## 安裝與啟動（Windows PowerShell）

第一次使用時，安裝所需套件：

```powershell
py -m pip install -r requirements.txt
```

確認 PostgreSQL 服務正常運作，並已設定 `database.py` 的資料庫連線資訊。

啟動 FastAPI：

```powershell
py -m uvicorn main:app --reload
```

開啟瀏覽器：

http://127.0.0.1:8000/login

註冊頁面：

http://127.0.0.1:8000/register

## 登入狀態管理

系統使用 `server_sessions.py` 管理伺服器端 Session。

登入成功後，系統產生隨機登入識別碼，並將對應的登入資訊儲存在 PostgreSQL 的 `web_sessions` 資料表中。

因此不需要額外設定 `SESSION_SECRET`。

## 開發環境

本系統目前主要用於本機開發與軟體工程課程展示，尚未完成正式公開部署所需的完整安全設定。
