# Giọng Việt Studio

Ứng dụng tạo giọng đọc tiếng Việt trên Windows: nhập kịch bản, chọn giọng tham chiếu, chỉnh tốc độ và khoảng nghỉ, xuất WAV hoặc MP3.

Giao diện Vue chạy trong trình duyệt. Launcher Python phục vụ giao diện trên `127.0.0.1`; worker dùng VieNeu v3 Turbo, ONNX Runtime và FFmpeg để tạo âm thanh trên máy.

## Thành phần

- `src/`: giao diện Vue, nút theo mẫu Shadcn-vue/Reka UI, chuyển động với motion-v.
- `launcher.py`: máy chủ nội bộ, quản lý tác vụ và mở giao diện.
- `worker.py`: tạo giọng đọc và xuất âm thanh.
- `dong-goi.ps1`: đóng gói portable theo bố cục thư mục của dự án gốc.
- `HUONG-DAN.txt`: hướng dẫn sử dụng và kiểm tra thủ công.

## Chuẩn bị và đóng gói

Yêu cầu Windows x64, Node.js/npm và môi trường Python 3.13 có VieNeu 3.8.3, NumPy, SoundFile, ONNX Runtime, PyInstaller. Mô hình VieNeu v3 Turbo cùng MOSS Audio Tokenizer Nano ONNX cần được chuẩn bị trong cache Hugging Face.

```powershell
npm install
npm run build
```

Script `dong-goi.ps1` hiện dùng tài nguyên của dự án gốc ở thư mục cha:

```text
thu-muc-cha/
  .tools/vieneu/                   # Python venv và thư viện
  .tools/vieneu-models/            # HF cache có mô hình
  Vidieo tuyên truyền/giong-Ha-Noi/MC-tham-chieu-5p82-giay.wav
  Ung-dung-tao-giong/             # repo này
```

Đường dẫn FFmpeg trong script trỏ đến bản cài Chocolatey. Trên máy khác, chỉnh các đường dẫn tài nguyên tương ứng trong script trước khi đóng gói. Script tải Python embeddable từ python.org, chép các thư viện/mô hình và tạo EXE bằng PyInstaller.

```powershell
.\dong-goi.ps1
```

Kết quả nằm trong `Giong-Viet-Portable/`. Chép **toàn bộ thư mục** sang máy nhận và mở `Giong-Viet-Studio.exe`. Cần quyền ghi trong thư mục ứng dụng. Chế độ tạo giọng được đặt offline; máy phải có bộ mô hình đầy đủ. Khuyến nghị RAM từ 8 GB; mức tương thích còn phụ thuộc CPU và thư viện native.

## Dữ liệu và quyền sử dụng

Repo chỉ chứa mã nguồn. Không kèm giọng mẫu của dự án, nội dung riêng, mô hình, nhật ký, file xuất hoặc gói EXE. Hãy tự cung cấp mẫu giọng được phép sử dụng. Các mô hình và thư viện có điều khoản riêng; repo không cấp lại quyền cho các thành phần đó.

Ứng dụng lưu nội dung và giọng mẫu từng lượt trong `work/`, âm thanh trong `outputs/`, nhật ký trong `logs/`. Các thư mục này không được đưa vào Git.

## Trạng thái

Đã đóng gói giao diện và EXE. Chưa chạy kiểm thử ứng dụng theo yêu cầu của chủ dự án; xem các bước kiểm tra thủ công trong `HUONG-DAN.txt`. Chất lượng giọng phụ thuộc mẫu và kịch bản; không bảo đảm giống hoàn toàn giọng gốc.
