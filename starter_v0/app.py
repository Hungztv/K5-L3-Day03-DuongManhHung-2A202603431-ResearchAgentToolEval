"""Streamlit chat UI for the unchanged v0 research-agent artifacts."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from chat import (
    now_iso,
    run_model_tool_loop,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from ui_runtime import execute_with_send_preview
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).resolve().parent
V0_DIR = ROOT / "artifacts" / "v0"
PROMPT_PATH = V0_DIR / "system_prompt.md"
TOOLS_PATH = V0_DIR / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"
VERSION = "v0"
HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4

st.set_page_config(page_title="Research Agent · v0", page_icon="🔎", layout="centered")
load_lab_env(ROOT)


def new_session(provider_name: str, model_name: str) -> dict:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"ui_{VERSION}_{provider_name}_{timestamp}_{uuid4().hex[:6]}"
    artifact = build_artifact_version(VERSION, PROMPT_PATH, TOOLS_PATH)
    transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model_name,
        "system_prompt": str(PROMPT_PATH),
        "tools": str(TOOLS_PATH),
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    return {
        "config": (provider_name, model_name),
        "transcript": transcript,
        "path": TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json",
        "pending_sends": [],
    }


def save_session(session: dict) -> None:
    write_transcript(session["path"], session["transcript"])


def run_turn(session: dict, user_text: str) -> None:
    transcript = session["transcript"]
    history = []
    for turn in transcript["turns"]:
        if turn.get("status") != "provider_error":
            history.extend([
                {"role": "user", "content": turn["user"]},
                {"role": "assistant", "content": turn.get("assistant_text") or ""},
            ])

    pending_sends: list[dict] = []
    turn_record = {
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
        "pending_sends": pending_sends,
        "manual_actions": [],
    }
    try:
        provider = make_provider(transcript["provider"])
        messages = [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8")},
            *trim_history(history, HISTORY_WINDOW),
            {"role": "user", "content": user_text},
        ]
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=to_openai_tools(load_tool_declarations(TOOLS_PATH)),
            model=transcript["model"],
            max_tool_rounds=MAX_TOOL_ROUNDS,
            tool_executor=lambda call: execute_with_send_preview(call, pending_sends),
        )
        turn_record.update(result)
    except Exception as exc:
        turn_record.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {exc}",
            "assistant_text": "Không xử lý được yêu cầu. Xem chi tiết lỗi bên dưới.",
        })
    turn_record["ended_at"] = now_iso()
    transcript["turns"].append(turn_record)
    session["pending_sends"].extend(
        {**item, "turn_index": turn_record["turn_index"]} for item in pending_sends
    )
    save_session(session)


def record_send_decision(session: dict, item: dict, *, confirm: bool) -> None:
    item["status"] = "sent" if confirm else "cancelled"
    if confirm:
        try:
            result = TOOL_FUNCTIONS["send"](text=item["text"], confirmed=True)
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if token and isinstance(result.get("message"), str):
            result["message"] = result["message"].replace(token, "[redacted]")
        if result.get("status") != "sent":
            item["status"] = "error"
    else:
        result = {"status": "cancelled"}

    turn = session["transcript"]["turns"][item["turn_index"] - 1]
    turn["manual_actions"].append({
        "action": "send_telegram",
        "confirmed_by_user": confirm,
        "text": item["text"],
        "result": result,
        "at": now_iso(),
    })
    for pending in turn["pending_sends"]:
        if pending["id"] == item["id"]:
            pending["status"] = item["status"]
    save_session(session)


st.title("🔎 Research Agent")
st.caption("Bản v0 · Tìm kiếm, đọc nguồn và xem agent chọn tool như thế nào")

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini", "ollama"])
    default_model = getattr(make_provider(provider_name), "default_model", "")
    chosen_model = st.text_input("Model", value=default_model, help="Giữ nguyên để dùng model mặc định của provider.")
    model_name = chosen_model.strip() or default_model
    st.caption("Prompt và tool của v0 được lưu riêng trong artifacts/v0/.")

if not PROMPT_PATH.exists() or not TOOLS_PATH.exists():
    st.error("Thiếu bản lưu prompt/tools v0 trong artifacts/v0/.")
    st.stop()

config = (provider_name, model_name)
if "research_session" not in st.session_state or st.session_state.research_session["config"] != config:
    st.session_state.research_session = new_session(*config)
session = st.session_state.research_session

with st.sidebar:
    if st.button("Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.research_session = new_session(*config)
        st.rerun()
    st.caption(f"Artifact: `{session['transcript']['artifact_version']}`")
    st.caption(f"Transcript: `{session['path'].name}`")
    st.download_button(
        "Tải transcript JSON",
        data=json.dumps(session["transcript"], ensure_ascii=False, indent=2, default=str),
        file_name=session["path"].name,
        mime="application/json",
        use_container_width=True,
    )

required_key = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}.get(provider_name)
if required_key and not os.getenv(required_key):
    st.error(f"Chưa có {required_key} trong .env. Hãy cấu hình key rồi tải lại trang.")
    st.stop()

if not session["transcript"]["turns"]:
    st.write("Thử một yêu cầu để xem câu trả lời và các tool đã được gọi.")
    examples = [
        "Tweet mới nhất của Sam Altman là gì?",
        "Tìm tin AI hôm nay trên web.",
        "Tóm tắt bài viết này: https://example.com",
    ]
    columns = st.columns(len(examples))
    example_prompt = next(
        (example for column, example in zip(columns, examples) if column.button(example, use_container_width=True)),
        None,
    )
else:
    example_prompt = None

for turn in session["transcript"]["turns"]:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        st.markdown(turn.get("assistant_text") or "*(Không có nội dung trả lời)*")
        if turn.get("error"):
            st.error(turn["error"])
        for action in turn.get("manual_actions", []):
            status = action["result"].get("status")
            if status == "sent":
                st.success("Đã gửi nội dung lên Telegram.")
            elif status == "cancelled":
                st.info("Đã hủy gửi Telegram.")
            else:
                st.error(f"Gửi Telegram chưa thành công: {action['result']}")
        if turn.get("tool_events"):
            with st.expander(f"Chi tiết tool · {len(turn['tool_events'])} lần gọi"):
                st.json(turn["tool_events"])

for item in session["pending_sends"]:
    if item["status"] != "pending":
        continue
    st.warning("Agent đề xuất gửi nội dung này lên Telegram. Chưa có gì được gửi.")
    st.code(item["text"], language=None)
    send_col, cancel_col = st.columns(2)
    if send_col.button("Xác nhận gửi Telegram", key=f"send_{item['id']}", type="primary"):
        record_send_decision(session, item, confirm=True)
        st.rerun()
    if cancel_col.button("Hủy", key=f"cancel_{item['id']}"):
        record_send_decision(session, item, confirm=False)
        st.rerun()

user_prompt = st.chat_input("Nhập yêu cầu nghiên cứu...") or example_prompt
if user_prompt and user_prompt.strip():
    with st.spinner("Agent đang xử lý..."):
        run_turn(session, user_prompt.strip())
    st.rerun()
