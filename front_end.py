import gradio as gr
import uuid
import requests
import os

BASE_URL = "http://localhost:8000"

# 登录（调用后端 /token）
def login(username, password):
    try:
        resp = requests.post(
            f"{BASE_URL}/token",
            data={"username": username, "password": password}
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data["access_token"]
            user_id = data["user_id"]
            return gr.update(visible=False), f"✅ 登录成功 | 用户ID：{user_id}", token, user_id
        else:
            gr.Warning("账号或密码错误")
            return gr.update(visible=True), "登录失败", "", ""
    except:
        gr.Error("无法连接后端，请启动 api.py")
        return gr.update(visible=True), "连接失败", "", ""

# 新建对话
def new_session(all_sessions, cur_session, token, user_id):
    new_id = str(uuid.uuid4())[:6]
    all_sessions[new_id] = []
    return all_sessions, new_id, gr.Radio(choices=list(all_sessions.keys()), value=new_id), []

# 切换历史会话
def switch_session(session_id, all_sessions):
    return all_sessions.get(session_id, [])

# 发送消息（调用后端 /chat）
def send_message(data, cur_session, all_sessions, token, user_id):
    if not token:
        gr.Warning("请先登录！")
        return {}, all_sessions.get(cur_session, []), all_sessions

    text = data.get("text", "")
    files = data.get("files", [])

    if not text and not files:
        return {}, all_sessions.get(cur_session, []), all_sessions

    use_user_rag = False

    # 处理文件上传
    if files:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            # 构建 multipart/form-data 文件列表
            upload_files = [("files", (os.path.basename(f), open(f, "rb"))) for f in files]
            resp = requests.post(f"{BASE_URL}/upload", files=upload_files, headers=headers)
            
            # 关闭文件句柄
            for _, file_tuple in upload_files:
                file_tuple[1].close()
                
            if resp.status_code == 200:
                use_user_rag = True  # 标记后续对话针对用户文件
                gr.Info("文件上传并解析成功！")
            else:
                gr.Warning("文件上传失败，将使用内置知识库回答")
        except Exception as e:
            gr.Warning(f"文件上传异常: {str(e)}")

    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "question": text,
            "thread_id": cur_session,
            "use_user_rag": use_user_rag  # 告诉后端是否使用用户文件RAG
        }
        resp = requests.post(f"{BASE_URL}/chat", json=payload, headers=headers)
        if resp.status_code == 200:
            answer = resp.json()["answer"]
        else:
            answer = f"请求失败: {resp.json().get('detail', '未知错误')}"
    except Exception as e:
        answer = f"后端接口调用失败: {str(e)}"

    all_sessions[cur_session].append((text, answer))
    return {}, all_sessions[cur_session], all_sessions

# Gradio 界面
with gr.Blocks(title="高校课程智能问答系统") as demo:
    # 全局状态
    all_sessions = gr.State({})
    cur_session = gr.State(None)
    token_state = gr.State("")
    user_id_state = gr.State("")

    # 顶部栏
    with gr.Row():
        info_text = gr.Textbox(value="未登录", scale=8, interactive=False)
        login_btn = gr.Button("登录", scale=1)

    # 登录面板
    with gr.Column(visible=False) as login_panel:
        username = gr.Textbox(label="账号")
        password = gr.Textbox(label="密码", type="password")
        submit_login = gr.Button("确认登录")

    # 主布局
    with gr.Row():
        with gr.Column(scale=1):
            new_chat_btn = gr.Button("➕ 新建对话")
            session_list = gr.Radio(label="历史对话", choices=[])
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=500)
            msg_input = gr.MultimodalTextbox(file_types=[".txt", ".pdf", ".docx"], placeholder="输入消息或上传文件")

    # 事件绑定
    login_btn.click(lambda: gr.update(visible=True), None, login_panel)
    submit_login.click(
        login,
        inputs=[username, password],
        outputs=[login_panel, info_text, token_state, user_id_state]
    )

    new_chat_btn.click(
        new_session, 
        inputs=[all_sessions, cur_session, token_state, user_id_state], 
        outputs=[all_sessions, cur_session, session_list, chatbot]
    )

    session_list.change(
        switch_session, 
        inputs=[session_list, all_sessions], 
        outputs=[chatbot]
    )

    msg_input.submit(
        send_message, 
        inputs=[msg_input, cur_session, all_sessions, token_state, user_id_state], 
        outputs=[msg_input, chatbot, all_sessions]
    )

if __name__ == "__main__":
    demo.launch()