# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Huy Hoàng
- **MSSV:** 2A202602738
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/Hoang-H-Nguyen/K4-L3B-Day13-NguyenHuyHoang-2A202602738-Monitoring-LLMOps
- **Commit SHA cuối:** a0cd51eddf07fefb7c5fa715c15311412e7c5866
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602738`

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback-before.png`, `evidence/10-prompt-rollback-after.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối đã kiểm tra | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; 21 records; 20 thiếu trường bắt buộc; 20 thiếu context; 0 correlation ID hợp lệ | 100/100; 13 records; 7 correlation ID; 0 thiếu trường/context | Không phát hiện PII thô |
| `validate_dashboard.py` | 6/6 panel trong dashboard contract | 6/6 panel; dashboard runtime đủ sáu panel | Evidence 03 và 11 |
| `pytest` | 22 passed trong 1.57s | 28 passed trong 0.96s | Bao gồm test logging, tracing và dashboard runtime |
| Số traces hợp lệ | Chưa xác nhận ở baseline | Ít nhất 10 traces trong project cá nhân | Evidence 06; trace có root/retrieval/generation |
| Số PII leak | 0 theo validator baseline | 0 | Test thêm email, điện thoại VN, CCCD và thẻ giả |
| Latency P95 / TTFT P95 | Baseline ban đầu thay đổi theo lần chạy | Incident mới nhất: 3868 / 50 ms | 5/5 request incident vượt 2000 ms |
| Retrieval success rate | 100% ở workload thành công | 100% trong incident `rag_slow` | Retrieval thành công nhưng chậm |

Baseline được ghi trước khi sửa CP1: 10/10 response HTTP 200 nhưng correlation ID là `MISSING`, validator log đạt 30/100. Sau khi sửa, log cũ được chuyển ra ngoài repo trước khi đo lại. Kiểm tra cuối chạy trên worktree hiện tại: `pytest` 28 passed, log validator 100/100 và dashboard validator 6/6.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ bằng `clear_contextvars()`, giữ header hợp lệ dạng `req-<8-hex>` hoặc tạo ID mới từ UUID, bind ID vào structlog và `request.state`, truyền ID vào agent/trace, JSON response và header `x-request-id`. Header `x-response-time-ms` ghi thời gian xử lý; context được dọn trong `finally`.
- **Các metadata được ghi vào structured log:** `ts`, `level`, `service`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`; response còn có latency, TTFT, token, cost, quality, `trace_id`, tool name và tool success.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` duyệt chuỗi trong dict/list lồng nhau và chạy trước file writer lẫn JSON renderer. Pattern che email, điện thoại Việt Nam, CCCD và thẻ thanh toán. User ID được băm SHA-256 rút gọn; trace chỉ lưu preview đã scrub, không capture raw input/output.
- **Cách kiểm chứng kết quả:** Evidence 04 cho thấy structured JSON đầy đủ context; evidence 05 dùng dữ liệu kiểm thử giả và cho thấy bốn dấu `[REDACTED_*]`; evidence 02 xác nhận 0 PII leak. Test concurrent request xác nhận ID/context không bị lẫn giữa request.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Evidence 06 hiển thị tên project `day13-k4-l3b-2A202602738` và danh sách hơn 10 trace. Project ID `cmuniwaey048gad0cr0xfzzy1` trong API trùng project của trace; correlation ID trong trace khớp structured log.
- **Cấu trúc root/retrieval/generation observations:** `lab-agent-run` loại agent là root; `retrieval` loại retriever và `generation` loại generation là hai child. Generation ghi model, usage input/output, cost và prompt managed; input/output chỉ dùng preview đã scrub.
- **Cách nối trace với log:** `response_sent.trace_id` nối trực tiếp với `traceId`; metadata root và child mang cùng `correlation_id`. Evidence 07 cho thấy cây observation; evidence 08 cho thấy metadata, usage và cost.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** version 1, labels `baseline` và `production` sau rollback.
- **Version/label candidate:** version 2, labels `candidate` và `latest`; trong bước promote, `production` tạm thời trỏ vào version 2.
- **Trace ID của mỗi version:** version 2 trước rollback: `ec45e6531c5a50c741c52a9cd0ef6dbb` (`prompt_version=2`, `prompt_label=production`); version 1 sau rollback: `1b72a1978f60c83cb8773bcfa69838a4` (`prompt_version=1`, `prompt_label=production`).
- **Cách promote và rollback `production`:** Chuyển label `production` sang v2, restart API và chạy workload; trace đầu xác nhận app lấy v2 từ Langfuse. Sau đó chuyển `production` về v1, restart và chạy lại; trace thứ hai xác nhận v1. Evidence 09 cho thấy hai version; evidence 10-before/after chứng minh hai trace trước và sau rollback.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard local chạy bằng `python scripts/dashboard.py` tại `http://127.0.0.1:8501`, đọc trực tiếp `data/logs.jsonl`. Sáu panel gồm latency P50/P95/P99 và TTFT P95, traffic, error rate/retrieval success, cost, input/output tokens và quality. Mặc định 60 phút, refresh 30 giây, có đơn vị, time range và threshold từ `config/dashboard.yaml`. Evidence 11 là dashboard runtime; evidence 03 là contract validator.
- **SLO và lý do chọn:** SLO chính là 99.5% request trong cửa sổ 28 ngày phải có `response_sent` và `latency_ms <= 3000`. Ngưỡng 3000 ms cân bằng trải nghiệm chờ với baseline của lab, đồng thời incident `rag_slow` mới nhất đạt P95 3868 ms nên bị phát hiện. Guardrail bổ sung: error rate tối đa 2%, daily cost tối đa 2.5 USD, quality trung bình tối thiểu 0.75 và retrieval success tối thiểu 90%.
- **Cách tính error budget:** Target 99.5% nghĩa là error budget 0.5%. Với 10,000 request trong 28 ngày, tối đa 50 request được phép lỗi hoặc chậm hơn 3000 ms; từ request thứ 51 là vượt budget.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` cảnh báo khi P95 > 3000 ms trong 5 phút; `HighErrorRate` critical khi error rate > 2% trong 5 phút; `LowRetrievalSuccess` critical khi retrieval success < 90% trong 5 phút. Cả ba gửi Slack `#k4-l3b-alerts`, owner `student-2A202602738`, cấu hình tại `config/alert_rules.yaml` và hướng dẫn điều tra/mitigation tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`, cohort K4, feature `monitoring`. File chính thức được đặt tại `config/challenge.json`, được Git ignore; workload chạy bằng `--challenge --concurrency 5` mà không sửa input/seed.
- **Khoảng thời gian điều tra:** từ `2026-09-30T07:40:33.917698Z` đến `2026-09-30T07:40:44.540677Z` (khoảng 14:40:33–14:40:44, UTC+7).
- **Triệu chứng từ metrics:** workload incident có 5 request; P95 của `response_sent.latency_ms` là `3868 ms`, vượt ngưỡng challenge 2000 ms và ngưỡng dashboard 3000 ms. Cả 5/5 request đều vượt 2000 ms. Request được chọn có TTFT 50 ms. Evidence 12 khoanh vùng metric và thời gian.
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-30T07:40:33.917698Z`, `correlation_id=req-d0b7ba76`, `trace_id=c67fd73cae3eb5a29b0d4682199404b6`, `latency_ms=3868`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`. Evidence 13 là log của request này.
- **Trace ID và span gây ảnh hưởng:** trace `c67fd73cae3eb5a29b0d4682199404b6`; root `lab-agent-run` (`d905af3d0c46721b`) dài khoảng 3869 ms; child `retrieval` (`57f33222f6586994`) dài 2500 ms; child `generation` (`a993514d2990f1e6`) dài 151 ms. Metadata có cùng `correlation_id=req-d0b7ba76`. Evidence 14 là trace tương ứng.
- **Root cause:** Incident `rag_slow` thêm khoảng 2.5 giây chờ trong `app/mock_rag.py:retrieve`, khớp retrieval span 2500 ms. Generation chỉ mất 151 ms và TTFT là 50 ms. `tool_success=true` cho thấy retrieval không lỗi mà chỉ bị chậm.
- **Fix action:** Đã chạy `python scripts/inject_incident.py --disable`; `/health` sau đó trả `ok=true`, `tracing_enabled=true` và cả `rag_slow`, `tool_fail`, `cost_spike` đều `false`.
- **Preventive measure:** Theo dõi latency P95 theo feature, cảnh báo khi vượt 3000 ms liên tục 5 phút; từ correlation ID mở retrieval span; đặt timeout/fallback cho retrieval và chạy lại workload để xác nhận recovery. Alert chưa được tuyên bố firing vì workload lab không kéo dài đủ 5 phút.

Luồng evidence: ảnh 12 xác định metric và khoảng thời gian → ảnh 13 chọn request `req-d0b7ba76` → ảnh 14 dùng cùng trace ID để xác định retrieval là span chậm. [Mở trace incident trên Langfuse](https://us.cloud.langfuse.com/project/cmuniwaey048gad0cr0xfzzy1/traces/c67fd73cae3eb5a29b0d4682199404b6).

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt correlation ID ở middleware và bind metadata request trước `request_received`, vì cách này bảo đảm mọi log và trace downstream dùng cùng context, đồng thời middleware có thể trả đúng ID trong response header.
- **Một lỗi/blocker đã gặp:** Ban đầu log trả `MISSING`, thiếu enrichment và Langfuse không tìm thấy prompt `day13-chat:production`; trace export cũng từng timeout.
- **Cách tìm nguyên nhân và xử lý:** Lần theo request từ middleware đến logger/agent, bật scrubber đúng thứ tự, bổ sung child observations và tạo managed prompt v1/v2 trên đúng project. Sau đó kiểm tra bằng validator, test concurrent request, trace metadata và hai lượt promote/rollback.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cho biết loại triệu chứng và thời gian; log chọn một request cụ thể bằng correlation ID; trace của request đó phân rã thời gian theo retrieval/generation để xác định root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version giúp biết chính xác cấu hình tạo output và rollback mà không sửa code; token/cost phát hiện chi phí bất thường; SLO/error budget biến chất lượng thành mục tiêu đo được; alert và runbook giúp phản ứng nhất quán.
- **Điều quan trọng nhất đã học:** Observability hữu ích khi metric, structured log và trace chia sẻ ID và metadata an toàn; một biểu đồ hoặc một trace riêng lẻ chưa đủ để kết luận nguyên nhân.
- **Hạn chế hoặc phần chưa hoàn thành:** Alert được cấu hình và có runbook nhưng workload ngắn nên chưa chứng minh alert firing đủ 5 phút. Số mẫu challenge nhỏ, phù hợp lab nhưng chưa đại diện production. Commit SHA cuối và bước nộp LMS chỉ hoàn tất sau khi chốt commit.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối — chưa thể xác nhận khi worktree còn thay đổi.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README; kiểm tra cuối đạt 28 tests, log 100/100, dashboard 6/6.
- [x] Không có secret, API key, PII thật hoặc evidence của người khác/lớp khác; dữ liệu PII trong evidence 05 là dữ liệu giả để test redaction.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs — URL đã điền, chưa thể xác minh thao tác nộp và SHA cuối.
