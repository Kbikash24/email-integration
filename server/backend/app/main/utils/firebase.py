from firebase_admin import auth
from app.main.utils.authentication import db

def verify_jwt_token(jwt_token):
    try:
        decoded_token = auth.verify_id_token(jwt_token)
        uid = decoded_token['uid']
        return uid
    except Exception as ex:
        raise {'message': 'jwt token is invalid'}
    
def get_doc(uid):
    user_doc = db.collection('users').document(uid)
    out = user_doc.get().to_dict()
    return out

def get_list_group_doc(group_id):
    list_group_doc = db.collection('lists_group').document(group_id)
    out = list_group_doc.get().to_dict()
    return out

def get_document(collection, id):
    doc = db.collection(collection).document(id)
    return(doc)

def doc_field_dict(doc, key):
    try:
        dict = doc.get([key]).to_dict()
        if key in dict.keys():
            dict = dict[key]
        return(dict)
    except:
        return({})
    
def verify_token_and_get_doc(jwt_token):
    try:
        decoded_token = auth.verify_id_token(jwt_token)
        return decoded_token
    except Exception as ex:
        raise {'message': 'jwt token is invalid'}

def get_list_doc(list_id):
    list_doc = db.collection('lists').document(list_id)
    out = list_doc.get().to_dict()
    return out