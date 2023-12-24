# (c) Mr. Avishkar

import datetime
from pymongo import MongoClient

class UsersDatabase:
    def __init__(self, uri, database_name):
        self._client = MongoClient(uri)
        self.db = self._client[database_name]
        self.col = self.db["users"]

    def new_user(self, id):
        return {
            "id": int(id),
            "join_date": datetime.date.today().isoformat(),
            "notif": True,
            "premium": False,
            "trial": False,
            "ban_status": {
                "is_banned": False,
                "ban_duration": 0,
                "banned_on": None,
                "ban_reason": "",
            },
            "clawbox": {
                "default_account": None,
                "accounts": [
                    # {
                    #     "account_info": {},
                    #     "refresh_token": {}
                    # }
                ],
            },
        }

    def add_user(self, id):
        user = self.new_user(id)
        self.col.insert_one(user)

    def is_user_exist(self, id):
        user = self.col.find_one({"id": int(id)})
        return True if user else False

    def total_users_count(self):
        count = self.col.count_documents({})
        return count

    def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    def delete_user(self, user_id):
        self.col.delete_many({"id": int(user_id)})

    def remove_ban(self, id):
        ban_status = {
            "is_banned": False,
            "ban_duration": 0,
            "banned_on": None,
            "ban_reason": "",
        }
        self.col.update_one({"id": int(id)}, {"$set": {"ban_status": ban_status}})

    def ban_user(self, user_id, ban_duration, ban_reason):
        ban_status = {
            "is_banned": True,
            "ban_duration": ban_duration,
            "banned_on": datetime.date.today().isoformat(),
            "ban_reason": ban_reason,
        }
        self.col.update_one({"id": int(user_id)}, {"$set": {"ban_status": ban_status}})

    def get_ban_status(self, id):
        default = {
            "is_banned": False,
            "ban_duration": 0,
            "banned_on": None,
            "ban_reason": "",
        }
        user = self.col.find_one({"id": int(id)})
        return user.get("ban_status", default)

    def get_all_banned_users(self):
        banned_users = self.col.find({"ban_status.is_banned": True})
        return banned_users

    def set_notif(self, id, notif):
        self.col.update_one({"id": int(id)}, {"$set": {"notif": notif}})

    def get_notif(self, id):
        user = self.col.find_one({"id": int(id)})
        return user.get("notif", False)

    def get_all_notif_user(self):
        notif_users = self.col.find({"notif": True})
        return notif_users

    def total_notif_users_count(self):
        count = self.col.count_documents({"notif": True})
        return count

    def login_clawbox(self, id, account_info, refresh_token):
        self.col.update_one(
            {"id": int(id)},
            {
                "$push": {
                    "clawbox.accounts": {
                        "account_info": account_info,
                        "refresh_token": refresh_token,
                    }
                }
            },
        )

    def logout_clawbox(self, id):
        self.col.update_one(
            {"id": int(id)},
            {
                "$set": {
                    "clawbox.accounts": []
                }
            },
        )

    def get_account(self, id):
        user = self.col.find_one({"id": int(id)})
        return user.get("clawbox", {}).get(
            "accounts", [{"account_info": {}, "refresh_token": {}}]
        )[-1]["account_info"]

    def get_refresh_token(self, id):
        user = self.col.find_one({"id": int(id)})
        _accounts = user.get("clawbox", {}).get(
            "accounts", [{"account_info": {}, "refresh_token": {}}]
        )
        if not _accounts:
            return {}
        return _accounts[-1]["refresh_token"]
    
    def get_last_payout_method(self, id):
        user = self.col.find_one({"id": int(id)})
        return user.get("payout_method", {})
    
    def set_payout_method(self, id, payout_method):
        self.col.update_one({"id": int(id)}, {"$set": {"payout_method": payout_method}})
    def __init__(self, uri, database_name):
        self._client = MongoClient(uri)
        self.db = self._client[database_name]
        self.col = self.db["admin"]

    def init(self, id):
        self.id = int(id)
        if not self.is_admin_exists():
            self.add_admin()

    def new_admin(self, id):
        return {
            "id": int(id),
            "maintenance": {"enabled": False, "updated_on": None, "updated_by": 0},
            "transaction_ids": [],
        }

    def add_admin(self):
        user = self.new_admin(self.id)
        self.col.insert_one(user)

    def is_admin_exists(self):
        user = self.col.find_one({"id": self.id})
        return True if user else False

    def set_maintenance(self, state, by):
        self.col.update_one({"id": self.id}, {"$set": {"maintenance.enabled": state}})
        self.col.update_one(
            {"id": self.id},
            {
                "$set": {
                    "maintenance.updated_on": datetime.datetime.now(
                        tz=datetime.timezone.utc
                    ).isoformat(timespec="seconds")
                }
            },
        )
        self.col.update_one(
            {"id": self.id}, {"$set": {"maintenance.updated_by": int(by)}}
        )