import streamlit as st
from processor import ContentProcessor
import base64

st.set_page_config(page_title="數產署議題摘錄器 v2", layout="wide")

# 初始化後端
proc = ContentProcessor()

# --- UI: 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 服務商設定")
    provider_type = st.radio("模型類型", ["多模態 (可看圖)", "純文字 (省額度)"])
    api_key = st.text_input("API Key", type="password")
    model = st.selectbox("模型選擇", [
        "google/gemini-2.5-pro-preview",
        "google/gemini-2.0-flash-001",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-3-5-haiku",
        "anthropic/claude-3-5-sonnet",
        "deepseek/deepseek-chat",
        "deepseek/deepseek-r1",
    ])
    st.divider()
    user_direction = st.text_area("🎯 強制注意/回應方向", placeholder="例如：強調數位轉型政策、注意資安法規...")

# --- UI: 主畫面 ---
st.title("📋 議題智能摘錄系統")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📤 來源輸入")
    input_type = st.tabs(["檔案上傳", "網頁連結", "文字貼上"])
    
    with input_type[0]:
        uploaded_files = st.file_uploader("支援 Word, PDF, 圖片", accept_multiple_files=True)
    
    with input_type[1]:
        url_input = st.text_input("輸入 Google 表單或網頁連結")
    
    with input_type[2]:
        raw_text = st.text_area("直接貼上內容", height=200)

if st.button("🚀 開始分析", type="primary"):
    combined_content = ""
    error_msgs = []

    # 處理 URL
    if url_input:
        text, err = proc.fetch_url(url_input)
        if err: error_msgs.append(err)
        else: combined_content += f"\n[網頁來源]:\n{text}"

    # 處理檔案
    if uploaded_files:
        for f in uploaded_files:
            if f.name.endswith(".docx"): combined_content += proc.read_docx(f)
            elif f.name.endswith(".pdf"): combined_content += proc.read_pdf(f)
            # 圖片處理邏輯...
    
    combined_content += raw_text

    # 顯示錯誤提醒
    for err in error_msgs: st.warning(err)

    if combined_content.strip():
        with st.spinner("AI 深度分析中..."):
            # 組合 Prompt 與呼叫後端 AI
            # (省略部分 Prompt 組合邏輯，同前次建議)
            res, ai_err = proc.call_ai(api_key, "https://openrouter.ai/api/v1", model, "System Prompt...", combined_content)
            if ai_err:
                st.error(ai_err)
            else:
                st.markdown(res)