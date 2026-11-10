from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import now_iso, run_model_tool_loop, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "demo"


@st.cache_resource
def get_provider(name: str):
    return make_provider(name)


def start_transcript(provider: str, model: str | None, version: str) -> dict[str, Any]:
    artifact_version = build_artifact_version(
        version,
        ARTIFACTS_DIR / "system_prompt.md",
        ARTIFACTS_DIR / "tools.yaml",
    )
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(provider), timestamp])
    return {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider,
        "model": model,
        "system_prompt": str(ARTIFACTS_DIR / "system_prompt.md"),
        "tools": str(ARTIFACTS_DIR / "tools.yaml"),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }


def render_tool_events(events: list[dict[str, Any]]) -> None:
    for index, event in enumerate(events, start=1):
        name = event.get("tool", "tool")
        args = event.get("args", {})
        result = event.get("result", {})
        with st.expander(f"Công cụ {index}: {name}", expanded=False):
            st.markdown("**Tham số**")
            st.json(args)
            st.markdown("**Kết quả**")
            st.json(result)


st.set_page_config(page_title="Research Agent Demo", page_icon="🔎", layout="wide")
st.title("🔎 Research Agent")
st.caption("Demo local · Tra cứu web/X, đọc URL, hỏi lại khi thiếu thông tin và tổng hợp nguồn.")

with st.sidebar:
    st.subheader("Cấu hình")
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini", "ollama"])
    model = st.text_input("Model (để trống dùng mặc định)", placeholder="Ví dụ: openai/gpt-4o-mini")
    version = st.text_input("Nhãn phiên bản", value="demo-v2")
    st.caption("API key được đọc từ file `.env` trong `starter_v0/`.")
    if st.button("Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.transcript = start_transcript(provider_name, model or None, version)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.history = []
    st.session_state.transcript = start_transcript(provider_name, model or None, version)

active_config = (provider_name, model.strip(), version.strip())
if st.session_state.get("active_config") != active_config:
    if st.session_state.transcript.get("turns"):
        st.info("Cấu hình đã đổi. Bấm **Cuộc trò chuyện mới** để bắt đầu phiên với cấu hình này.")
    else:
        st.session_state.transcript = start_transcript(provider_name, model.strip() or None, version.strip() or "demo")
    st.session_state.active_config = active_config

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tool_events"):
            render_tool_events(message["tool_events"])

prompt = st.chat_input("Ví dụ: Tin AI hôm nay có gì nổi bật?")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    system_prompt = prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    selected_model = model.strip() or None
    turn = {
        "turn_index": len(st.session_state.transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": prompt,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.chat_message("assistant"):
        with st.spinner("Agent đang xử lý..."):
            try:
                result = run_model_tool_loop(
                    provider=get_provider(provider_name),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *st.session_state.history[-10:],
                        {"role": "user", "content": prompt},
                    ],
                    tools=openai_tools,
                    model=selected_model,
                    max_tool_rounds=4,
                )
                turn.update(result)
                answer = result.get("assistant_text") or "Mình chưa nhận được nội dung trả lời từ agent."
                st.markdown(answer)
                render_tool_events(result.get("tool_events", []))
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "tool_events": result.get("tool_events", []),
                })
                st.session_state.history.extend([
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": answer},
                ])
            except Exception as exc:
                answer = f"Không thể chạy agent: {type(exc).__name__}: {exc}"
                turn.update({"status": "provider_error", "error": answer})
                st.error(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

    turn["ended_at"] = now_iso()
    st.session_state.transcript["turns"].append(turn)
    transcript_path = TRANSCRIPTS_DIR / f"{st.session_state.transcript['transcript_id']}.transcript.json"
    write_transcript(transcript_path, st.session_state.transcript)
    st.caption(f"Transcript đã lưu: `{transcript_path.relative_to(ROOT)}`")

if st.session_state.transcript.get("turns"):
    st.caption(f"Phiên bản: `{st.session_state.transcript.get('artifact_version', version)}`")
