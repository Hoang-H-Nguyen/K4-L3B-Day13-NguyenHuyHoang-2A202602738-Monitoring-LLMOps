# Dựng và kiểm tra dashboard

[`../config/dashboard.yaml`](../config/dashboard.yaml) là contract chấm điểm, không phụ thuộc việc bạn dựng dashboard trong Langfuse hay một công cụ local. File này quy định đúng nguồn dữ liệu, phép tổng hợp, đơn vị và threshold cho sáu panel.

Trường `query` trong YAML là pseudocode mô tả phép tính, không phải câu lệnh để copy nguyên vào mọi công cụ. Bạn chuyển cùng logic đó sang cú pháp của công cụ đã chọn.

Lab không bắt buộc một công cụ dashboard cụ thể. Bạn có thể dùng Streamlit, notebook, Grafana, script local tạo biểu đồ hoặc công cụ tương đương. Điều quan trọng khi chấm là dashboard runtime có dữ liệu thật từ `data/logs.jsonl`, đủ sáu panel, đọc được time range/đơn vị/threshold và khớp logic trong `config/dashboard.yaml`.

## Dashboard local đã có trong repo

Mở terminal tại gốc repo, activate venv và chạy:

```bash
source .venv/bin/activate
python scripts/dashboard.py
```

Mở **http://127.0.0.1:8501** trong trình duyệt. Không cần cài Streamlit hoặc thư viện mới. Server chỉ lắng nghe localhost và đọc `data/logs.jsonl`; không cần API đang chạy để xem log cũ.

- Mặc định: 60 phút gần nhất, tự cập nhật 30 giây theo contract.
- Chọn **Lịch sử — kết thúc tại log mới nhất** nếu log đã cũ và cửa sổ live không có dữ liệu. Màn hình ghi rõ chế độ lịch sử và thời gian đang xem.
- Chọn **Lịch sử — chọn thời điểm kết thúc** để xem một khoảng cụ thể; thời điểm nhập theo múi giờ trình duyệt.
- Nút **Tạm dừng để chụp** cố định số liệu đang hiển thị. Nút tiếp tục bật lại cập nhật tự động.
- Mọi threshold lấy từ `config/dashboard.yaml`. Traffic so sánh trung bình request/phút trong cửa sổ; cost so sánh tổng cửa sổ; token so sánh riêng tổng input và output.
- Error rate = số `request_failed` / số `request_received`. Retrieval success dùng mọi log API có `tool_name=retrieval` và `tool_success` boolean, gồm cả response thành công; không chỉ đếm event lỗi.
- P50/P95/P99 dùng nearest-rank. Không có mẫu thì hiển thị dấu gạch, không giả định success 100%.

Để chụp ảnh 11: mở rộng cửa sổ browser, chọn khoảng có dữ liệu, nhấn tạm dừng, giữ tiêu đề và thanh thời gian cùng đủ sáu panel trong ảnh. Có thể giảm zoom browser hoặc chụp hai ảnh nếu màn hình nhỏ. Lưu `submission/evidence/11-dashboard-overview.png`, rồi dẫn trong report. Không dùng ảnh validator thay ảnh runtime.

## Mapping dữ liệu

| Panel | Event/field | Phép tổng hợp |
|---|---|---|
| Latency | `response_sent.latency_ms/ttft_ms` | latency P50/P95/P99 và TTFT P95 |
| Traffic | `request_received` | count, request/phút |
| Errors | `request_received`, `request_failed`, `error_type`, `tool_success` | error rate, breakdown và retrieval success |
| Cost | `response_sent.cost_usd` | tổng theo phút và toàn cửa sổ |
| Tokens | `response_sent.tokens_in/tokens_out` | tổng theo từng field |
| Quality | `response_sent.quality_score` | mean |

Giữ time range mặc định 60 phút, refresh 30 giây và hiển thị threshold/SLO line. Giá trị chính xác nằm trong `config/dashboard.yaml`; không tự đổi contract chỉ để ảnh dashboard đẹp hơn.

## Cách dựng

1. Hoàn thiện logging/PII và chạy API.
2. Chạy `python scripts/load_test.py --concurrency 5` để tạo baseline.
3. Dùng `data/logs.jsonl` làm nguồn chuẩn để tạo đúng sáu panel bằng Streamlit, notebook, Grafana hoặc công cụ tương đương. Langfuse vẫn là nơi mở trace/prompt version để điều tra sâu.
4. Đặt tên panel, đơn vị và threshold giống contract.
5. Chạy validator:

```bash
python scripts/validate_dashboard.py
```

Validator kiểm tra cấu trúc contract; nó không thể chứng minh biểu đồ trong ảnh dùng đúng dữ liệu. Evidence runtime vẫn bắt buộc.

## Cách kiểm tra runtime

1. Lưu ảnh baseline và giá trị P95/error/cost hiện tại.
2. Bật một incident practice, ví dụ `python scripts/inject_incident.py --scenario <practice_scenario>`.
3. Chạy lại load test với cùng input và concurrency.
4. Xác nhận panel liên quan thay đổi theo đúng hướng theo loại practice scenario đã chọn.
5. Lọc log chậm, lấy correlation ID rồi mở trace có cùng ID.
6. Tắt incident bằng `python scripts/inject_incident.py --scenario <practice_scenario> --disable`.

Ảnh dashboard phải nhìn được tên panel, time range, đơn vị và threshold. Báo cáo phải dẫn lại trace ID hoặc log line dùng để giải thích thay đổi.
