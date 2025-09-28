from tinydb import TinyDB, Query
from datetime import datetime

db = TinyDB("accounts.json")
accounts_table = db.table("accounts")

def save_account_metadata(user_id, phone, session_name, account_name, username):
    Account = Query()
    
    # Check if the user + phone already exists
    existing = accounts_table.get((Account.user_id == user_id) & (Account.phone == phone))

    data = {
        "user_id": user_id,
        "phone": phone,
        "session_name": session_name,
        "account_name": account_name,
        "username": username,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }

    if existing:
        accounts_table.update(data, doc_ids=[existing.doc_id])
        print("🔁 Updated existing account in DB")
    else:
        accounts_table.insert(data)
        print("✅ New account saved to DB")
      
