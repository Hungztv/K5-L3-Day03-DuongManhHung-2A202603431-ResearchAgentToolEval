from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from chat import run_model_tool_loop
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


@st.cache_resource
def get_provider(name: str) -> Any:
    return make_provider(name)


@st.cache_data
def get_agent_config() -> tuple[str, list[dict[str, Any]]]:
    prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    return prompt, to_openai_tools(declarations)


def clear_chat() -> None:
    st.session_state.messages = []
    st.session_state.tool_events = []


st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")
st.title("🔎 Research Agent")
st.caption("Research agent với chat nhiều lượt và hiển thị tool evidence.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_events" not in st.session_state:
    st.session_state.tool_events = []

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox(
        "Provider",
        ["openrouter", "openai", "anthropic", "gemini", "ollama"],
        index=0,
    )
    model = st.text_input("Model (tuỳ chọn)")
    max_tool_rounds = st.slider("Số vòng tool tối đa", 1, 6, 4)
    if st.button("Xóa cuộc trò chuyện"):
        clear_chat()
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_text = st.chat_input("Nhập yêu cầu nghiên cứu...")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    prompt, tools = get_agent_config()
    provider = get_provider(provider_name)
    messages = [
        {"role": "system", "content": prompt},
        *st.session_state.messages,
    ]

    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=tools,
                model=model or getattr(provider, "default_model", None),
                max_tool_rounds=max_tool_rounds,
            )

        answer = result["assistant_text"] or "Agent không trả về nội dung."
        st.markdown(answer)

        for index, event in enumerate(result["tool_events"], start=1):
            with st.expander(f"Tool {index}: {event.get('tool', 'unknown')}"):
                st.json(
                    {
                        "args": event.get("args", {}),
                        "result": event.get("result", {}),
                    }
                )

        if result["status"] == "waiting_for_user":
            st.info("Agent đang chờ bạn bổ sung thông tin.")
        elif result["status"] == "max_tool_rounds":
            st.warning("Agent đã đạt số vòng tool tối đa.")

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.tool_events.extend(result["tool_events"])

with st.sidebar:
    st.divider()
    st.caption(f"Lượt chat: {len(st.session_state.messages) // 2}")
    st.caption(f"Tool events: {len(st.session_state.tool_events)}")
