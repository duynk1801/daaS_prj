# Kế Hoạch Phát Triển & Tích Hợp API Backend Cho Mobile DaaS v2

Tài liệu này vạch ra lộ trình phát triển chi tiết từng bước, kết hợp cập nhật Database (DB) và chỉnh sửa code dự án để các chức năng hoạt động đồng bộ với Mobile App.

Tất cả các tài liệu mô tả chi tiết chức năng và API được lưu trữ trong thư mục [.agent/doc/](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/).

---

## 📋 Mục Lục Tiến Trình (Click để xem tài liệu chi tiết)

| Bước thực hiện | Nhóm chức năng | Tài liệu chi tiết (API & DB Schema) | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Bước 1** | Đăng ký, Đăng nhập OTP, Đăng xuất, Đổi/Quên mật khẩu, Hồ sơ cá nhân | [auth-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/auth-doc.md)<br>[profile-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/profile-doc.md) | ⏳ Chờ triển khai |
| **Bước 2** | Ví điện tử, Nạp tiền (VNPay), Chuyển tiền nội bộ, Lịch sử giao dịch | [wallet-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/wallet-doc.md) | ⏳ Chờ triển khai |
| **Bước 3** | Bản đồ, Vẽ vùng bay, Tính diện tích (ha) & Waypoints, Kiểm tra vùng cấm bay | [booking-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/booking-doc.md) | ⏳ Chờ triển khai |
| **Bước 4** | Tính báo giá tạm tính, Đặt lịch bay, Xác nhận & Giữ tiền (Hold), Hủy lịch & Hoàn tiền | [booking-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/booking-doc.md)<br>[payment-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/payment-doc.md) | ⏳ Chờ triển khai |
| **Bước 5** | Theo dõi chuyến bay (Live Tracking WS), Tọa độ & telemetry thực tế, Lịch sử đường bay | [tracking-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/tracking-doc.md) | ⏳ Chờ triển khai |
| **Bước 6** | Báo cáo hoàn thành (Reports), Kết quả AI Summary (JSON), File tải về (PDF/OBJ/KMZ) | [reports-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/reports-doc.md) | ⏳ Chờ triển khai |
| **Bước 7** | Đọc/Đánh dấu Thông báo (Notifications), Tin tức công nghệ & chính sách, Dashboard | [notifications-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/notifications-doc.md)<br>[news-doc.md](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/news-doc.md) | ⏳ Chờ triển khai |

---

## 🛠️ Quy Trình Triển Khai Từng Bước (Cập nhật DB & Viết API)

### Bước 1: Tài Khoản & Hồ Sơ Cá Nhân (Features 1-7, 16)
1. **Migration DB**:
   - Tạo bảng `users` chứa thông tin cá nhân: `id` (UUID), `email` (Unique), `phone_number`, `full_name`, `password_hash`, `role`, `avatar_url`, `is_active`.
   - Tạo bảng `refresh_tokens` phục vụ cơ chế JWT Auth.
   - Tạo bảng `user_settings` (hoặc nhúng vào `users`) lưu: `language` (vi/en), `dark_mode` (bool), `enable_push` (bool).
2. **BE APIs**:
   - `POST /api/v1/auth/register` (Đăng ký tài khoản).
   - `POST /api/v1/auth/login` (Đăng nhập Email + OTP, trả về JWT Access Token + Refresh Token). *Lưu ý: OTP khi test local sẽ được ghi log trực tiếp ra console để tiện kiểm thử.*
   - `POST /api/v1/auth/logout` (Đăng xuất, xóa refresh token).
   - `POST /api/v1/auth/forgot-password` và `POST /api/v1/auth/reset-password` (Quên & Đặt lại mật khẩu).
   - `GET /api/v1/profile/me` & `PUT /api/v1/profile/me` (Xem và chỉnh sửa hồ sơ).
3. **Kết nối Mobile**:
   - Sử dụng Postman / Mobile App gọi API login, lấy token gắn vào header `Authorization: Bearer <token>` cho các API sau.
   - Test cập nhật thông tin cá nhân/avatar để hiển thị trực tiếp trên UI Mobile.

---

### Bước 2: Ví Điện Tử & Giao Dịch (Feature 14)
1. **Migration DB**:
   - Tạo bảng `wallets` lưu số dư: `id`, `user_id` (FK), `balance`, `currency`.
   - Tạo bảng `transactions` ghi nhật ký giao dịch: `id`, `wallet_id` (FK), `type` (DEPOSIT, PAYMENT, HOLD, RELEASE, REFUND, TRANSFER), `amount`, `reference_id` (ID của booking hoặc nạp tiền), `description`, `created_at`.
   - Tạo bảng `payment_methods` lưu thông tin thẻ liên kết (giả lập token).
2. **BE APIs**:
   - `GET /api/v1/wallet/balance` (Xem số dư).
   - `GET /api/v1/wallet/transactions` (Lịch sử giao dịch).
   - `POST /api/v1/wallet/topup` (Tạo URL thanh toán qua VNPay).
   - `POST /api/v1/wallet/transfer` (Chuyển tiền nội bộ giữa các ví).
3. **Kết nối Mobile**:
   - Mobile hiển thị số dư ví lên Dashboard và ví cá nhân.
   - Test nạp tiền: mở Webview VNPay trên Mobile, sau khi thanh toán thành công, hệ thống nhận webhook cập nhật số dư -> Mobile hiển thị đúng số dư mới.

---

### Bước 3: Bản Đồ & Vùng Bay (Feature 9.3)
1. **Migration DB**:
   - Cập nhật bảng `bookings`: Thêm trường `polygon_coordinates` (lưu tọa độ các điểm vẽ vùng dạng JSON), `area_ha` (diện tích ha), `pin_count` (số lượng marker ghim).
2. **BE APIs**:
   - `POST /api/v1/booking/calculate-area`: Nhận GeoJSON từ mobile, tính toán diện tích bằng công thức toán học thực tế (hệ tọa độ WGS84) và trả về số ha, số điểm ghim, ước tính thời gian bay cần thiết.
   - `POST /api/v1/booking/validate-zone`: Kiểm tra xem polygon vùng bay có nằm trong khu vực cấm bay (No-Fly Zone) hay không.
3. **Kết nối Mobile**:
   - Người dùng vẽ polygon trên Google Maps / Mapbox trên Mobile.
   - Mobile gửi danh sách tọa độ lên BE, BE tính toán diện tích và trả về hiển thị tức thì trên Mobile (VD: *Diện tích: 12.5 ha - Thời gian bay dự kiến: 45 phút*).

---

### Bước 4: Thanh Toán & Quản Lý Đặt Lịch (Features 10, 11)
1. **Migration DB**:
   - Tạo bảng `payments` để quản lý hóa đơn/giao dịch giữ tiền của booking.
2. **BE APIs**:
   - `POST /api/v1/booking/quote`: Nhận diện tích (ha) + gói AI, tính toán báo giá tạm tính (Basic price + AI package + Vận chuyển + VAT).
   - `POST /api/v1/bookings`: Tạo booking trạng thái `PENDING_PAYMENT`.
   - `POST /api/v1/bookings/{id}/confirm-hold`: Thực hiện trừ/giữ tiền (Hold) trên ví -> Chuyển trạng thái booking sang `CONFIRMED`.
   - `PATCH /api/v1/bookings/{id}/cancel`: Người dùng yêu cầu hủy lịch. Nếu hợp lệ, BE chuyển sang `CANCELLED`, giải phóng số tiền đang giữ (Release Hold) hoàn lại ví của người dùng.
3. **Kết nối Mobile**:
   - Mobile hiển thị màn hình hóa đơn chi tiết.
   - Nhấn "Thanh toán" -> Gọi API giữ tiền -> Thành công chuyển sang màn hình "Đặt lịch thành công".
   - Test tính năng "Hủy lịch bay" -> Ví cộng lại tiền ngay lập tức.

---

### Bước 5: Theo Dõi Chuyến Bay Trực Tiếp (Feature 12, 13)
1. **Migration DB**:
   - Tạo bảng `schedules`: `id`, `booking_id` (FK), `drone_id`, `pilot_id`, `mission_date`.
   - Tạo bảng `telemetry_logs`: Lưu tọa độ bay thực tế phục vụ vẽ lại đường bay: `id`, `booking_id` (FK), `latitude`, `longitude`, `altitude`, `speed`, `battery`, `timestamp`.
2. **BE APIs**:
   - WebSocket `/api/v1/tracking/{booking_id}/live`: Đẩy tọa độ trực tiếp của drone (được mô phỏng bay theo lộ trình polygon vẽ ở Bước 3), độ cao, tốc độ, dung lượng pin, tiến độ hoàn thành (%).
   - `GET /api/v1/tracking/{booking_id}/path`: Trả về mảng tọa độ GPS lịch sử của chuyến bay.
3. **Kết nối Mobile**:
   - Mở màn hình Live Tracking trên Mobile -> Kết nối WebSocket tới BE.
   - BE liên tục gửi telemetry (1s/lần) -> Mobile cập nhật vị trí drone di chuyển trên bản đồ và hiển thị kim tốc độ/độ cao tương ứng.

---

### Bước 6: Báo Cáo Kết Quả AI (Feature 15)
1. **Migration DB**:
   - Tạo bảng `reports` lưu kết quả: `id`, `booking_id` (FK), `ai_summary` (tóm tắt AI), `stats` (JSON chứa cặp Key-Value chỉ số báo cáo, ví dụ: *{"total_panels": 1240, "critical_faults": 15}*).
   - Tạo bảng `report_attachments` lưu liên kết tệp tin: `id`, `report_id` (FK), `file_name`, `file_type` (PDF, OBJ, KMZ, PNG...), `file_url`, `file_size`.
2. **BE APIs**:
   - `GET /api/v1/reports`: Danh sách báo cáo.
   - `GET /api/v1/reports/{id}`: Xem chi tiết báo cáo và tóm tắt AI.
   - `GET /api/v1/reports/download/{attachment_id}`: Sinh Signed URL tải tệp đính kèm (PDF báo cáo, ảnh nhiệt gốc, model 3D...) từ hệ thống lưu trữ (S3/MinIO).
3. **Kết nối Mobile**:
   - Người dùng click xem Báo cáo hoàn thành trên Mobile.
   - Mobile tải dữ liệu AI Summary, vẽ biểu đồ thống kê từ trường `stats` (JSON) và cung cấp nút tải báo cáo PDF / xem mô hình 3D.

---

### Bước 7: Thông Báo, Tin Tức & Dashboard (Features 8, 17, 18)
1. **Migration DB**:
   - Tạo bảng `notifications`: `id`, `user_id` (FK), `title`, `body`, `type` (payment, flight, report), `is_read`, `created_at`.
   - Tạo bảng `news`: `id`, `title`, `category`, `image_url`, `body` (mảng văn bản), `source`, `read_time`, `is_published`, `created_at`.
2. **BE APIs**:
   - `GET /api/v1/notifications` (Danh sách thông báo).
   - `PATCH /api/v1/notifications/{id}/read` (Đánh dấu đã đọc).
   - `GET /api/v1/analytics/dashboard` (API tổng hợp thông tin Dashboard: số dư ví, 3 lịch bay gần nhất, số thông báo chưa đọc).
   - `GET /api/v1/news` & `GET /api/v1/news/{id}` (Danh sách & Chi tiết tin tức).
3. **Kết nối Mobile**:
   - Hiển thị số lượng thông báo chưa đọc lên biểu tượng quả chuông ở màn hình chính.
   - Load tin tức và các lối tắt thao tác nhanh (lịch bay hôm nay & ngày mai) lên Dashboard.

---

## 🔒 Quy Tắc Cập Nhật Tài Liệu (MANDATORY Rules)

Để tránh tình trạng trôi lệch cấu trúc tài liệu thiết kế (doc) so với code thực thi:
1. **Quy tắc Bắt buộc**: Khi bất kỳ trường dữ liệu DB nào bị thay đổi hoặc API Router/Schema thay đổi, lập trình viên (hoặc Agent) **PHẢI** cập nhật tệp tài liệu hướng dẫn tương ứng nằm trong [.agent/doc/](file:///Volumes/ssd_roi/prj/my-fastapi-project/.agent/doc/) trong cùng một commit.
2. **Task Checklist**: Mọi Task Checklist phát triển tính năng đều phải chứa mục kiểm tra tài liệu ở phần `Post-Implementation`:
   - `[ ] Update: .agent/doc/<feature>-doc.md`
3. **Cơ chế kiểm soát tự động**: Trước khi đóng PR hoặc đẩy code, công cụ lint / kiểm tra dự án sẽ quét sự thay đổi của code trong thư mục `features/<feature>` và yêu cầu tệp `<feature>-doc.md` tương ứng phải được cập nhật tương đương.
