import os
import uuid
import sqlite3
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import timedelta

from auth import (
    authenticate_user, create_access_token, get_current_user,
    fake_users_db, ACCESS_TOKEN_EXPIRE_MINUTES, OAuth2PasswordRequestForm
)
from agent import run_conversation_api
from utils.config import Config
from utils.memory_sqlite import get_sqlite_saver
from utils.user_rag import add_user_documents

app = FastAPI(title = "高校课程智能问答API",version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

class Question(BaseModel):
    question:str
    thread_id:str = None
    user_id:str = None
    use_user_rag:bool = False

class QuestionResponse(BaseModel):
    answer:str
    thread_id:str
    user_id:str

@app.post("/token",summary="用户登录获取令牌")
async def login(form_data:OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code = 401,
            detail = "手机号或密码错误",
            headers = {"WWW-Authenticate":"Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {"sub":user["phone"],"user_id":user["user_id"]},
        expires_delta = access_token_expires
    )
    return {
        "access_token":access_token,
        "token_type":"bearer",
        "user_id":user["user_id"],
        "nickname":user["nickname"]
    }

@app.get("/sessions", summary="获取用户所有会话")
async def get_sessions(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    db_path = Config.MEMORY_DB_PATH

    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()

        # LangGraph 存储格式：thread_id 格式 = user_id___xxx
        cursor.execute('''
            SELECT DISTINCT thread_id, created_at
            FROM checkpoints
            WHERE thread_id LIKE ?
            ORDER BY created_at DESC
        ''', (f"{user_id}___%",))

        sessions = []
        for row in cursor.fetchall():
            full_thread_id = row[0]
            create_time = row[1]
            # 提取真正的会话ID
            real_thread_id = full_thread_id.split("___")[-1]
            sessions.append({
                "session_id": real_thread_id,
                "session_name": f"会话 {real_thread_id[-4:]}",
                "update_time": create_time
            })

        conn.close()
        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败：{str(e)}")


# ------------------------------
# 3. 获取指定会话的历史消息（从LangGraph内存取）
# ------------------------------
@app.get("/history/{thread_id}", summary="获取指定会话历史")
async def get_history(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    langgraph_thread_id = f"{user_id}___{thread_id}"

    try:
        saver = get_sqlite_saver()
        checkpoint = saver.get(
            {"configurable": {"thread_id": langgraph_thread_id}}
        ) # 获取指定会话的历史消息，内部自动反序列化成Python字典
        history = []
        if checkpoint and "channel_values" in checkpoint:
            messages = checkpoint["channel_values"].get("messages", [])
            for msg in messages:
                role = msg["role"]
                content = msg["content"]

                if role == "user":
                    history.append({"question": content, "answer": None, "time": ""})
                elif role == "assistant":
                    history.append({"question": None, "answer": content, "time": ""})

        return {"history": history}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败：{str(e)}")
    
@app.post("/upload", summary="上传课程文件并解析入库")
async def upload_files(
    files: list[UploadFile] = File(...), 
    current_user: dict = Depends(get_current_user)
):
    saved_paths = []
    try:
        for file in files:
            # 构造保存路径：data/user_uploads/用户ID_文件名
            user_id = current_user["user_id"]
            save_path = os.path.join(Config.USER_UPLOAD_DIR, f"{user_id}_{file.filename}")
            
            # 写入文件
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_paths.append(save_path)
        
        # 调用 RAG 模块解析并注入用户专属向量库
        add_user_documents(saved_paths)
        
        return {"status": "success", "message": f"成功上传并解析 {len(files)} 个文件"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传处理失败: {str(e)}")

@app.post("/chat", response_model=QuestionResponse, summary="智能问答接口")
async def chat(req: Question, current_user: dict = Depends(get_current_user)):
    thread_id = req.thread_id or str(uuid.uuid4())
    user_id = current_user["user_id"]
    try:
        answer = run_conversation_api(
            question=req.question,
            thread_id=thread_id,
            user_id=user_id,
            use_user_rag=req.use_user_rag  # 传递标识给 Agent
        )
        return {"answer": answer, "thread_id": thread_id, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务异常:{str(e)}")
