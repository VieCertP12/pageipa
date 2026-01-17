import os
import re

# Thư mục chứa file plist
folder_path = './esignplist'
# Đầu link chuẩn bạn muốn
base_url = "https://sharechungchi.com/ipa"

print("Dang quet va sua loi link...")

if os.path.exists(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('.plist'):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tìm đoạn link bị sai (có chứa //github.com...) và lấy tên file đuôi .ipa
            # Thay thế bằng link chuẩn sharechungchi.com/ipa/Tên_File.ipa
            new_content = re.sub(
                r'<string>https://sharechungchi\.com/ipa//github\.com/.*?/([^/]+\.ipa)</string>', 
                rf'<string>{base_url}/\1</string>', 
                content
            )
            
            # Chỉ ghi lại file nếu có sự thay đổi
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Da sua: {filename}")
else:
    print("❌ Khong tim thay thu muc esignplist")