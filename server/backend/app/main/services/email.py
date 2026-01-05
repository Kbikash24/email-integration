from typing import Optional, Dict, List, Any
from app.main.utils.authentication import db
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64
from uuid import uuid4
from email.mime.text import MIMEText
import json
import os

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# Define the path to your client secrets file
CLIENT_SECRET_FILE = "app/main/files/client_secret.json"

def build_timestamp():
    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    return SERVER_TIMESTAMP

class GmailService:
    def __init__(self, uid: str):
        self.uid = uid
        self.db = db

    def _get_client_config(self):
        """Read the client secrets file and return the config."""
        with open(CLIENT_SECRET_FILE, "r") as f:
            return json.load(f)

    def get_flow(self, state=None):
        conf = self._get_client_config()
        flow = Flow.from_client_config(
            conf,
            scopes=SCOPES,
            redirect_uri=conf["web"]["redirect_uris"][0]
        )
        if state:
            flow.state = state
        return flow

    def _get_existing_account_id(self) -> Optional[str]:
        ref = self.db.collection("users").document(self.uid).collection("gmailAccounts")
        docs = list(ref.limit(1).stream())
        return docs[0].id if docs else None

    def _ensure_account_doc(self, account_id: str) -> None:
        doc_ref = (self.db.collection("users")
                .document(self.uid)
                .collection("gmailAccounts")
                .document(account_id))
        doc_ref.set({"createdAt": build_timestamp()}, merge=True)

    def list_all_accounts(self) -> List[Dict]:
        print("\n" + "="*60)
        print("DEBUG: list_all_accounts() CALLED")
        print("="*60)
        try:
            print(f"DEBUG: self.uid = '{self.uid}'")
            print(f"DEBUG: Calling collection_group('gmailAccounts').stream()")
            
            accounts = []
            doc_count = 0
            
            for doc in self.db.collection_group("gmailAccounts").stream():
                doc_count += 1
                print(f"\nDEBUG: Processing document #{doc_count}: {doc.id}")
                try:
                    data = doc.to_dict() or {}
                    print(f"DEBUG: Document data: {data}")
                    
                    created_at = data.get("createdAt")
                    uid = None
                    try:
                        uid = doc.reference.parent.parent.id
                        print(f"DEBUG: Got uid: {uid}")
                    except Exception as e:
                        print(f"DEBUG: Error getting uid: {str(e)}")
                    
                    account_obj = {
                        "uid": uid,
                        "accountId": doc.id,
                        "emailAddress": data.get("emailAddress"),
                        "name": data.get("name"),
                        "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat")
                                    else (str(created_at) if created_at else None),
                    }
                    print(f"DEBUG: Adding account: {account_obj}")
                    accounts.append(account_obj)
                except Exception as e:
                    print(f"DEBUG: Error processing doc {doc.id}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    continue
            
            print(f"\nDEBUG: Total documents: {doc_count}, accounts: {len(accounts)}")
            return accounts
        except Exception as e:
            print(f"DEBUG: EXCEPTION in list_all_accounts: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def get_auth_url(self, account_id: Optional[str] = None) -> Dict[str, str]:
        if account_id:
            self._ensure_account_doc(account_id)
        else:
            existing_id = self._get_existing_account_id()
            if existing_id:
                account_id = existing_id
            else:
                account_id = str(uuid4())
                self._ensure_account_doc(account_id)
        state = f"{self.uid}:{account_id}"
        flow = self.get_flow(state=state)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="select_account consent",
            state=state
        )
        return {"url": auth_url, "accountId": account_id}

    def get_credentials(self, account_id: Optional[str] = None) -> Optional[Credentials]:
        if account_id:
            doc_ref, _owner_uid = self._doc_ref_for_account(account_id)
            if not doc_ref:
                return None
        else:
            if not self.uid:
                return None
            ref = (self.db.collection("users")
                   .document(self.uid)
                   .collection("gmailAccounts"))
            docs = list(ref.limit(1).stream())
            if not docs:
                return None
            doc_ref = docs[0].reference
        data = doc_ref.get().to_dict() or {}
        if "refresh_token" not in data:
            return None
        creds = Credentials(
            token=data.get("access_token"),
            refresh_token=data["refresh_token"],
            client_id=self._get_client_config()["web"]["client_id"],
            client_secret=self._get_client_config()["web"]["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES
        )
        if not creds.valid or creds.expired:
            creds.refresh(Request())
            doc_ref.update({
                "access_token": creds.token,
                "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
            })
        return creds

    def save_refresh_token(self, code: str, state: str):
        uid, account_id = state.split(":")
        flow = self.get_flow(state=state)
        flow.fetch_token(code=code)
        creds = flow.credentials
        doc_ref = self.db.collection("users").document(uid).collection("gmailAccounts").document(account_id)
        existing = doc_ref.get().to_dict() or {}
        refresh_token = creds.refresh_token or existing.get("refresh_token")
        if not refresh_token:
            return {"success": False, "error": "No refresh_token returned"}
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress")
        doc_ref.set({
            "refresh_token": refresh_token,
            "access_token": creds.token,
            "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
            "emailAddress": email_address,
            "name": email_address.split("@")[0] if email_address else "",
        }, merge=True)
        return {"success": True}

    def _doc_ref_for_account(self, account_id: str):
        if self.uid:
            doc_ref = (self.db.collection("users")
                       .document(self.uid)
                       .collection("gmailAccounts")
                       .document(account_id))
            snap = doc_ref.get()
            if snap.exists:
                return doc_ref, self.uid
        for doc in self.db.collection_group("gmailAccounts").stream():
            if doc.id == account_id:
                owner_uid = doc.reference.parent.parent.id
                return doc.reference, owner_uid
        return None, None

    def get_service(self, account_id: str):
        doc_ref, _owner_uid = self._doc_ref_for_account(account_id)
        if not doc_ref:
            raise ValueError("Gmail account not connected")
        data = doc_ref.get().to_dict() or {}
        if "refresh_token" not in data:
            raise ValueError("Gmail account not connected")
        creds = Credentials(
            token=data.get("access_token"),
            refresh_token=data["refresh_token"],
            client_id=self._get_client_config()["web"]["client_id"],
            client_secret=self._get_client_config()["web"]["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES
        )
        if not creds.valid or creds.expired:
            creds.refresh(Request())
            doc_ref.update({
                "access_token": creds.token,
                "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
            })
        return build("gmail", "v1", credentials=creds)

    def handle_callback(self, state, code):
        try:
            if ":" not in state:
                return None, "Invalid state format: expected 'uid:account_id'"

            uid, account_id = state.split(":", 1)
            flow = self.get_flow(state=state)
            flow.fetch_token(code=code)
            creds = flow.credentials

            if not creds.refresh_token:
                return None, "No refresh_token returned"

            doc_ref = self.db.collection("users").document(uid).collection("gmailAccounts").document(account_id)
            existing = doc_ref.get().to_dict() or {}
            refresh_token = creds.refresh_token or existing.get("refresh_token")

            if not refresh_token:
                return None, "No refresh_token returned"

            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            email_address = profile.get("emailAddress")

            doc_ref.set({
                "refresh_token": refresh_token,
                "access_token": creds.token,
                "expiry": str(creds.expiry),
                "emailAddress": email_address,
                "name": email_address.split("@")[0] if email_address else "",
            }, merge=True)

            return account_id, None

        except Exception as e:
            return None, f"Error in handle_callback: {str(e)}"

    def list_messages(self, account_id: str, max_results=10):
        service = self.get_service(account_id)
        resp = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = resp.get("messages", [])
        out = []
        for msg in messages:
            mdata = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            out.append({
                "id": mdata["id"],
                "snippet": mdata.get("snippet", ""),
                "headers": {h["name"]: h["value"] for h in mdata["payload"]["headers"]}
            })
        return out

    def send_message(self, account_id: str, to: str, subject: str, body: str):
        service = self.get_service(account_id)
        msg = MIMEText(body, "html")
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return sent

    def disconnect_account(self, account_id: str, admin_mode: bool = False) -> Dict[str, Any]:
        """
        Disconnect a Gmail account.

        Args:
            account_id: The ID of the Gmail account to disconnect.
            admin_mode: If True, allows admin to disconnect any account. If False, only the owner can disconnect.

        Returns:
            Dict: {"success": bool, "error": Optional[str]}
        """
        try:
            doc_ref, owner_uid = self._doc_ref_for_account(account_id)

            if not doc_ref:
                return {"success": False, "error": "Gmail account not found"}

            # If not admin_mode, ensure the current user is the owner
            if not admin_mode and owner_uid != self.uid:
                return {"success": False, "error": "You do not have permission to disconnect this account"}

            # Delete the account document
            doc_ref.delete()

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"Failed to disconnect account: {str(e)}"}
