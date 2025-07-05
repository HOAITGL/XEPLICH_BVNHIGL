from models import User

# Hàm chuẩn hóa contract_type
def standardize_contract_type(raw):
    if not raw:
        return None
    cleaned = raw.strip().lower()
    if 'biên' in cleaned:
        return 'Biên chế'
    elif 'hợp' in cleaned:
        return 'Hợp đồng'
    return cleaned.title()

# Cập nhật dữ liệu
updated = 0
for user in User.query.all():
    original = user.contract_type
    standardized = standardize_contract_type(original)
    if original != standardized:
        user.contract_type = standardized
        updated += 1

db.session.commit()
print(f"✅ Đã chuẩn hóa {updated} người dùng.")
