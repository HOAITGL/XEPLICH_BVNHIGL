import json
import os

def get_unit_config():
    filepath = os.path.join(os.path.dirname(__file__), 'unit_config.json')
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Dữ liệu mặc định nếu không đọc được file
    return {
        "name": "ĐƠN VỊ MẶC ĐỊNH",
        "address": "",
        "phone": ""
    }
