
from getpass import getpass
from werkzeug.security import generate_password_hash
from database import get_connection

username = input("請輸入帳號：").strip()
password = getpass("請輸入密碼：")

if not username or not password:
    print("帳號和密碼不能空白")
else:
    password_hash = generate_password_hash(password)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
            """, (username, password_hash, "editor"))

    print("編輯者帳號建立成功！")
