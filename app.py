import streamlit as st
import subprocess
import json
import time
import sys

# Hàm bóc tách JSON thông minh (Bỏ qua các dòng cảnh báo thừa)
def extract_valid_json(output_str):
    try:
        # Thử đọc trực tiếp trước
        return json.loads(output_str)
    except json.JSONDecodeError:
        # Nếu lỗi, tìm dấu ngoặc nhọn đầu tiên và cuối cùng để lấy lõi JSON
        start_idx = output_str.find('{')
        end_idx = output_str.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = output_str[start_idx:end_idx+1]
            try:
                return json.loads(clean_json)
            except Exception as e:
                raise ValueError(f"Đã tìm thấy ngoặc JSON nhưng dữ liệu bên trong bị hỏng: {e}")
        else:
            raise ValueError(f"Không tìm thấy định dạng JSON trong phản hồi: \n{output_str}")

# Cấu hình giao diện trang web
st.set_page_config(page_title="CapCut TTS Web", page_icon="🎙️", layout="centered")

st.title("🎙️ Công cụ tạo giọng nói CapCut")
st.markdown("Chuyển đổi văn bản thành giọng nói AI của CapCut miễn phí.")

# Ô nhập văn bản
text_input = st.text_area("Nhập văn bản cần đọc (Tiếng Việt):", height=150, placeholder="Xin chào, đây là công cụ đọc văn bản...")

# Khung cài đặt nâng cao
with st.expander("⚙️ Cài đặt giọng đọc nâng cao (Tùy chọn)"):
    st.markdown("*(Để trống nếu muốn dùng giọng mặc định. Xem mã giọng trong file `Voice.json`)*")
    col1, col2 = st.columns(2)
    with col1:
        voice_id = st.text_input("Mã giọng (Voice ID):", placeholder="VD: BV074_streaming")
    with col2:
        resource_id = st.text_input("Resource ID:", placeholder="VD: 7102355709945188865")
    
    rate = st.slider("Tốc độ đọc (Rate):", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# Nút bấm chạy xử lý
if st.button("Tạo âm thanh", type="primary", use_container_width=True):
    if not text_input.strip():
        st.warning("⚠️ Vui lòng nhập đoạn văn bản bạn muốn chuyển đổi!")
    else:
        status_box = st.empty()
        status_box.info("🚀 Đang khởi tạo dịch vụ, vui lòng đợi...")
        
        try:
            python_path = sys.executable
            
            # 1. Chuẩn bị lệnh tạo Task (tts-new)
            cmd_new = [python_path, 'capcut_common_task_client.py', 'tts-new', '--text', text_input]
            
            if voice_id.strip() and resource_id.strip():
                cmd_new.extend(['--voice', voice_id.strip(), '--resource-id', resource_id.strip()])
            if rate != 1.0:
                cmd_new.extend(['--rate', str(rate)])

            # Chạy lệnh
            result_new = subprocess.run(cmd_new, capture_output=True, text=True, check=True, encoding='utf-8')
            
            # SỬ DỤNG HÀM LỌC JSON THÔNG MINH TẠI ĐÂY
            data_new = extract_valid_json(result_new.stdout)
            
            # Lấy thông tin ID và Token từ CapCut trả về
            task_id = data_new["data"]["tasks"][0]["id"]
            token = data_new["data"]["tasks"][0]["token"]
            
            status_box.info(f"⏳ Đã gửi yêu cầu thành công tới CapCut (Task: {task_id[:6]}...). Đang xử lý file âm thanh...")
            
            # 2. Vòng lặp chờ file âm thanh
            success = False
            for i in range(15):
                time.sleep(2) 
                
                cmd_query = [python_path, 'capcut_common_task_client.py', 'tts-query', '--task-id', task_id, '--token', token]
                result_query = subprocess.run(cmd_query, capture_output=True, text=True, check=True, encoding='utf-8')
                
                # SỬ DỤNG HÀM LỌC JSON THÔNG MINH TẠI ĐÂY
                data_query = extract_valid_json(result_query.stdout)
                
                status = data_query["data"]["tasks"][0]["status"]
                
                if status == "success":
                    status_box.success("✅ Thành công! Bạn có thể nghe và tải file âm thanh bên dưới:")
                    
                    payload_str = data_query["data"]["tasks"][0]["payload"]
                    
                    try:
                        payload_json = extract_valid_json(payload_str)
                        audio_url = payload_json.get("url") or payload_json.get("speech_url") or payload_str
                        st.audio(audio_url)
                    except:
                        # Backup: in thẳng ra nếu định dạng không phải JSON
                        st.code(payload_str)
                        
                    success = True
                    break
                elif status == "failed":
                    status_box.error("❌ Xảy ra lỗi từ phía máy chủ CapCut. Không thể chuyển đổi giọng nói này.")
                    break
                    
            if not success:
                status_box.warning("⚠️ Đã hết thời gian chờ nhưng chưa nhận được file. Đoạn văn của bạn có thể quá dài.")
                
        except subprocess.CalledProcessError as e:
            status_box.error("❌ Lỗi thực thi file hệ thống (Subprocess Error).")
            # In ra lỗi gốc của hệ thống để dễ bắt bệnh
            st.code(f"Mã lỗi: {e.returncode}\nChi tiết: {e.stderr}") 
        except Exception as e:
            status_box.error(f"❌ Có lỗi kỹ thuật xảy ra: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Được triển khai trên Streamlit Cloud</p>", unsafe_allow_html=True)
