import argparse
from getpass import getpass
import sqlite3
import time
from pydantic import ValidationError
from .config import Settings
from .database import Database
from .schemas import CreateUser
from .security import hash_password


def main():
    parser = argparse.ArgumentParser(description="本草知问初始管理员配置")
    parser.add_argument("command", choices=["create-admin", "ensure-admin"])
    args = parser.parse_args()
    database = Database(Settings.from_env().database)
    database.initialize()
    with database.connect() as db:
        exists = db.execute("SELECT id FROM users WHERE role = 'admin' AND active = 1").fetchone()
    if exists:
        if args.command == "create-admin":
            parser.exit(1, "管理员已存在，请登录后台管理账号。\n")
        return
    print("首次启动：创建管理员账号（密码至少 10 位，输入时不显示）。")
    username = input("登录账号 [admin]: ").strip() or "admin"
    display_name = input("显示名称 [管理员]: ").strip() or "管理员"
    password = getpass("密码: ")
    if password != getpass("再次输入密码: "):
        parser.exit(1, "两次密码不一致。\n")
    try:
        user = CreateUser(username=username, display_name=display_name, password=password, role="admin")
    except ValidationError:
        parser.exit(1, "账号须为 3–32 位字母、数字或下划线；密码须为 10–128 位；名称须为 1–50 位。\n")
    encoded = hash_password(user.password)
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT id FROM users WHERE role = 'admin' AND active = 1").fetchone():
            parser.exit(1, "管理员已由其他进程创建。\n")
        try:
            db.execute("INSERT INTO users(username, display_name, password_hash, role, created_at) VALUES(?,?,?,?,?)",
                       (user.username, user.display_name, encoded, "admin", int(time.time())))
        except sqlite3.IntegrityError:
            parser.exit(1, "该账号已存在。\n")
    print("管理员已创建。请在登录页面使用刚设置的账号和密码。")


if __name__ == "__main__":
    main()
