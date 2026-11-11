import os
import jwt #JWT 令牌生成、解码、校验
from datetime import datetime,timedelta
from passlib.context import CryptContext #密码加密
from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
# 初始化密码加密
pwd_context = CryptContext(schemes=["pbkdf2_sha256"],deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY","9527")
ALGORITHM = "HS256" #加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = 30
fake_users_db = {
    "123": {
        "user_id": "1",
        "phone": "123",
        "hashed_password": pwd_context.hash("123456"),
        "nickname": "默认用户"
    }
}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") #初始化令牌认证器
#密码校验
def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)
#获取密码哈希
def get_password_hash(password):
    return pwd_context.hash(password)
#获取用户
def get_user(db,phone:str):
    if phone in db:
        return db[phone]
    return None
#认证用户
def authenticate_user(fake_db,phone:str,password:str):
    user = get_user(fake_db,phone)
    if not user:
        return False
    if not verify_password(password,user["hashed_password"]):
        return False
    return user
#创建访问令牌
def create_access_token(data:dict,expires_delta:timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt
#获取当前用户
async def get_current_user(token:str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "无法验证凭据",
        headers = {"www-Authenticate":"Bearer"},
    ) #凭证异常
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        phone:str = payload.get("sub")
        if phone is None:
            raise credentials_exception
        user_id:str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = {"phone":phone,"user_id":user_id}
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(fake_users_db,phone=token_data["phone"])
    if user is None:
        raise credentials_exception
    return user