# 🍮 布丁投稿室 — FastAPI 投稿審查系統

## 專案結構
- `main.py`：FastAPI 路由、Session、角色驗證與投稿審查邏輯
- `database.py`：PostgreSQL 連線（沿用既有 `submission_system`）
- `templates/`：Jinja2 HTML 頁面
- `static/css/style.css`：奶油布丁風 CSS
- `static/js/main.js`：刪除確認視窗

## 安裝與啟動（Windows PowerShell）
請先備份舊版專案，並確認原本 PostgreSQL 資料庫仍可連線。

```powershell
py -m pip install -r requirements.txt
$env:DB_PASSWORD = "你的資料庫密碼"
$env:SESSION_SECRET = "請設定一組長且隨機的字串"
py -m uvicorn main:app --reload
```

瀏覽 `http://127.0.0.1:8000/login`。

### 保留功能
- 作者 / 編輯者登入與 Session 權限
- 作者投稿清單依 `user_id` 隔離
- 新增、編輯、刪除、送出審查
- 編輯者待審清單、查看完整稿件、通過、退回
- 原有 API 路徑與資料表欄位不變

### 注意
- 本版重構了畫面，未連線至你的本機 PostgreSQL 做端對端測試，請先用測試文章驗證。
- 本機 Demo 使用 `https_only=False`，正式部署 HTTPS 時應調整設定。
- 此版未新增 CSRF Token，**不適合直接公開部署**。
- 不要把資料庫密碼、Session Secret、`.env` 或真實使用者資料推送到 GitHub。
- `create_user.py` 沿用你原本的檔案，不包含在壓縮包內。

## 新增：網頁註冊及管理員建立編輯者
- `/register`：訪客自行註冊，**角色固定為 author**，不接受使用者指定角色。
- `/admin/users`：管理員建立 editor 帳號、查看帳號清單。
- `/login`：新增註冊入口。
- **預設管理員是既有 `editor1` 帳號**（需本來就具有 `editor` 角色），直接用它登入即可進入「帳號管理」。如帳號名稱不同，請在啟動前設定 `$env:ADMIN_USERNAME = "你的既有編輯者帳號"`。不會自動建立或升級任何帳號。
- 新帳號密碼採 Werkzeug `generate_password_hash`，不儲存明文；帳號不可重複。
- 建議 PostgreSQL 的 `users.username` 設有 UNIQUE 約束；如果尚未設定，確認沒有重複帳號後執行：`ALTER TABLE users ADD CONSTRAINT users_username_unique UNIQUE (username);`（若已有唯一約束則不需執行）。
- 新增的註冊與管理員表單有 CSRF token；**原本的投稿、審查、登入表單尚未全面加入 CSRF 保護**。本專案仍定位為本機課堂 Demo，不宜直接公開部署。
- 本版未連接你的本機 PostgreSQL 執行端對端測試，請依下方流程測試。

### 測試
1. 未登入開啟 `/register`，建立 `author3`，再登入並投稿。
2. 以 `editor1` 登入，左側點「帳號管理」，新增 `editor2`。
3. 登出並以 `editor2` 登入，確認能審查稿件，但無法進入 `/admin/users`（403）。
4. 再用作者測試編輯、刪除、送審，編輯者測試通過與退回。
