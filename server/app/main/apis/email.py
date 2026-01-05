from ..apis import vedasis_search
from flask_restplus import Resource
from flask import jsonify, request
import flask
from ..utils.decorators import require_permission
from ..services.email import GmailService
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import threading
import base64

api = vedasis_search.api_email 

@api.route("/accounts")
class GmailAccounts(Resource):
    @require_permission("email_access") 
    @api.doc(security="apikey", description="List ALL connected Gmail accounts")
    def get(self, method_data=None, current_user_obj=None, auth_token_data=None):
        gmail_service = GmailService("")  
        accounts = gmail_service.list_all_accounts()
        return {"accounts": accounts}, 200

@api.route("/auth-url")
class GmailAuthUrl(Resource):
    @require_permission("email_access")
    @api.doc(security="apikey")
    def get(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            if not auth_token_data or "uid" not in auth_token_data:
                return {"error": "Missing uid in auth_token_data"}, 400

            uid = auth_token_data["uid"]
            gmail_service = GmailService(uid)
            return gmail_service.get_auth_url(), 200
        except Exception as ex:
            return {"error": str(ex)}, 500

@api.route("/accounts/<account_id>/disconnect")
class GmailDisconnect(Resource):
    @require_permission("email_access")
    @api.doc(security="apikey", 
             description="Disconnect a Gmail account",
             params={'account_id': 'ID of the Gmail account to disconnect'})
    def post(self, account_id: str, method_data=None, current_user_obj=None, auth_token_data=None):
        """
        Disconnect a Gmail account
        
        This endpoint removes the Gmail account's credentials and data from the system.
        After disconnection, you'll need to re-authenticate to use the account again.
        """
        try:
            if not auth_token_data or "uid" not in auth_token_data:
                return {"error": "Missing uid in auth token"}, 400

            uid = auth_token_data["uid"]
            gmail_service = GmailService(uid)
            result = gmail_service.disconnect_account(account_id)

            if result.get("success"):
                return result, 200
            else:
                return {"error": result.get("error", "Failed to disconnect account")}, 400

        except Exception as e:
            return {"error": str(e)}, 500

@api.route("/admin/accounts/<account_id>/disconnect")
class AdminGmailDisconnect(Resource):
    @require_permission("admin_flag")  
    @api.doc(security="apikey", 
             description="Admin endpoint to disconnect any Gmail account",
             params={'account_id': 'ID of the Gmail account to disconnect'})
    def post(self, account_id: str, method_data=None, current_user_obj=None, auth_token_data=None):
        """
        Admin endpoint to disconnect any Gmail account
        
        This endpoint allows administrators to disconnect any Gmail account from the system,
        regardless of which user the account belongs to. Use with caution.
        """
        try:
            if not auth_token_data or "uid" not in auth_token_data:
                return {"error": "Missing uid in auth token"}, 400

            uid = auth_token_data["uid"]
            gmail_service = GmailService(uid)
            result = gmail_service.disconnect_account(account_id, admin_mode=True)

            if result.get("success"):
                return result, 200
            else:
                return {"error": result.get("error", "Failed to disconnect account")}, 400

        except Exception as e:
            return {"error": str(e)}, 500
            
@api.route("/callback")
class GmailCallback(Resource):
    def get(self):
        try:
            code = request.args.get("code")
            state = request.args.get("state")  
            if not code or not state:
                return {"error": "Missing code or state parameter"}, 400

            try:
                uid, account_id = state.split(":", 1)
            except ValueError:
                return {"error": "Invalid state format"}, 400

            gmail_service = GmailService(uid)
            account_id, error = gmail_service.handle_callback(state, code)

            if error:
                return {"error": error}, 400

            html = """
            <html><body>
              <script>
                window.opener.postMessage({
                    type: 'GMAIL_CONNECTED',
                    accountId: '%s'
                }, '*');
                window.close();
              </script>
              <p>Successfully connected Gmail account! You can close this window.</p>
            </body></html>
            """ % (account_id)
            return flask.Response(html, mimetype="text/html")

        except Exception as e:
            return {"error": f"Internal server error: {str(e)}"}, 500

@api.route("/messages")
class GmailMessages(Resource):
    @require_permission("email_access")
    @api.doc(security="apikey", description="List Gmail messages for the specified account (header: account_id)")
    def get(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            gmail_service = GmailService("")

            account_id = flask.request.headers.get("account_id")
            if not account_id:
                return {"error": "Missing account_id header"}, 400

            max_results = flask.request.headers.get("maxResults") or 10
            max_results = max(1, min(int(max_results), 100))

            messages = gmail_service.list_messages(account_id=account_id, max_results=max_results)
            return {"messages": messages}, 200
        except ValueError as ve:
            return {"error": str(ve)}, 400
        except Exception as ex:
            return {"error": str(ex)}, 500

def _json_safe(obj):
    import base64
    from datetime import datetime, date

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return base64.urlsafe_b64encode(obj).decode()
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, tuple):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    return str(obj)

@api.route("/messages/full")
class GmailMessagesFull(Resource):
    #@require_permission("email_access")
    #@api.doc(security="apikey", description="List FULL Gmail messages (sanitized) for the specified account (header: account_id)")
    
    def get(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            gmail_service = GmailService("")

            account_id = flask.request.headers.get("account_id")
            if not account_id:
                return {"error": "Missing account_id header"}, 400

            service = gmail_service.get_service(account_id)
            resp = service.users().messages().list(userId="me").execute()
            ids = [m["id"] for m in resp.get("messages", [])]

            details = []
            for mid in ids:
                msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
                details.append(_json_safe(msg))

            return {"messages": details}, 200
        except ValueError as ve:
            return {"error": str(ve)}, 400
        except Exception as ex:
            return {"error": str(ex)}, 500

@api.route("/send")
class GmailSend(Resource):
    @api.doc(security="apikey", description="Send an email via Gmail")
    #@api.expect(swagger_schemas.send_email_schema)
    @require_permission("email_access")
    def post(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            data = request.get_json(force=True)  
            to = data.get("to")
            subject = data.get("subject")
            body = data.get("body")

            if not all([to, subject, body]):
                return {"error": "missing required fields: to, subject, body"}, 400

            if not auth_token_data or "uid" not in auth_token_data:
                return {"error": "Missing uid in auth_token_data"}, 400

            uid = auth_token_data["uid"]
            account = GmailService(uid)
            creds = account.get_credentials()
            if not creds:
                return {"error": "gmail not connected"}, 400

            service = build("gmail", "v1", credentials=creds)
            msg = MIMEText(body, "html")
            msg["to"] = to
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            sent = service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            return {"id": sent["id"], "success": True}, 200
        except Exception as ex:
            return {"error": str(ex)}, 500
