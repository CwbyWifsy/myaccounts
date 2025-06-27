import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type
import tempfile


def derive_key(password: str, salt: bytes) -> bytes:
    """
    使用 Argon2id 从主密码派生 32 字节对称密钥
    """
    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=2,
        memory_cost=2**16,
        parallelism=1,
        hash_len=32,
        type=Type.ID
    )


def encrypt_vault(password: str, data: dict) -> dict:
    """
    输入明文数据 dict，返回包含 salt/nonce/ciphertext 的加密 Vault JSON
    """
    salt = os.urandom(16)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode()
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "kdf": "argon2id",
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode()
    }


def decrypt_vault(password: str, vault_json: dict) -> dict:
    """
    从加密 Vault JSON 解密并返回明文数据 dict
    """
    salt = base64.b64decode(vault_json["salt"])
    nonce = base64.b64decode(vault_json["nonce"])
    ct = base64.b64decode(vault_json["ciphertext"])
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct, None)
    return json.loads(pt.decode())

def atomic_write(path: str, content: dict):
    """
    原子化写入 JSON 文件，避免写入中断导致损坏
    """
    dir_name = os.path.dirname(path) or '.'
    with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
        json.dump(content, tf)
        tf.flush()
        os.fsync(tf.fileno())
    os.replace(tf.name, path)

def load_vault_file(path: str) -> dict:
    """
    安全加载 Vault 文件，捕获文件读写和 JSON 错误
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        raise ValueError("无法读取 Vault 文件，可能传入了非 Vault 文件路径。")
    except json.JSONDecodeError:
        raise ValueError("Vault 文件不是有效的 JSON，请检查文件路径和内容。")
    except FileNotFoundError:
        raise ValueError(f"找不到 Vault 文件: {path}")