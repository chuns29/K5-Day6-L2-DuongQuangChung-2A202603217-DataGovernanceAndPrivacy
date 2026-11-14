# Báo cáo Day 6 · G03 · T06 Dataset Semantic Integrity & Provenance Gate

- Học viên thực hiện cá nhân: Dương Quang Chung.
- Repo: https://github.com/chuns29/K5-Day6-L2-DuongQuangChung-2A202603217-DataGovernanceAndPrivacy
- HEAD của lần chạy: b0ce8bf. Các thay đổi của bài làm đang ở working tree tại thời điểm lập báo cáo.
- Mốc demo và nộp cuối: sẽ gắn tag khi chốt từng bản.

## 1. Bài toán

Mỗi bản ứng viên chứa danh sách ảnh, nhãn vật thể, bảng mã lớp và metadata. Một file JSON đọc được vẫn có thể đổi ý nghĩa mã lớp, dịch khung bao hoặc làm mất frame. Những lỗi này có thể đưa nhãn sai vào tập huấn luyện. Gate ra một quyết định cho từng bản ứng viên trước khi phát hành. PASS nghĩa là qua các kiểm tra đã cấu hình. HOLD đưa bản có dấu hiệu lỗi vào diện xem xét. Sau khi xem bằng chứng, người duyệt có thể chọn REWORK để yêu cầu sửa.

## 2. Dữ liệu và nguồn gốc

Dữ liệu mô phỏng từ fixtures/t06_release_gate, giấy phép trong manifest là CC0-1.0 (synthetic, generated for AI20K Day06). Có 20 ứng viên, chia 10 dev và 10 eval theo releases.csv. Bản cha là releases/v1.0. Nhãn COCO dùng category_id và bbox dạng [x, y, w, h]. PoC xác minh SHA-256 của manifest đầu vào và đối chiếu parent_version, parent_sha256 do từng ứng viên khai. Cả hai lượt chạy dùng seed 42 và chạy offline bằng Python 3.12.16 trên Windows.

## 3. Cách làm

Baseline thử đọc JSON, kiểm cấu trúc và kiểm file ảnh có tồn tại. PoC bổ sung kiểm tra ID trùng, frame thiếu, phiên bản và ý nghĩa mã lớp, khung bao vượt biên và chênh lệch tọa độ với bản cha. Khung ghép theo ID nhãn và ID ảnh, ngưỡng mặc định 5 px. Không có model hoặc weights. So sánh theo ID giúp giải thích bằng chứng nhưng giả định ID được giữ ổn định giữa các bản. Một chỉnh sửa nhãn có chủ đích hoặc dịch khung lớn hợp lệ vẫn có thể cần người duyệt xác nhận.

Luồng chạy: manifest và ứng viên → kiểm tra → xếp thứ tự theo số nhóm lỗi → review tùy chọn → quyết định và báo cáo. PoC xuất hàng chờ với B=20. Bảng dưới dùng quyết định tự động trước review, với ngân sách can thiệp bằng 0 cho cả hai lượt.

## 4. So sánh baseline và PoC

| Tập | N | Baseline PASS | Baseline giữ | PoC PASS | PoC giữ |
|---|---:|---:|---:|---:|---:|
| Toàn bộ | 20 | 20 | 0 | 10 | 10 |
| dev | 10 | 10 | 0 | 3 | 7 |
| eval | 10 | 10 | 0 | 7 | 3 |

Runtime toàn lượt trên máy chạy là 0.3986 giây cho baseline và 1.0574 giây cho PoC. Thời gian PoC gồm xác minh manifest và xuất trang review. Đây là một lần đo.

Số bản bị giữ mô tả hành vi của chương trình. Điểm Silent-defect Detection F1, recall, tỷ lệ chặn nhầm và độ chính xác nguyên nhân đang chờ gt_releases.csv của giảng viên. Chấm trên split eval theo metric_contract.md. Không sử dụng các quyết định của PoC làm nhãn đáp án.

## 5. Đối chiếu thủ công trên dev

- r07 có JSON hợp lệ. So bảng categories với v1.0 cho thấy mã 1 đổi từ car sang pedestrian, mã 2 đổi từ pedestrian sang car. Baseline PASS, PoC HOLD với class_swap.
- r02 thiếu 9 ID ảnh có trong danh sách images của v1.0. Baseline PASS vì các file được tham chiếu vẫn tồn tại. PoC HOLD với dropped_frames. Các ID thiếu được lưu trong rework_report.json.

## 6. Review và kiểm thử

Ở ca demo bước 6, đã đối chiếu r07 và ghi edit thành REWORK trong review_queue_reviewed.csv. Chạy lại PoC xác nhận HOLD → REWORK, với lý do trong audit_log.jsonl. Chủ trách nhiệm release trong cấu hình G03 là Dương Quang Chung. Hai test T06 kiểm tra một bản hợp lệ và ca đảo mã có ghi lại override.

## 7. Chạy lại trên Windows

~~~powershell
.\.venv\Scripts\python.exe -m src.main --track t06 --pipeline src.examples.t06_baseline --output out/baseline_t06 --run-name baseline --offline --seed 42
.\.venv\Scripts\python.exe -m src.main --track t06 --output out/poc --run-name poc --offline --seed 42
.\.venv\Scripts\python.exe -m pytest -q
# Khi có đáp án chính thức
.\.venv\Scripts\python.exe -m src.evaluate --track t06 --pred out/baseline_t06/release_decisions.csv --run-name baseline --out reports/metrics_baseline.json
.\.venv\Scripts\python.exe -m src.evaluate --track t06 --pred out/poc/release_decisions.csv --run-name poc --out reports/metrics_poc.json
.\.venv\Scripts\python.exe -m src.compare reports/metrics_baseline.json reports/metrics_poc.json --out reports/table1_baseline_vs_poc.md
~~~

Dùng thư mục PoC mới hoặc trống khi đo tự động để tránh áp lại một file review từ lượt demo.

## 8. Giới hạn và đóng góp

Chưa đo F1 hoặc khoảng tin cậy trên eval. Có thể báo bootstrap theo release sau khi có GT và nêu rõ độ bất định của tập nhỏ. Kiểm thử chuyển đổi qua lại COCO–YOLO và rollback vẫn thuộc mốc hoàn thiện. Thí nghiệm sử dụng dữ liệu mô phỏng và chỉ kiểm tra chất lượng kỹ thuật. Với dữ liệu thật, quyền sử dụng và phát hành cần được người phụ trách xác nhận.

G03 thực hiện cá nhân. Chi tiết vai trò và file nằm trong team_contributions.csv. Commit triển khai và kiểm thử là `965ba5535ea1`.

## 9. Tài liệu trong repo

- docs/tracks/T06.md mô tả dạng lỗi, baseline và yêu cầu đánh giá.
- src/metrics/tracks.py chứa evaluator, phép ghép release_id và định nghĩa các metric.
- src/common/review.py quy định định dạng phiếu review và cách ghi override.
