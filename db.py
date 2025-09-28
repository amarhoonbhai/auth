from tinydb import TinyDB, Query
from datetime import datetime
import os

DB_FILE = "accounts.json"
db = TinyDB(DB_FILE)
accounts_table = db.table("accounts")
queue_table = db.table("login_queue")

def enqueue_login(request: dict):
    request["created_at"] = datetime.utcnow().isoformat()
    queue_table.insert(request)

def dequeue_login():
    Item = Query()
    all_items = queue_table.all()
    if not all_items:
        return None
    item = all_items[0]
    queue_table.remove(doc_ids=[item.doc_id])
    return item

def save_account_metadata(user_id, phone, session_name, account_name, username, session_string):
    Account = Query()
    existing = accounts_table.get((Account.user_id == user_id) & (Account.phone == phone))
    data = {
        "user_id": user_id,
        "phone": phone,
        "session_name": session_name,
        "account_name": account_name,
        "username": username,
        "session_string": session_string,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    if existing:
        accounts_table.update(data, doc_ids=[existing.doc_id])
    else:
        accounts_table.insert(data)

def get_all_accounts():
    return accounts_table.all()
