from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import run_model_tool_loop, trim_history
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
VERSIONS_DIR = ARTIFACTS_DIR / "versions"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_transcript() -> None:
    transcript = st.session_state["transcript"]
    transcript["updated_at"] = now_iso()
    path = Path(transcript["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def version_artifact_paths(version: str) -> tuple[Path, Path]:
    version_dir = VERSIONS_DIR / version
    prompt_path = version_dir / "system_prompt.md"
    tools_path = version_dir / "tools.yaml"
    if not prompt_path.is_file() or not tools_path.is_file():
        raise ValueError(f"Chưa có artifact snapshot cho {version}.")
    return prompt_path, tools_path


def start_session(provider_name: str, model: str, version: str) -> None:
    prompt_path, tools_path = version_artifact_paths(version)
    artifact_version = build_artifact_version(version, prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    path = TRANSCRIPTS_DIR / f"{version}_{provider_name}_{timestamp}.transcript.json"
    st.session_state["provider_name"] = provider_name
    st.session_state["model"] = model.strip() or None
    st.session_state["system_prompt"] = prompt_path.read_text(encoding="utf-8")
    st.session_state["tools"] = to_openai_tools(load_tool_declarations(tools_path))
    st.session_state["history"] = []
    st.session_state["transcript"] = {
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": model.strip() or None,
        "system_prompt": str(prompt_path),
        "tools": str(tools_path),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "path": str(path),
        "turns": [],
    }
    save_transcript()


def render_tool_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        with st.expander(f"Tool: {event.get('tool', 'unknown')}"):
            st.json({"args": event.get("args", {}), "result": event.get("result", {})})


st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")
st.title("🔎 Research Agent")
st.caption("Tìm kiếm, đọc và tổng hợp thông tin bằng các tool của nhóm.")

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["groq", "gemini", "openrouter", "openai", "anthropic", "ollama"])
    model = st.text_input("Model (để trống dùng mặc định)", value="")
    version = st.selectbox("Artifact version", ["v0", "v1", "v2"])
    if st.button("Bắt đầu phiên mới"):
        start_session(provider_name, model, version)
        st.rerun()

if "transcript" not in st.session_state:
    start_session(provider_name, model, version)

for turn in st.session_state["transcript"]["turns"]:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        if turn.get("status") == "provider_error":
            st.error(turn.get("error", "Provider error"))
        else:
            st.write(turn.get("assistant_text", ""))
            render_tool_events(turn.get("tool_events", []))

user_text = st.chat_input("Bạn muốn tìm hiểu điều gì?")
if user_text:
    turn_index = len(st.session_state["transcript"]["turns"]) + 1
    turn_record: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    with st.chat_message("user"):
        st.write(user_text)
    try:
        provider = make_provider(st.session_state["provider_name"])
        messages = [
            {"role": "system", "content": st.session_state["system_prompt"]},
            *trim_history(st.session_state["history"], 5),
            {"role": "user", "content": user_text},
        ]
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=st.session_state["tools"],
            model=st.session_state["model"],
            max_tool_rounds=4,
        )
        turn_record.update(result)
        st.session_state["history"].extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": result["assistant_text"]},
        ])
        with st.chat_message("assistant"):
            st.write(result["assistant_text"])
            render_tool_events(result["tool_events"])
    except Exception as exc:
        turn_record.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {exc}",
        })
        with st.chat_message("assistant"):
            st.error(turn_record["error"])
    turn_record["ended_at"] = now_iso()
    st.session_state["transcript"]["turns"].append(turn_record)
    save_transcript()

st.sidebar.caption(f"Transcript: {st.session_state['transcript']['path']}")
