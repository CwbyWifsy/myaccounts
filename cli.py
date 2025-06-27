## cli.py
import json
import typer
from typing import Optional
from vault import encrypt_vault, decrypt_vault, atomic_write, load_vault_file
from argon2.exceptions import VerifyMismatchError

app = typer.Typer(help="简单的加密 Vault 管理工具")

@app.command()
def init(file: str):
    """初始化 Vault 文件"""
    pw = typer.prompt("设置主密码", hide_input=True, confirmation_prompt=True)
    empty = {"entries": []}
    encrypted = encrypt_vault(pw, empty)
    atomic_write(file, encrypted)
    typer.secho(f"已初始化 Vault：{file}", fg="green")

@app.command()
def show(
    file: str
):
    """解密并显示 Vault 内容"""
    pw = typer.prompt("输入主密码", hide_input=True)
    try:
        vault = load_vault_file(file)
        data = decrypt_vault(pw, vault)
    except ValueError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))

@app.command()
def add(
    file: str,
    name: str = typer.Option(..., help="条目名称"),
    username: Optional[str] = typer.Option(None, help="用户名"),
    account: Optional[str] = typer.Option(None, help="账号"),
    password: Optional[str] = typer.Option(None, help="密码"),
    website: Optional[str] = typer.Option(None, help="网站 URL"),
    phone: Optional[str] = typer.Option(None, help="手机号"),
    email: Optional[str] = typer.Option(None, help="邮箱地址")
):
    """向 Vault 添加新条目，支持多种属性"""
    pw = typer.prompt("输入主密码", hide_input=True)
    try:
        vault = load_vault_file(file)
        data = decrypt_vault(pw, vault)
    except ValueError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(code=1)
    entry = {"name": name}
    for key, val in [("username", username), ("account", account), ("password", password), ("website", website), ("phone", phone), ("email", email)]:
        if val is not None:
            entry[key] = val
    data["entries"].append(entry)
    new_vault = encrypt_vault(pw, data)
    atomic_write(file, new_vault)
    typer.secho(f"已添加条目：{name}", fg="green")

@app.command()
def delete(file: str, name: str):
    """删除 Vault 中指定名称的条目"""
    pw = typer.prompt("输入主密码", hide_input=True)
    try:
        vault = load_vault_file(file)
        from vault import decrypt_vault
        data = decrypt_vault(pw, vault)
    except ValueError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(code=1)
    entries = data.get("entries", [])
    filtered = [e for e in entries if e.get("name") != name]
    if len(filtered) == len(entries):
        typer.secho(f"未找到条目：{name}", fg="yellow")
        raise typer.Exit(code=1)
    data["entries"] = filtered
    new_vault = encrypt_vault(pw, data)
    atomic_write(file, new_vault)
    typer.secho(f"已删除条目：{name}", fg="green")

@app.command()
def update(
    file: str,
    name: str,
    username: Optional[str] = None,
    account: Optional[str] = None,
    password: Optional[str] = None,
    website: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None
):
    """更新 Vault 中指定名称条目的属性"""
    pw = typer.prompt("输入主密码", hide_input=True)
    try:
        vault = load_vault_file(file)
        from vault import decrypt_vault
        data = decrypt_vault(pw, vault)
    except ValueError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(code=1)
    for entry in data.get("entries", []):
        if entry.get("name") == name:
            for key, val in [("username", username), ("account", account), ("password", password), ("website", website), ("phone", phone), ("email", email)]:
                if val is not None:
                    entry[key] = val
            break
    else:
        typer.secho(f"未找到条目：{name}", fg="yellow")
        raise typer.Exit(code=1)
    new_vault = encrypt_vault(pw, data)
    atomic_write(file, new_vault)
    typer.secho(f"已更新条目：{name}", fg="green")

if __name__ == "__main__":
    app()
