# debug_password.py
import hashlib
from app.database import get_db
from app.crud.user_crud import get_user_by_email

def debug_password():
    db = next(get_db())
    user_email = "rushi@gmail.com"
    test_password = "$2b$12$9C4khzaOn66gKFOcFcPuL.mOLGTlqb5HgDQNTNuLOoZ0rlBHCmhIG"  # ← Change this to the actual password you're trying
    
    print("🔍 PASSWORD DEBUGGING")
    print("=" * 50)
    
    # 1. Check if user exists
    user = get_user_by_email(db, user_email)
    if not user:
        print("❌ USER NOT FOUND IN DATABASE")
        return
        
    print(f"✅ User found: {user.first_name} {user.last_name}")
    print(f"📧 Email: {user.email}")
    print(f"🔑 Stored hash: {user.password}")
    print(f"📝 Password you're trying: '{test_password}'")
    print("")
    
    # 2. Test the hashing function
    def get_password_hash(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    input_hash = get_password_hash(test_password)
    print(f"🔐 Input password hash: {input_hash}")
    print(f"✅ Hashes match: {input_hash == user.password}")
    print("")
    
    # 3. Test different common passwords (if you're not sure)
    common_passwords = ["password", "123456", "rushi", "rushi123", "test", "admin"]
    print("🧪 Testing common passwords:")
    for common in common_passwords:
        common_hash = get_password_hash(common)
        if common_hash == user.password:
            print(f"   🎯 FOUND MATCH: '{common}' -> {common_hash}")
        else:
            print(f"   ❌ '{common}' -> {common_hash[:20]}...")
    
    print("")
    print("💡 If hashes don't match, the password is wrong")
    print("💡 If you forgot the password, use the reset feature")

if __name__ == "__main__":
    debug_password()