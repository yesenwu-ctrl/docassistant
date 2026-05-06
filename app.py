import streamlit as st

from processor import ContentProcessor


st.set_page_config(page_title="AI擬答助理", layout="wide")

proc = ContentProcessor()


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@600;700&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            --ink: #1e2019;
            --muted: #6a6a5f;
            --paper: #fffaf0;
            --sage: #dfe8cf;
            --clay: #c96f4a;
            --moss: #47533d;
            --line: rgba(30, 32, 25, 0.12);
        }

        .stApp {
            color: var(--ink);
            background:
                radial-gradient(circle at 8% 8%, rgba(201, 111, 74, 0.22), transparent 28rem),
                radial-gradient(circle at 90% 18%, rgba(111, 138, 86, 0.26), transparent 26rem),
                linear-gradient(135deg, #fffaf0 0%, #f4ecd9 48%, #eef1df 100%);
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 250, 240, 0.86);
            border-right: 1px solid var(--line);
            backdrop-filter: blur(18px);
        }

        h1, h2, h3 {
            font-family: 'Noto Serif TC', serif;
            letter-spacing: -0.035em;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.4rem;
            border: 1px solid var(--line);
            border-radius: 34px;
            background:
                linear-gradient(140deg, rgba(255, 250, 240, 0.92), rgba(223, 232, 207, 0.72)),
                repeating-linear-gradient(90deg, rgba(71, 83, 61, 0.05) 0 1px, transparent 1px 18px);
            box-shadow: 0 28px 80px rgba(71, 83, 61, 0.14);
        }

        .hero:after {
            content: "";
            position: absolute;
            right: -4rem;
            top: -5rem;
            width: 16rem;
            height: 16rem;
            border-radius: 999px;
            background: rgba(201, 111, 74, 0.18);
        }

        .eyebrow {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--clay);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .hero h1 {
            max-width: 820px;
            margin: 0.35rem 0 0.8rem;
            font-size: clamp(2.2rem, 6vw, 4.8rem);
            line-height: 0.96;
        }

        .hero p {
            max-width: 760px;
            color: var(--muted);
            font-size: 1.05rem;
            line-height: 1.8;
        }

        .metric-card {
            min-height: 118px;
            padding: 1.15rem;
            border-radius: 24px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.52);
        }

        .metric-card strong {
            display: block;
            color: var(--moss);
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.7rem;
        }

        .stButton > button {
            border: 0;
            border-radius: 999px;
            padding: 0.82rem 1.4rem;
            background: linear-gradient(135deg, var(--moss), #273022);
            color: #fffaf0;
            box-shadow: 0 16px 36px rgba(71, 83, 61, 0.24);
        }

        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
            border-radius: 18px;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 24px;
            background: rgba(255, 250, 240, 0.55);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def append_text_section(buffer, title, content):
    if content and content.strip():
        buffer.append(f"## {title}\n{content.strip()}")


def collect_uploaded_content(files, include_images=False):
    text_sections = []
    image_data_urls = []
    warnings = []

    for file in files or []:
        lower_name = file.name.lower()
        try:
            if lower_name.endswith(".docx"):
                append_text_section(text_sections, f"檔案：{file.name}", proc.read_docx(file))
            elif lower_name.endswith(".pdf"):
                append_text_section(text_sections, f"檔案：{file.name}", proc.read_pdf(file))
            elif lower_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
                if include_images:
                    image_data_urls.append(proc.image_to_data_url(file))
                    append_text_section(text_sections, f"圖片：{file.name}", "已附上圖片，請直接閱讀圖片內容。")
                else:
                    warnings.append(f"已略過圖片「{file.name}」，因目前選擇純文字模式。")
            elif lower_name.endswith(".txt") or lower_name.endswith(".md"):
                append_text_section(text_sections, f"檔案：{file.name}", file.getvalue().decode("utf-8", errors="ignore"))
            else:
                warnings.append(f"暫不支援「{file.name}」的檔案格式。")
        except Exception:
            warnings.append(f"讀取「{file.name}」時發生錯誤，請改用貼上文字。")

    return "\n\n".join(text_sections), image_data_urls, warnings


def resolve_ai_config(api_key):
    stripped_key = (api_key or "").strip()
    if stripped_key.startswith("sk-or-"):
        return "https://openrouter.ai/api/v1", "deepseek/deepseek-chat", "OpenRouter / DeepSeek Chat"
    return "https://api.deepseek.com", "deepseek-chat", "DeepSeek Chat"


def build_prompt(reply_goal, reply_tone, response_format, source_content, reference_content, user_direction):
    system_prompt = f"""
你是一位謹慎、精準且善於擬稿的中文助理。你的任務不是只整理摘要，而是根據使用者提供的來源內容與參考資料，直接產出可使用的回覆草稿。

寫作規則：
1. 優先回答對方真正需要的內容，不要只做條列摘錄。
2. 若來源內容資訊不足，請在回覆中以溫和方式標明「需要補充確認」的地方，不要捏造。
3. 參考資料只能作為補強脈絡，不得覆蓋來源內容中的明確事實。
4. 語氣使用「{reply_tone}」。
5. 輸出格式使用「{response_format}」。
6. 若內容涉及法規、承諾、數字或時程，請用保守措辭並提示需人工複核。
""".strip()

    user_prompt = f"""
# 我想請 AI 完成的回覆任務
{reply_goal.strip() or "請根據來源內容擬一份完整、清楚、可直接修改使用的回覆。"}

# 使用者額外要求
{user_direction.strip() or "無"}

# 需要回覆的來源內容
{source_content.strip()}

# 可參考的背景資料
{reference_content.strip() or "無"}
""".strip()

    return system_prompt, user_prompt


with st.sidebar:
    st.caption("AI SERVICE")
    st.header("API 金鑰")
    api_key = st.text_input("API Key", type="password", placeholder="貼上 DeepSeek 或 OpenRouter API Key")
    base_url, model, resolved_model_label = resolve_ai_config(api_key)
    st.caption(f"系統會自動使用：{resolved_model_label}")

    st.divider()
    st.caption("WRITING CONTROL")
    reply_tone = st.selectbox("回覆語氣", ["正式清楚", "友善專業", "簡潔直接", "溫和說明", "政策幕僚風格"])
    response_format = st.selectbox("輸出格式", ["完整回覆信件", "正式公文式回覆", "條列說明", "Line/簡訊短回覆", "Markdown 草稿"])
    user_direction = st.text_area("特別注意事項", placeholder="例如：避免承諾時程、引用資安法規、需要先感謝對方...")


st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">AI Reply Assistant</div>
        <h1>AI擬答助理</h1>
        <p>
            上傳來文或貼上文字，再補充參考資料與回覆方向，
            讓 AI 直接擬好一份可修改、可送出的草稿。
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(3)
with metric_cols[0]:
    st.markdown('<div class="metric-card"><strong>01</strong>貼上 API Key</div>', unsafe_allow_html=True)
with metric_cols[1]:
    st.markdown('<div class="metric-card"><strong>02</strong>放入來文與參考資料</div>', unsafe_allow_html=True)
with metric_cols[2]:
    st.markdown('<div class="metric-card"><strong>03</strong>生成可直接修改的回覆</div>', unsafe_allow_html=True)

st.write("")

left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("需要回覆的內容")
    source_tabs = st.tabs(["檔案上傳", "網頁連結", "文字貼上"])

    with source_tabs[0]:
        uploaded_files = st.file_uploader(
            "上傳來文、PDF、Word 或文字檔",
            type=["docx", "pdf", "txt", "md"],
            accept_multiple_files=True,
        )

    with source_tabs[1]:
        url_input = st.text_input("貼上公開網頁或 Google 表單連結")

    with source_tabs[2]:
        raw_text = st.text_area("直接貼上需要回覆的內容", height=220, placeholder="把對方來信、問題、會議紀錄或申請內容貼在這裡。")

with right:
    st.subheader("參考資料與任務")
    reply_goal = st.text_area(
        "你希望 AI 幫你怎麼回？",
        height=120,
        placeholder="例如：請幫我回覆承辦單位，說明本案可先提供初步資料，但正式時程需待內部確認。",
    )
    reference_text = st.text_area(
        "可參考資料",
        height=220,
        placeholder="貼上政策背景、過往回覆、內部原則、注意事項或希望 AI 參考但不要逐字照抄的資料。",
    )
    reference_files = st.file_uploader(
        "補充參考檔案",
        type=["docx", "pdf", "txt", "md"],
        accept_multiple_files=True,
        key="reference_files",
    )

generate = st.button("生成 AI 回覆草稿", type="primary", use_container_width=True)

if generate:
    source_parts = []
    reference_parts = []
    image_data_urls = []
    warnings = []

    uploaded_text, uploaded_images, uploaded_warnings = collect_uploaded_content(
        uploaded_files,
        include_images=False,
    )
    append_text_section(source_parts, "上傳內容", uploaded_text)
    image_data_urls.extend(uploaded_images)
    warnings.extend(uploaded_warnings)

    if url_input:
        url_text, url_error = proc.fetch_url(url_input)
        if url_error:
            warnings.append(url_error)
        else:
            append_text_section(source_parts, "網頁內容", url_text)

    append_text_section(source_parts, "貼上文字", raw_text)

    reference_file_text, _, reference_warnings = collect_uploaded_content(reference_files, include_images=False)
    append_text_section(reference_parts, "貼上參考資料", reference_text)
    append_text_section(reference_parts, "參考檔案", reference_file_text)
    warnings.extend(reference_warnings)

    for warning in warnings:
        st.warning(warning)

    source_content = "\n\n".join(source_parts)
    reference_content = "\n\n".join(reference_parts)

    if not source_content.strip():
        st.error("請至少提供一段需要回覆的內容。")
    elif not api_key.strip():
        st.error("請先在左側輸入 API Key。")
    else:
        system_prompt, user_prompt = build_prompt(
            reply_goal,
            reply_tone,
            response_format,
            source_content,
            reference_content,
            user_direction,
        )

        with st.spinner("AI 正在閱讀資料並擬回覆..."):
            result, ai_error = proc.call_ai(
                api_key,
                base_url,
                model,
                system_prompt,
                user_prompt,
                image_data_urls=image_data_urls,
            )

        if ai_error:
            st.error(ai_error)
        else:
            st.success("已生成回覆草稿，請人工複核後再送出。")
            st.markdown("### AI 回覆草稿")
            st.markdown(result)

            with st.expander("查看本次送給 AI 的整理內容"):
                st.markdown(user_prompt)
