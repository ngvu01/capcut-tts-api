import streamlit as st
import subprocess
import json
import time
import sys

def extract_valid_json(output_str):
    try:
        return json.loads(output_str)
    except json.JSONDecodeError:
        start_idx = output_str.find('{')
        end_idx = output_str.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = output_str[start_idx:end_idx+1]
            try:
                return json.loads(clean_json)
            except Exception as e:
                raise ValueError(f"Dữ liệu JSON bị hỏng: {e}")
        else:
            raise ValueError(f"Không tìm thấy định dạng JSON trong: \n{output_str}")

st.set_page_config(page_title="CapCut TTS Web", page_icon="🎙️", layout="centered")
st.title("🎙️ Công cụ tạo giọng nói CapCut")

text_input = st.text_area("Nhập văn bản cần đọc:", height=150)

with st.expander("⚙️ Cài đặt giọng đọc nâng cao"):
    col1, col2 = st.columns(2)
    with col1:
        voice_id = st.text_input("Mã giọng (Voice ID):")
    with col2:
        resource_id = st.text_input("Resource ID:")
    rate = st.slider("Tốc độ đọc (Rate):", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

if st.button("Tạo âm thanh", type="primary", use_container_width=True):
    if not text_input.strip():
        st.warning("⚠️ Vui lòng nhập đoạn văn bản!")
    else:
        status_box = st.empty()
        status_box.info("🚀 Đang gửi yêu cầu tới CapCut...")
        
        try:
            python_path = sys.executable
            cmd_new = [python_path, 'capcut_common_task_client.py', 'tts-new', '--text', text_input]
            
            if voice_id.strip() and resource_id.strip():
                cmd_new.extend(['--voice', voice_id.strip(), '--resource-id', resource_id.strip()])
            if rate != 1.0:
                cmd_new.extend(['--rate', str(rate)])

            result_new = subprocess.run(cmd_new, capture_output=True, text=True, check=True, encoding='utf-8')
            data_new = extract_valid_json(result_new.stdout)
            
            # --- KIỂM TRA LỖI TỪ CAPCUT TẠI ĐÂY ---
            if "data" not in data_new or "tasks" not in data_new["data"]:
                status_box.error("❌ CapCut đã từ chối yêu cầu. Chi tiết lỗi từ máy chủ CapCut:")
                st.json(data_new) # In thẳng lỗi để chẩn đoán
            else:
                # Nếu có tasks thì xử lý bình thường
                task_id = data_new["data"]["tasks"][0]["id"]
                token = data_new["data"]["tasks"][0]["token"]
                
                status_box.info(f"⏳ Đã tạo Task ({task_id[:6]}...). Đang đợi âm thanh...")
                
                success = False
                for i in range(15):
                    time.sleep(2) 
                    
                    cmd_query = [python_path, 'capcut_common_task_client.py', 'tts-query', '--task-id', task_id, '--token', token]
                    result_query = subprocess.run(cmd_query, capture_output=True, text=True, check=True, encoding='utf-8')
                    data_query = extract_valid_json(result_query.stdout)
                    
                    if "data" not in data_query or "tasks" not in data_query["data"]:
                        status_box.error("❌ Truy vấn thất bại. Phản hồi từ CapCut:")
                        st.json(data_query)
                        break

                    status = data_query["data"]["tasks"][0]["status"]
                    
                    if status == "success":
                        status_box.success("✅ Thành công! Tải âm thanh bên dưới:")
                        payload_str = data_query["data"]["tasks"][0]["payload"]
                        try:
                            payload_json = extract_valid_json(payload_str)
                            audio_url = payload_json.get("url") or payload_json.get("speech_url") or payload_str
                            st.audio(audio_url)
                        except:
                            st.code(payload_str)
                        success = True
                        break
                    elif status == "failed":
                        status_box.error("❌ Xảy ra lỗi xử lý âm thanh từ CapCut.")
                        break
                        
                if not success and ("data" in data_query and "tasks" in data_query["data"]):
                    status_box.warning("⚠️ Đã hết thời gian chờ (30 giây).")
                    
        except subprocess.CalledProcessError as e:
            status_box.error("❌ Lỗi hệ thống khi chạy file Python.")
            st.code(e.stderr)
        except Exception as e:
            status_box.error(f"❌ Có lỗi: {e}")
