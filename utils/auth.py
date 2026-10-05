import hashlib
import hmac
import secrets
from database.db import one, connection, audit

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000).hex()
    return f'pbkdf2_sha256$260000${salt}${digest}'

def verify_password(password, encoded):
    try:
        _, rounds, salt, expected = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError):
        return False

def login(username, password):
    user=one('SELECT * FROM users WHERE username=? AND active=1',(username.strip(),))
    if not user or not verify_password(password,user['password_hash']):
        return None
    user.pop('password_hash')
    user['auth_epoch']=one("SELECT value FROM settings WHERE key='auth_epoch'")['value']
    if user['role']=='teacher':
        teacher=one('SELECT id FROM teachers WHERE user_id=? AND active=1',(user['id'],))
        if not teacher:
            return None
        user['teacher_id']=teacher['id']
    with connection() as conn:
        audit(conn,user,'Login','Successful login')
    return user

def current_user(user_id):
    user=one('SELECT id,username,name,role,active FROM users WHERE id=? AND active=1',(user_id,))
    if user and user['role']=='teacher':
        teacher=one('SELECT id FROM teachers WHERE user_id=? AND active=1',(user_id,))
        if not teacher:
            return None
        user['teacher_id']=teacher['id']
    return user

def require_admin(user):
    if user['role']!='admin':
        raise PermissionError('This action is available only to administrators.')
