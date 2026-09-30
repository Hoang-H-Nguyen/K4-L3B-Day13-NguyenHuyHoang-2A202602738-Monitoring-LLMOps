# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1: HighLatencyP95

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`; SLO request tốt khi latency không quá 3000 ms.
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` liên tục 5 phút.
- Ảnh hưởng tới người dùng: thời gian chờ câu trả lời tăng, dù request có thể vẫn thành công.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel latency, xác nhận P95/P99, TTFT và khoảng thời gian bất thường.
  2. Lọc `response_sent` trong khoảng đó, chọn request có latency cao và lấy `correlation_id` cùng `trace_id`.
  3. Mở trace tương ứng, so sánh retrieval và generation để xác định span chậm.
- Mitigation tạm thời: tắt incident/config gây chậm nếu đang diễn tập; bật timeout/fallback retrieval hoặc giảm concurrency khi upstream quá tải; xác nhận P95 phục hồi.
- Owner: `student-2A202602738`

## Alert 2: HighErrorRate

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: error rate = `request_failed / request_received`; guardrail tối đa 2%.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút.
- Ảnh hưởng tới người dùng: request không trả được câu trả lời thành công.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel errors và xem breakdown theo `error_type`.
  2. Lấy `correlation_id` từ một `request_failed`, kiểm tra `tool_name`, `tool_success` và timestamp.
  3. Mở trace cùng ID để xác định observation lỗi và dependency liên quan.
- Mitigation tạm thời: tắt thay đổi/incident gây lỗi; chuyển sang fallback an toàn; kiểm tra lại error rate bằng cùng workload.
- Owner: `student-2A202602738`

## Alert 3: LowRetrievalSuccess

- Tên: `LowRetrievalSuccess`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ `tool_success=true` của retrieval; guardrail tối thiểu 90%.
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90` liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời thiếu context hoặc request lỗi do không lấy được tài liệu.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel errors/retrieval success và xác nhận tỷ lệ giảm.
  2. Lọc log `tool_name=retrieval` và `tool_success=false`, lấy correlation ID đại diện.
  3. Mở retrieval observation trong trace, kiểm tra status, latency và error message đã scrub.
- Mitigation tạm thời: bật fallback không dùng retrieval hoặc nguồn dự phòng, giảm tải vector store, sau đó chạy lại workload để xác nhận tỷ lệ trên 90%.
- Owner: `student-2A202602738`
