# Metric contract · G03 · T06

| Mục | Khai báo |
|---|---|
| Track | T06 · Dataset Semantic Integrity & Provenance Gate |
| Primary metric | Silent-defect Detection F1. Cao hơn tốt hơn. |
| Đơn vị và cách ghép | Một candidate release. Ghép prediction với ground truth theo release_id. |
| Công thức | 2TP / (2TP + FP + FN). TP là release lỗi bị giữ, FP là release sạch bị giữ, FN là release lỗi được cho qua. |
| Quyết định | HOLD và REWORK được tính là giữ. PASS được tính là cho qua. |
| Candidate pool | 20 candidate trong fixtures/t06_release_gate/releases.csv, gồm 10 dev và 10 eval. |
| Eval split | Dùng split eval để chấm. Tập dev dùng để phát triển và minh họa lỗi. Giữ nguyên pool và ngưỡng khi chấm. |
| Review budget | B=20 cho review queue của PoC. So sánh baseline và PoC tự động với 0 override ở cả hai lượt. Các quyết định review demo được ghi trong audit log riêng của lượt review. |
| Seed | 42 |
| Threshold policy | Ngưỡng mặc định 5 px cho chênh lệch lớn nhất giữa các thành phần bbox của cùng annotation trên cùng image ID. Giữ giá trị đã dùng ở bước 7 cho lần chấm chính thức. |
| Metric phụ | Defect recall = TP/(TP+FN). False-block rate = FP/(FP+TN). Root-cause accuracy tính trên các release lỗi đã bị giữ và có dự đoán root_cause. |
| Slices | Dev và eval cho số quyết định. Báo tỷ lệ giữ theo corruption_type khi có GT. |
| Độ bất định | Khi có GT, có thể báo khoảng bootstrap 95% bằng cách lấy mẫu lại theo release và ghi kèm N. |
| Ngày giờ và người phụ trách | Cập nhật 2026-11-14 17:51 +07:00 giờ Việt Nam. Dương Quang Chung (G03). |
| Trạng thái | Đã khai báo quy trình. F1 và các metric cần nhãn đang chờ gt_releases.csv chính thức từ giảng viên. |

Nếu baseline F1 bằng 0, ghi giá trị gốc và chênh lệch tuyệt đối, tránh tính phần trăm cải thiện.
