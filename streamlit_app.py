import base64
import html
import uuid
from typing import Any

import boto3
import botocore.exceptions
import streamlit as st


APP_TITLE = "Toki-chan"
APP_SUBTITLE = "Memory-aware personal AI assistant"
BRAND_NAME = "TOKAICOM Mitra Indonesia"
MAX_UPLOAD_CHARS = 20_000

ASSISTANT_INSTRUCTION = (
    "You are Toki-chan, a helpful personal AI assistant with AgentCore Memory support. "
    "Help the user with general work, notes, summaries, drafts, planning, and safe memory-aware assistance. "
    "You may also help with AWS topics when asked, but do not force AWS framing. "
    "Keep answers concise, practical, and clear. "
    "Do not greet or address the user by a stored name unless the user provides that name in the current conversation "
    "or explicitly asks you to use it. "
    "Never store or expose secrets, credentials, tokens, passwords, private keys, or confidential data."
)

REQUIRED_SECRETS = (
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "HARNESS_ARN",
)

QUICK_ACTIONS = {
    "Attach": "Use the uploaded context for this request, if one is available.",
    "Search": "Search your available knowledge and answer this clearly: ",
    "Reasoning": "Think through this carefully and show the key reasoning steps: ",
    "Create Image": "Help me draft a detailed image prompt for: ",
    "Deep Research": "Create a concise research brief with sources to check for: ",
}


def load_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #F5F7FB;
                --panel: #FAFBFE;
                --card: #FFFFFF;
                --primary: #635BFF;
                --primary-soft: #F0EFFF;
                --text: #24262D;
                --muted: #80848E;
                --faint: #B8BCC7;
                --border: #E9ECF2;
                --shadow: 0 18px 46px rgba(36, 38, 45, 0.06);
                --soft-shadow: 0 8px 22px rgba(36, 38, 45, 0.05);
            }

            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            #MainMenu,
            footer {
                visibility: hidden;
                height: 0;
            }

            .stApp {
                background: var(--bg);
                color: var(--text);
            }

            .block-container {
                max-width: 100%;
                min-height: 100vh;
                padding: 1rem 1.35rem 2.5rem;
            }

            [data-testid="stAppViewContainer"] {
                display: flex !important;
            }

            [data-testid="stSidebar"] {
                width: 18rem !important;
                min-width: 18rem !important;
                max-width: 18rem !important;
                left: 0 !important;
                transform: translateX(0) !important;
                position: relative !important;
                border-right: 1px solid rgba(233, 236, 242, 0.82);
                background: rgba(255, 255, 255, 0.86);
                box-shadow: 10px 0 40px rgba(36, 38, 45, 0.03);
            }

            [data-testid="stSidebarContent"],
            [data-testid="stSidebarUserContent"] {
                width: 18rem !important;
                min-width: 18rem !important;
                max-width: 18rem !important;
                left: 0 !important;
                transform: translateX(0) !important;
            }

            [data-testid="stAppViewContainer"] > .main {
                flex: 1 1 auto !important;
                min-width: 0 !important;
            }

            [data-testid="stSidebar"] > div:first-child {
                padding: 1.25rem 0.9rem 1rem;
            }

            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] p {
                color: var(--muted);
                font-size: 0.84rem;
            }

            .sidebar-section {
                color: #A2A6B1;
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0;
                margin: 1.25rem 0 0.5rem;
            }

            .sidebar-brand {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                margin: 0.4rem 0 1.15rem;
            }

            .sidebar-brand-title {
                color: var(--text);
                font-size: 0.94rem;
                font-weight: 800;
                line-height: 1.2;
            }

            .sidebar-brand-subtitle {
                color: var(--muted);
                font-size: 0.76rem;
                margin-top: 0.1rem;
            }

            .tokai-logo {
                display: block;
                width: 7.4rem;
                height: auto;
            }

            .tokai-logo-sidebar {
                width: 8.4rem;
                flex: 0 0 auto;
            }

            .st-key-sidebar_search input {
                border-radius: 12px !important;
                border: 1px solid var(--border) !important;
                background: #FFFFFF !important;
                box-shadow: var(--soft-shadow);
                min-height: 2.45rem;
                font-size: 0.82rem !important;
            }

            .sidebar-nav {
                display: grid;
                gap: 0.25rem;
                margin: 0.9rem 0 1rem;
            }

            .sidebar-nav-item {
                display: flex;
                align-items: center;
                gap: 0.62rem;
                min-height: 2.1rem;
                padding: 0.3rem 0.55rem;
                border-radius: 8px;
                color: #6E737E;
                font-size: 0.86rem;
                font-weight: 500;
            }

            .sidebar-nav-item.active {
                background: #F4F6FA;
                color: var(--text);
                font-weight: 700;
            }

            .sidebar-nav-icon {
                width: 1rem;
                color: #9AA0AC;
                text-align: center;
            }

            .sidebar-recent {
                display: grid;
                gap: 0.65rem;
                margin-bottom: 0.75rem;
            }

            .sidebar-recent-item {
                overflow: hidden;
                color: #858995;
                font-size: 0.82rem;
                line-height: 1.3;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sidebar-compact-actions {
                margin-top: 1rem;
            }

            .st-key-app_frame {
                min-height: calc(100vh - 2rem);
                border: 1px solid rgba(233, 236, 242, 0.9);
                border-radius: 14px;
                background:
                    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.95)),
                    var(--panel);
                box-shadow: 0 22px 70px rgba(36, 38, 45, 0.07);
                overflow: hidden;
            }

            .st-key-chat_header {
                padding: 1.35rem 1.65rem 0.5rem;
                background: transparent;
            }

            .chat-header-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
            }

            .chat-title {
                color: var(--text);
                font-size: 0.9rem;
                font-weight: 750;
                line-height: 1.2;
            }

            .chat-subtitle {
                color: var(--muted);
                font-size: 0.74rem;
                margin-top: 0.1rem;
            }

            .model-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                min-height: 2.15rem;
                padding: 0.24rem 0.7rem;
                border: 1px solid var(--border);
                border-radius: 10px;
                background: #FFFFFF;
                color: var(--text);
                box-shadow: var(--soft-shadow);
                font-size: 0.86rem;
                font-weight: 700;
            }

            .model-dot {
                display: inline-grid;
                place-items: center;
                width: 1.25rem;
                height: 1.25rem;
                border-radius: 999px;
                background: var(--primary);
                color: #FFFFFF;
                font-size: 0.72rem;
                font-weight: 800;
            }

            .status-row {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 0.45rem;
                flex-wrap: wrap;
            }

            .status-pill {
                display: inline-flex;
                align-items: center;
                min-height: 1.8rem;
                padding: 0.25rem 0.6rem;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.86);
                color: var(--muted);
                font-size: 0.74rem;
                font-weight: 700;
                white-space: nowrap;
            }

            .status-pill.connected {
                border-color: #D6D4FF;
                background: var(--primary-soft);
                color: #5048E5;
            }

            .empty-state {
                display: flex;
                min-height: 36vh;
                flex-direction: column;
                align-items: center;
                justify-content: flex-end;
                text-align: center;
                padding: 4.2rem 1rem 2rem;
            }

            .assistant-mark {
                display: inline-grid;
                place-items: center;
                width: 3.1rem;
                height: 3.1rem;
                margin-bottom: 1.05rem;
                border: 1px solid #DFDFFF;
                border-radius: 14px;
                background: #FFFFFF;
                color: var(--primary);
                box-shadow: 0 14px 34px rgba(99, 91, 255, 0.15);
                font-size: 1.2rem;
                font-weight: 800;
            }

            .empty-state h1 {
                color: var(--text);
                font-size: 1.72rem;
                font-weight: 760;
                letter-spacing: 0;
                margin: 0;
                line-height: 1.24;
            }

            .empty-state .accent {
                color: var(--primary);
            }

            .chat-history {
                width: min(58rem, calc(100% - 3rem));
                margin: 0 auto;
                padding: 0.7rem 0 1rem;
            }

            [data-testid="stChatMessage"] {
                border: 1px solid var(--border);
                border-radius: 16px;
                background: #FFFFFF;
                box-shadow: var(--shadow);
                padding: 0.6rem 0.75rem;
                margin-bottom: 0.85rem;
            }

            .user-bubble {
                max-width: 74%;
                margin: 0 0 0.85rem auto;
                padding: 0.72rem 0.9rem;
                border: 1px solid #D6D4FF;
                border-radius: 14px 14px 4px 14px;
                background: var(--primary-soft);
                color: var(--text);
                box-shadow: 0 10px 24px rgba(99, 91, 255, 0.08);
                white-space: pre-wrap;
            }

            .assistant-bubble {
                max-width: 84%;
                margin: 0 auto 0.85rem 0;
                padding: 0.84rem 0.96rem;
                border: 1px solid var(--border);
                border-radius: 14px 14px 14px 4px;
                background: #FFFFFF;
                color: var(--text);
                box-shadow: var(--shadow);
                white-space: pre-wrap;
            }

            .st-key-message_composer {
                width: min(46rem, calc(100% - 3rem));
                margin: 0 auto 2.8rem;
            }

            .st-key-message_composer [data-testid="stForm"] {
                padding: 0.78rem 0.9rem 0.7rem;
                border: 1px solid var(--border);
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.92);
                box-shadow: 0 18px 44px rgba(36, 38, 45, 0.08);
            }

            .st-key-message_composer [data-testid="stTextInputRootElement"] {
                min-height: 6.2rem !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                align-items: flex-start !important;
                padding-top: 1.05rem !important;
            }

            .st-key-message_composer input {
                background: transparent !important;
                color: var(--text) !important;
                font-size: 0.92rem !important;
                line-height: 1.4 !important;
            }

            .st-key-message_composer input::placeholder {
                color: #777C88 !important;
            }

            .st-key-message_composer [data-baseweb="input"],
            .st-key-message_composer [data-baseweb="input"] > div {
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            .st-key-message_composer div[data-testid="stFormSubmitButton"] > button {
                min-height: 2.25rem;
                border-radius: 10px;
                background: var(--primary);
                border-color: var(--primary);
                color: #FFFFFF;
                box-shadow: 0 9px 18px rgba(99, 91, 255, 0.18);
                font-weight: 750;
            }

            .composer-hint {
                color: var(--faint);
                font-size: 0.78rem;
                margin: -0.2rem 0 0.65rem;
            }

            .st-key-composer_actions {
                width: min(46rem, calc(100% - 3rem));
                margin: -4.45rem auto 2.8rem;
                padding: 0 0.85rem;
                position: relative;
                z-index: 2;
            }

            .st-key-composer_actions div.stButton > button {
                min-height: 1.95rem;
                border-radius: 8px;
                border: 1px solid var(--border);
                background: rgba(255, 255, 255, 0.9);
                color: var(--text);
                font-size: 0.74rem;
                font-weight: 650;
                box-shadow: 0 6px 15px rgba(36, 38, 45, 0.04);
                white-space: nowrap;
            }

            .st-key-composer_actions div.stButton > button:hover,
            div.stButton > button:hover {
                border-color: #D6D4FF;
                background: var(--primary-soft);
                color: #5048E5;
            }

            div.stButton > button,
            div.stDownloadButton > button {
                border: 1px solid var(--border);
                border-radius: 9px;
                background: #FFFFFF;
                color: var(--text);
                font-weight: 700;
            }

            .st-key-top_new_chat button {
                width: auto;
                min-height: 2.2rem;
                padding: 0.25rem 0.85rem;
                border-radius: 9px;
                border-color: #101115;
                background: #101115;
                color: #FFFFFF;
                box-shadow: 0 10px 22px rgba(16, 17, 21, 0.16);
            }

            .debug-note {
                color: var(--muted);
                font-size: 0.82rem;
            }

            @media (max-width: 900px) {
                .block-container {
                    padding: 0.75rem;
                }

                .st-key-app_frame {
                    min-height: calc(100vh - 1.5rem);
                    border-radius: 12px;
                }

                .st-key-chat_header {
                    padding: 1rem 1rem 0.25rem;
                }

                .chat-header-row {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .status-row {
                    justify-content: flex-start;
                }

                .user-bubble,
                .assistant-bubble {
                    max-width: 96%;
                }

                .empty-state {
                    min-height: 32vh;
                    padding-top: 2.25rem;
                }

                .empty-state h1 {
                    font-size: 1.38rem;
                }

                .st-key-message_composer,
                .st-key-composer_actions,
                .chat-history {
                    width: calc(100% - 1.5rem);
                }

                .st-key-composer_actions {
                    margin-top: -4.2rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def shorten(value: str, prefix: int = 12, suffix: int = 6) -> str:
    if not value:
        return "Not configured"
    if len(value) <= prefix + suffix + 3:
        return value
    return f"{value[:prefix]}...{value[-suffix:]}"


def render_tokai_logo(extra_class: str = "") -> str:
    class_attr = f"tokai-logo {extra_class}".strip()
    logo_svg = """
    <svg viewBox="0 0 176 65" role="img" aria-label="TOKAICOM Mitra Indonesia logo"
        xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="tokaiWingA" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#004ea8"/>
                <stop offset="1" stop-color="#2f72d9"/>
            </linearGradient>
            <linearGradient id="tokaiWingB" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#486eb8"/>
                <stop offset="1" stop-color="#d5def4"/>
            </linearGradient>
            <linearGradient id="tokaiWingC" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#0c5db8"/>
                <stop offset="1" stop-color="#c7d6f2"/>
            </linearGradient>
        </defs>
        <g transform="translate(0 14)">
            <path d="M3 17 L30 7 L27 19 L0 29 Z" fill="url(#tokaiWingA)"/>
            <path d="M28 6 L58 0 L52 17 L24 22 Z" fill="url(#tokaiWingB)"/>
            <path d="M27 21 L52 16 L45 32 L18 36 Z" fill="url(#tokaiWingC)"/>
            <path d="M7 29 L19 25 L14 38 L2 40 Z" fill="#005eb8"/>
            <text x="5" y="47" fill="#005eb8" font-family="Arial, Helvetica, sans-serif"
                font-size="5" font-weight="700" font-style="italic">TOKAI GROUP</text>
        </g>
        <g fill="#005eb8" font-family="Arial, Helvetica, sans-serif">
            <text x="66" y="14" font-size="20" font-weight="500" letter-spacing="0">TOKAICOM</text>
            <text x="66" y="36" font-size="20" font-weight="500" letter-spacing="0">Mitra</text>
            <text x="66" y="58" font-size="20" font-weight="500" letter-spacing="0">Indonesia</text>
        </g>
    </svg>
    """
    logo_data = base64.b64encode(logo_svg.encode("utf-8")).decode("ascii")
    return (
        f'<img class="{html.escape(class_attr)}" '
        f'src="data:image/svg+xml;base64,{logo_data}" '
        'alt="TOKAICOM Mitra Indonesia logo" />'
    )


def validate_secrets() -> dict[str, str]:
    missing = [key for key in REQUIRED_SECRETS if not st.secrets.get(key)]
    if missing:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                {render_tokai_logo()}
                <div>
                    <div class="sidebar-brand-title">{html.escape(BRAND_NAME)}</div>
                    <div class="sidebar-brand-subtitle">Setup required</div>
                </div>
            </div>
            <div class="assistant-bubble">
                <strong>Setup Required</strong><br>
                Add the missing Streamlit Secrets below, then redeploy or rerun the app.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code("\n".join(missing), language="text")
        st.stop()

    return {key: str(st.secrets[key]) for key in REQUIRED_SECRETS}


def login_gate() -> None:
    app_password = st.secrets.get("APP_PASSWORD", "")
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False if app_password else True

    if st.session_state.authenticated:
        return

    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-orb"></div>
            <h1>{html.escape(APP_TITLE)}</h1>
            <p>{html.escape(APP_SUBTITLE)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    password = st.text_input("Password", type="password")
    if st.button("Login", type="primary", use_container_width=True):
        if password == app_password:
            st.session_state.authenticated = True
            st.rerun()
        st.error("Wrong password")
    st.stop()


def init_session() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("runtime_session_id", str(uuid.uuid4()))
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("pending_context", None)
    st.session_state.setdefault("last_event_summary", [])
    st.session_state.setdefault("last_invocation_error", None)
    st.session_state.setdefault("uploaded_context", None)


def build_prompt(user_prompt: str, uploaded_context: str | None = None) -> str:
    context_block = ""
    if uploaded_context:
        context_block = (
            "\n\nUploaded context follows. Use it only for this request.\n"
            "--- BEGIN CONTEXT ---\n"
            f"{uploaded_context[:MAX_UPLOAD_CHARS]}\n"
            "--- END CONTEXT ---"
        )

    return (
        f"{ASSISTANT_INSTRUCTION}\n\n"
        "Respond in Indonesian or English following the user's message.\n\n"
        f"User request:\n{user_prompt.strip()}"
        f"{context_block}"
    )


def create_agentcore_client(secrets: dict[str, str]) -> Any:
    return boto3.client(
        "bedrock-agentcore",
        region_name=secrets["AWS_REGION"],
        aws_access_key_id=secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=secrets["AWS_SECRET_ACCESS_KEY"],
    )


def sanitize_sensitive_text(value: Any, secrets: dict[str, str]) -> str:
    text = str(value)
    replacements = {
        secrets.get("AWS_ACCESS_KEY_ID", ""): "[masked access key]",
        secrets.get("AWS_SECRET_ACCESS_KEY", ""): "[masked secret key]",
        secrets.get("HARNESS_ARN", ""): shorten(secrets.get("HARNESS_ARN", ""), 18, 8),
    }
    for raw_value, replacement in replacements.items():
        if raw_value:
            text = text.replace(raw_value, replacement)
    return text


def summarize_event(event: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]:
    event_type = next(iter(event.keys()), "unknown")
    summary: dict[str, Any] = {"type": event_type}

    if event_type == "contentBlockDelta":
        delta = event[event_type].get("delta", {})
        summary["has_text"] = "text" in delta
        summary["text_chars"] = len(delta.get("text", ""))
    elif event_type in {"runtimeClientError", "validationException"}:
        value = event.get(event_type, {})
        if isinstance(value, dict):
            summary["message"] = sanitize_sensitive_text(value.get("message", "Error event received"), secrets)
        else:
            summary["message"] = sanitize_sensitive_text(value, secrets)
    elif isinstance(event.get(event_type), dict):
        summary["keys"] = list(event[event_type].keys())

    return summary


def invoke_harness(prompt: str) -> str:
    secrets = validate_secrets()
    session_id = st.session_state.runtime_session_id
    st.session_state.last_event_summary = []
    st.session_state.last_invocation_error = None

    try:
        client = create_agentcore_client(secrets)
        response = client.invoke_harness(
            harnessArn=secrets["HARNESS_ARN"],
            runtimeSessionId=session_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
        )

        output_parts: list[str] = []
        for event in response.get("stream", []):
            st.session_state.last_event_summary.append(summarize_event(event, secrets))

            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    output_parts.append(delta["text"])
            elif "messageStop" in event:
                continue
            elif "runtimeClientError" in event:
                message = sanitize_sensitive_text(
                    event["runtimeClientError"].get("message", "Runtime client error"),
                    secrets,
                )
                output_parts.append(f"\nAgentCore runtime error: {message}")
            elif "validationException" in event:
                value = event["validationException"]
                message = value.get("message", value) if isinstance(value, dict) else value
                message = sanitize_sensitive_text(message, secrets)
                output_parts.append(f"\nValidation error: {message}")

        output = "".join(output_parts).strip()
        return output or "No response from AgentCore Harness."

    except botocore.exceptions.ClientError as exc:
        message = exc.response.get("Error", {}).get("Message", str(exc))
        message = sanitize_sensitive_text(message, secrets)
        st.session_state.last_invocation_error = message
        return f"AgentCore Harness returned an AWS client error: {message}"
    except Exception as exc:
        st.session_state.last_invocation_error = sanitize_sensitive_text(exc, secrets)
        return "I could not reach AgentCore Harness. Please check the app secrets, Harness ARN, region, and AWS permissions."


def read_uploaded_text(uploaded_file: Any) -> tuple[str, bool]:
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > MAX_UPLOAD_CHARS
    return text[:MAX_UPLOAD_CHARS], truncated


def send_message(user_prompt: str, uploaded_context: str | None = None) -> None:
    prompt = user_prompt.strip()
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    final_prompt = build_prompt(prompt, uploaded_context)
    with st.spinner("Thinking..."):
        output = invoke_harness(final_prompt)
    st.session_state.messages.append({"role": "assistant", "content": output})
    st.session_state.uploaded_context = None
    st.rerun()


def reset_chat() -> None:
    st.session_state.runtime_session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.last_event_summary = []
    st.session_state.last_invocation_error = None
    st.session_state.uploaded_context = None


def render_sidebar(secrets: dict[str, str]) -> None:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                {render_tokai_logo("tokai-logo-sidebar")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="sidebar_search"):
            st.text_input("Search", placeholder="Search", label_visibility="collapsed")

        st.markdown(
            """
            <div class="sidebar-nav">
                <div class="sidebar-nav-item active"><span class="sidebar-nav-icon">H</span>Home</div>
                <div class="sidebar-nav-item"><span class="sidebar-nav-icon">E</span>Explore</div>
                <div class="sidebar-nav-item"><span class="sidebar-nav-icon">L</span>Library</div>
                <div class="sidebar-nav-item"><span class="sidebar-nav-icon">R</span>History</div>
            </div>
            <div class="sidebar-section">Tomorrow</div>
            <div class="sidebar-recent">
                <div class="sidebar-recent-item">What's something you've learned...</div>
                <div class="sidebar-recent-item">If you could teleport anywhere...</div>
                <div class="sidebar-recent-item">What's one goal you want to ac...</div>
            </div>
            <div class="sidebar-section">7 Days Ago</div>
            <div class="sidebar-recent">
                <div class="sidebar-recent-item">Ask me anything weird or rand...</div>
                <div class="sidebar-recent-item">How are you feeling today, reall...</div>
                <div class="sidebar-recent-item">What's one habit you wish you...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-compact-actions">', unsafe_allow_html=True)
        if st.button("New Chat", use_container_width=True):
            reset_chat()
            st.rerun()
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Upload Context", expanded=False):
            uploaded_file = st.file_uploader("Upload Context", type=["txt", "md", "csv", "json", "py", "log"])
            if uploaded_file:
                uploaded_context, truncated = read_uploaded_text(uploaded_file)
                st.session_state.uploaded_context = uploaded_context
                size_kb = len(uploaded_file.getvalue()) / 1024
                st.caption(f"{uploaded_file.name} - {size_kb:.1f} KB")
                if truncated:
                    st.caption(f"Limited to {MAX_UPLOAD_CHARS:,} characters.")
                with st.expander("Preview", expanded=False):
                    st.text(uploaded_context[:3_000])

        with st.expander("Memory", expanded=False):
            if st.button("What do you remember?", use_container_width=True):
                send_message("Retrieve and summarize relevant safe memory context.")

            preference = st.text_area(
                "Preference to remember",
                height=84,
                placeholder="Example: I prefer short weekly summaries.",
            )
            if st.button("Remember", use_container_width=True):
                if preference.strip():
                    send_message(
                        "Store this as safe reusable memory if appropriate. "
                        f"Do not store secrets or confidential data: {preference.strip()}"
                    )
                else:
                    st.warning("Add a preference first.")

            forget_target = st.text_input("Forget / mark inactive", placeholder="Optional memory or preference")
            if st.button("Forget / Mark inactive", use_container_width=True):
                target = forget_target.strip() or "the relevant memory/preference"
                send_message(f"Forget or mark inactive this memory/preference if supported: {target}")

        with st.expander("Debug", expanded=False):
            try:
                client = create_agentcore_client(secrets)
                method_available = hasattr(client, "invoke_harness")
            except Exception:
                method_available = False

            st.markdown('<div class="debug-note">Sensitive values are masked.</div>', unsafe_allow_html=True)
            st.json(
                {
                    "region": secrets["AWS_REGION"],
                    "harness_arn_short": shorten(secrets["HARNESS_ARN"], 18, 8),
                    "runtime_session_id": st.session_state.runtime_session_id,
                    "invoke_harness_available": method_available,
                    "last_invocation_error": st.session_state.last_invocation_error,
                    "last_event_summary": st.session_state.last_event_summary,
                }
            )

        with st.expander("Account", expanded=False):
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()


def render_header(secrets: dict[str, str]) -> None:
    region = secrets.get("AWS_REGION", "Not configured")
    session_short = shorten(st.session_state.runtime_session_id, 8, 4)

    with st.container(key="chat_header"):
        left, right = st.columns([1, 1], vertical_alignment="center")
        with left:
            st.markdown(
                f"""
                <div class="model-pill">
                    <span class="model-dot">T</span>
                    <span>{html.escape(APP_TITLE)} 4o</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            status_col, button_col = st.columns([0.78, 0.22], vertical_alignment="center")
            with status_col:
                st.markdown(
                    f"""
                    <div class="status-row">
                        <span class="status-pill connected">AgentCore</span>
                        <span class="status-pill">{html.escape(region)}</span>
                        <span class="status-pill">{html.escape(session_short)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with button_col:
                if st.button("New Chat", key="top_new_chat"):
                    reset_chat()
                    st.rerun()


def render_chat_history() -> None:
    st.markdown('<main class="chat-history">', unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown(
            """
            <div class="empty-state">
                <div class="assistant-mark">T</div>
                <h1>Good Morning<br>How Can I <span class="accent">Assist You Today?</span></h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for message in st.session_state.messages:
            content = str(message["content"])
            if message["role"] == "user":
                st.markdown(f'<div class="user-bubble">{html.escape(content)}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-bubble">{html.escape(content)}</div>', unsafe_allow_html=True)
    st.markdown("</main>", unsafe_allow_html=True)


def render_composer() -> None:
    uploaded_context = st.session_state.get("uploaded_context")
    with st.container(key="message_composer"):
        with st.form("message_composer_form", clear_on_submit=True):
            if uploaded_context:
                st.markdown(
                    '<div class="composer-hint">Uploaded context is ready for the next message.</div>',
                    unsafe_allow_html=True,
                )
            prompt = st.text_input(
                "Message",
                placeholder="Initiate a query or send a command to the AI...",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send")

    if submitted and prompt:
        send_message(prompt, uploaded_context)


def render_quick_actions() -> None:
    with st.container(key="composer_actions"):
        columns = st.columns(5)
        for column, (label, prompt) in zip(columns, QUICK_ACTIONS.items()):
            with column:
                if st.button(label, use_container_width=True):
                    send_message(prompt)


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="T",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()
    login_gate()
    init_session()
    secrets = validate_secrets()
    render_sidebar(secrets)
    with st.container(key="app_frame"):
        render_header(secrets)
        render_chat_history()
        render_composer()
        render_quick_actions()


if __name__ == "__main__":
    main()
