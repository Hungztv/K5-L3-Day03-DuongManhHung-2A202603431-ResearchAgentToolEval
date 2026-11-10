# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team:
- Members:
- Provider/model: Gemini / gemini-3.5-flash

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent hỗ trợ tìm tin trên web/X, đọc URL và paper arXiv, tra cứu chính sách nội bộ, kiểm tra danh sách nguồn, rồi tổng hợp digest có dẫn nguồn. Agent hỏi lại khi thiếu thông tin và chỉ gửi Telegram sau khi người dùng duyệt nội dung, đích nhận và xác nhận rõ ràng.

**Link dùng thử (deploy):**

> UI Streamlit có thể chạy cục bộ bằng `streamlit run app.py` trong `starter_v0`. Chưa deploy public.
>
> URL: Chưa deploy

## A2. Tool agent có

> Liệt kê các tool agent đang dùng (gồm tool mới nhóm tự thêm). Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại khi thiếu thông tin hoặc cần xác nhận | không |
| timeline | Lấy bài đăng gần đây từ một tài khoản X | không |
| social_search | Tìm bài đăng X theo chủ đề, mới nhất hoặc phổ biến | không |
| lookup | Tìm thông tin trên web, gồm tin tức theo khoảng thời gian | không |
| fetch | Đọc nội dung của URL cụ thể | không |
| format | Định dạng các item có sẵn thành digest Markdown | không |
| source_audit | Phát hiện tiêu đề/URL thiếu, URL sai và URL trùng trong danh sách nguồn | có |
| send | Gửi nội dung tới Telegram đã cấu hình sau xác nhận rõ ràng | không |
| policy | Tra cứu tài liệu chính sách nội bộ | không |
| papers | Tìm bài nghiên cứu trên arXiv | không |
| paper_text | Trích văn bản từ một bài arXiv cụ thể | không |

## A3. Câu hỏi mẫu để thử

> 3–5 câu hỏi/yêu cầu mẫu để team khác tự thử agent ngay.

1. Tìm tin AI hôm nay trên web và các bài đăng mới nhất về AI agents trên X.
2. Tóm tắt 5 bài đăng mới nhất của Sam Altman.
3. Kiểm tra danh sách nguồn này có thiếu URL hoặc bị trùng không: `[{"title":"Study A","url":"https://example.com/a"},{"title":"Study A copy","url":"https://example.com/a/"}]`
4. Tìm paper arXiv về đánh giá AI agents.
5. Gửi bản tin này lên Telegram: agent cần hiển thị nội dung/đích và chờ xác nhận trước khi gửi.

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Gemini free tier hết quota theo ngày, nên baseline v0 và run v1 bằng Gemini đều không đầy đủ. Đã khôi phục prompt/tools gốc từ Git và chạy v0 bằng cùng Groq model `openai/gpt-oss-20b` như v1–v3. Groq v0 có 1 provider error (R13), nên so sánh xu hướng trên 19 case đo được; v1–v3 không có provider errors.

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | Chạy baseline trước khi thay đổi prompt/tool | Gemini incomplete | Gemini: 7/20 measured; 13 provider errors | `runs/v0_B_base_gemini_20261110T102449278860.json` |
| v0 (Groq) | Original prompt + tools recovered from Git | Baseline cùng model với v1–v3 | — | 10/19 measured passed (52.63%); 1 provider error | `runs/v0-groq-gpt-oss-20b_B_base_groq_20261110T125503539408.json` |
| v1 (Gemini) | `system_prompt.md` + `tools.yaml` | Nêu rõ routing, clarification, scope và xác nhận | v0 Gemini incomplete | 1/20 measured; 19 provider errors | `runs/v1_B_base_gemini_20261110T113348158525.json` |
| v1 (Groq) | v1 prompt + tools snapshot | So sánh v1–v3 trên cùng model | — | accuracy 0.85; routing 0.95; arguments 0.85; multiturn 1.00 | `runs/v1-groq-gpt-oss-20b_B_base_groq_20261110T124151706716.json` |
| v2 (Groq) | `artifacts/versions/v2/system_prompt.md` | Thứ tự quyết định scope → thông tin bắt buộc → mọi nguồn yêu cầu → tool; xác nhận gửi ở lượt sau | v1: accuracy 0.85 | accuracy 0.85; routing 0.95; arguments 0.85; multiturn 1.00 | `runs/v2-groq-gpt-oss-20b_B_base_groq_20261110T122757353859.json` |
| v3 (Groq) | `artifacts/versions/v3/tools.yaml` | Rút gọn/phân biệt descriptions, query gọn, xác nhận send multi-turn | v2: accuracy 0.85 | accuracy 0.80; routing 0.95; arguments 0.80; multiturn 1.00 | `runs/v3-groq-gpt-oss-20b_B_base_groq_20261110T123632221087.json` |

Artifacts v1–v3 được snapshot dưới `artifacts/versions/` để có thể chạy lại với đúng prompt/tool hash. Bản hiện hành trong `artifacts/system_prompt.md` và `artifacts/tools.yaml` tương ứng với prompt v2 + tool declarations v3.

So sánh trên cùng 19 case không lỗi provider: v0 Groq đạt 10/19 (52.6%), v1 và v2 đạt 16/19 (84.2%), v3 đạt 15/19 (78.9%). Như vậy v1/v2 cải thiện so với v0 trên cùng model; v3 giảm nhẹ so với v1/v2. v0 R13 lỗi provider nên bị loại khỏi phép so sánh common-case. Trong tất cả eval runs, tool `send` bị harness chặn thực thi để tránh tác dụng phụ.

## B2. Failure Analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R03 (v1/v2/v3 Groq) | wrong_arg_value | `lookup(query="AI news today", topic=news, timeframe=day)` | Model thêm từ “news today” vào query; xảy ra cả ba version | Tiếp tục yêu cầu query chỉ gồm chủ đề cốt lõi; cân nhắc sửa eval nếu chấp nhận biến thể query |
| R01 (v0 Groq) | wrong_arg_value | `timeline(screenname=samaltman, limit=1)` | Dùng tên tài khoản thay vì handle `sama` | Thêm quy tắc map tên người sang handle trong v1 |
| R10/R11 (v0 Groq) | missing_info | Tự gọi `timeline` với `SamAltman`; tự chọn URL BBC | Starter prompt khuyến khích đoán thay vì hỏi | Dùng `clarify` khi thiếu tài khoản hoặc URL |
| R12/R14 (v0 Groq) | wrong_boundary / out_of_scope | Tự gọi tool không liên quan thay vì hỏi xác nhận/không gọi tool | Thiếu ranh giới an toàn và scope trong starter | Bổ sung rule xác nhận nhiều lượt, giới hạn scope; eval chặn `send` execution |
| R10 (v1/v3 Groq) | missing_info | Gọi `clarify` nhưng `response_type=choice` thay vì `text` | Hỏi đúng để làm rõ nhưng enum không khớp expected | Làm rõ trong prompt rằng thiếu handle cần câu hỏi dạng text |
| R12 (v2/v3 Groq) | wrong_boundary | Gọi `clarify(response_type=text)` để xin draft; expected `yes_no` | Model không chọn yes/no cho request gửi thiếu nội dung; hỏi nội dung trước vẫn giữ an toàn | Cải thiện quy trình: xin draft, nêu đích và nội dung, rồi mới hỏi xác nhận rõ |
| R13 (v1/v2/v3 Groq) | wrong_tool | Chỉ gọi `lookup`, bỏ `social_search` | Model bỏ sót nguồn X trong yêu cầu hai nguồn | Củng cố rule gọi cả hai tool cho web + X |

Ở v1/v2/v3 Groq, cả 20 case đều được đo và không có provider errors. Ba phiên bản có điểm tổng lần lượt 17/20, 17/20, 16/20; việc rút ngắn descriptions ở v3 chưa cải thiện kết quả.

## B3. Team Eval Cases

List the 10 cases added to `data/eval_group.json` (5 single turn + 5 multi turn).

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01 | Chủ đề X | `social_search` Latest | PASS |
| G02 | Thiếu tài khoản | `clarify` | PASS |
| G03 | Thiếu/trùng citation | `source_audit` | PASS |
| G04 | Khám phá arXiv | `papers` | PASS |
| G05 | Hỏi khả năng agent | Không gọi tool | PASS |
| G06 | Giữ timeframe qua nhiều lượt | `lookup(news, day)` | PASS |
| G07 | Làm rõ handle và số lượng | `timeline(sundarpichai, 2)` | PASS |
| G08 | Đổi nguồn X sang web | `lookup(news, week)` | PASS |
| G09 | Bổ sung URL sau khi hỏi lại | `fetch` đúng URL | PASS |
| G10 | Người dùng từ chối gửi | Không gọi `send` | PASS |

v3/Groq run: `runs/v3-groq-gpt-oss-20b_B_group_groq_20261110T124713169916.json` — 10/10 PASS; accuracy/routing/arguments/multiturn đều 1.00, không provider error.

## B4. Live Chat Evidence

Use `transcripts/*.transcript.json`.

Chưa có transcript live; cần chạy `chat.py` sau khi provider quota khả dụng.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | `tests/test_tools_todo.py` | Mock test xác nhận request chỉ gửi khi `confirmed=True` | Chưa thử gửi thật; phải xác nhận nội dung và đích riêng |
| arXiv/company policy | tools hiện có | Chưa chạy live | Paper arXiv không mặc định peer-reviewed; policy là nguồn nội bộ tĩnh |
| UI | `app.py` | Streamlit trả HTTP 200 ở local smoke test | Chưa deploy public; provider/API key phải cấu hình local |
| Tool unit tests (`tests/`) | `pytest -q`: 88 passed, 0 skipped | 19 test case cho tool trong `test_tools_todo.py` | Không phát hiện bug mới trong tool có sẵn; mọi HTTP đều mock |

Ví dụ unit test mà eval không thay thế được: test Firecrawl kiểm tra summary bị cắt đúng 4.000 ký tự; eval chỉ chấm tool routing/arguments.

## B6. Reflection

- `system_prompt.md`: quy tắc routing, hỏi lại khi thiếu dữ liệu, giữ ngữ cảnh/correction và xác nhận trước hành động.
- `tools.yaml`: mô tả rõ khác biệt giữa timeline/search/web/fetch, convention arguments và ranh giới `send`.
- Cần manual review: chất lượng và độ liên quan của nội dung trả lời; eval định lượng không thể xác nhận câu trả lời có hữu ích hay nguồn có thật sự hỗ trợ kết luận không.
- Tiếp theo: chạy lại v0–v3 và 10 group cases bằng provider có quota ổn định, sau đó lưu transcript live và deploy UI.

## B7. Small Local Model Challenge (bonus)

Only fill if your team did the local model challenge.

`nemotron-3-super:cloud` was installed as an Ollama Cloud model, not an offline
local model. Its preflight returned HTTP 402 because Ollama Cloud usage credits
were unavailable, so no local-model run or B7 metrics were produced.

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v3 | (cloud) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v4-local |  |  |  |  |  |  |  |
| v5-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
