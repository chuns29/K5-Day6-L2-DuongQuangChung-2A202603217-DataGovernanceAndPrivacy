# Metric contract · G03 · T06

| Mục | Khai báo |
|---|---|
| Primary | Silent-defect Detection F1, cao hơn tốt hơn |
| Đơn vị ghép | Một release, ghép theo release_id |
| Công thức | 2TP / (2TP + FP + FN). TP là release lỗi bị giữ. FP là release sạch bị giữ. FN là release lỗi được cho qua. |
| Quyết định giữ | HOLD hoặc REWORK. PASS được tính là cho qua. |
| Pool và split | 20 ứng viên trong releases.csv. Chấm chính thức trên 10 bản eval. |
| Seed và budget | Seed 42. Hàng chờ PoC tối đa 20. So sánh quyết định tự động với 0 can thiệp ở cả hai lượt. |
| Ngưỡng đang dùng | 5 px cho chênh lệch lớn nhất của một thành phần bbox. Giữ ngưỡng hiện tại cho lần chấm chính thức. |
| Metric phụ | Defect recall, false-block rate, root-cause accuracy. |
| Slices | dev và eval cho bảng quyết định. Phân loại lỗi theo corruption_type khi có GT. |
| Độ bất định | Tập eval nhỏ. Có thể báo bootstrap theo release khi có GT. |
| Trạng thái | Ghi lại cấu hình đã dùng cho bước 7. Chưa có điểm eval chính thức. |
