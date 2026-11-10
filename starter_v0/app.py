from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from chat import run_model_tool_loop
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
PROVIDERS = ["gemini", "groq", "openrouter", "openai", "anthropic", "ollama"]


def main() -> None:
    st.set_page_config(page_title="Research Agent", page_icon="🔎")
    st.title("Research Agent")
    st.caption("Tìm kiếm, đọc nguồn và tổng hợp thông tin có dẫn nguồn.")

    with st.sidebar:
        provider_name = st.selectbox("Model provider", PROVIDERS, index=0)
        model_name = None
        if provider_name == "ollama":
            model_name = st.text_input(
                "Ollama model",
                value=os.getenv("OLLAMA_MODEL", "nemotron-3-super:cloud"),
            )
        if st.button("Cuộc trò chuyện mới"):
            st.session_state.messages = []
            st.rerun()

    messages: list[dict[str, str]] = st.session_state.setdefault("messages", [])
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Bạn muốn tìm hiểu điều gì?")
    if not prompt:
        return

    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
            declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
            result = run_model_tool_loop(
                provider=make_provider(provider_name),
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
                tools=to_openai_tools(declarations),
                model=model_name,
                max_tool_rounds=4,
            )
            answer = result.get("assistant_text") or "Không có nội dung trả lời."
            st.markdown(answer)
            if result.get("tool_events"):
                with st.expander("Chi tiết tool đã chạy"):
                    for event in result["tool_events"]:
                        st.markdown(f"**{event.get('tool', 'tool')}**")
                        st.json(event.get("result", {}))
            messages.append({"role": "assistant", "content": answer})
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
