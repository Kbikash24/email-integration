"""
User Management API Endpoints

This module provides REST API endpoints for user management in the Vhub Admin Backend.
It includes endpoints for fetching user data, updating user profiles and permissions,
managing admin operations, and handling user authentication and activity tracking.

All endpoints require proper authentication and most require admin-level permissions.
"""

from flask_restplus import Resource

from ..services import users
from flask import jsonify, request
from ..apis import vedasis_search
from ..utils.decorators import require_permission
import pandas as pd
from typing import Dict, Any, Optional

# API namespace for user-related endpoints
api = vedasis_search.api_users


@api.route('/user_doc')   ##working
# Handles GET to fetch current user's document and POST to create it.
class get_or_create_user_api(Resource):
    @api.doc(security='apikey')
    @require_permission('self_profile_access', expects_request_data=False) # Assuming 'self_profile_access' for own doc
    def get(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            response = current_user_obj.fetch_user_doc()
            return jsonify(response)
        except Exception as ex:
            raise ex
        
    
    @api.doc(security='apikey')
    @require_permission('self_profile_access', expects_request_data=True) # Assuming 'self_profile_access' for own doc
    def post(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            if current_user_obj.doc_exists == True:
                res, status_code = {"Error": "User Already Present"}, 500
            else:
                res, status_code = {"Error": "User document creation method has been removed"}, 501
            response = jsonify(res)
            response.status_code = status_code
            return (response)
        except Exception as ex:
            raise ex


@api.route('/fetch_email_from_uid')
# Handles POST requests to fetch emails from UIDs (admin access).
class fetch_email_from_uid_api(Resource):
    @api.doc(security='apikey')

    @require_permission('users_admin_access', expects_request_data=True)
    def post(self, method_data=None, current_user_obj=None, auth_token_data=None):
        try:
            res = users.fetch_email_from_uid(method_data['uids'])
            return jsonify(res)
        except Exception as ex:
            raise ex


@api.route('/new/<action>')
class NewUsersAPI(Resource):
    """New API endpoint for user operations with pagination support."""
    
    @api.doc(
        security='apikey',
        description='New user operations API with support for pagination and filtering. '
                   'Supports "get_users" action for pagination/filtering, "edit_user" action '
                   'for updating user documents, and "get_search_history" action for retrieving '
                   'user search history. Use new_users_api_body for get_users, '
                   'edit_user_api_body for edit_user, and get_search_history_api_body for get_search_history actions.',
        responses={
            200: 'Success - Returns paginated user data or edit confirmation',
            400: 'Bad Request - Invalid action or parameters',
            401: 'Unauthorized - Invalid or missing authentication token',
            403: 'Forbidden - User lacks admin access permissions',
            404: 'Not Found - User not found (for edit_user)'
        }
    )
    @require_permission('users_admin_access', expects_request_data=True)
    def post(self, action: str, method_data: Optional[Dict] = None, 
             current_user_obj: Optional[users.User] = None, 
             auth_token_data: Optional[Dict] = None) -> Any:
        """
        Handle new user operations with pagination support, user editing, and search history retrieval.
        
        Args:
            action: The action to perform (supports "get_users", "edit_user", and "get_search_history")
            method_data: JSON request body containing query parameters, pagination options, user edit data, or search history parameters
            
        Returns:
            JSON response containing paginated user data, edit confirmation, or error message
            
        Raises:
            Exception: Re-raised for Flask error handling
        """
        try:
            if action == 'get_users':
                result = users.get_users_with_pagination(method_data)
                return jsonify(result)
            elif action == 'edit_user':
                # Get user_id and create User instance
                user_id = method_data.get('user_id')
                if not user_id:
                    return jsonify({'error': 'user_id is required'}), 400
                
                user = users.User(user_id)
                result = user.edit_user_by_id(method_data)
                return jsonify(result)
            elif action == 'get_search_history':
                # Get user_id and create User instance
                user_id = method_data.get('id') or method_data.get('user_id')
                if not user_id:
                    return jsonify({'error': 'User ID is required (use "id" or "user_id" field)'}), 400
                
                user = users.User(user_id)
                result = user.get_search_history_with_pagination(method_data)
                return jsonify(result)
            else:
                return jsonify({'error': f'Unsupported action: {action}'}), 400
                
        except Exception as ex:
            raise ex

    @api.doc(
        security='apikey',
        description='Get specific user data by user_id. '
                   'Currently supports "get_user" action which returns the complete user class dictionary.',
        responses={
            200: 'Success - Returns user data',
            400: 'Bad Request - Invalid action or missing user_id',
            401: 'Unauthorized - Invalid or missing authentication token',
            403: 'Forbidden - User lacks admin access permissions',
            404: 'Not Found - User not found'
        }
    )
    
    @require_permission('users_admin_access', expects_request_data=True)
    def get(self, action: str, method_data: Optional[Dict] = None, 
            current_user_obj: Optional[users.User] = None, 
            auth_token_data: Optional[Dict] = None) -> Any:
        """
        Handle GET requests for user operations.
        
        Args:
            action: The action to perform (currently supports "get_user")
            method_data: Headers containing user_id parameter
            
        Returns:
            JSON response containing user data or error message
            
        Raises:
            Exception: Re-raised for Flask error handling
        """
        try:
            if action == 'get_user':
                user_id = method_data.get('user_id')
                if not user_id:
                    return jsonify({'error': 'user_id is required in headers'}), 400
                
                # Create User instance and return user data
                user = users.User(user_id)
                if not user.doc_exists:
                    return jsonify({'error': 'User not found'}), 404
                
                # Get user data dictionary and filter out internal fields
                user_data = user.__dict__.copy()
                internal_fields = ['doc_ref', 'doc_exists', 'doc_snap']
                for field in internal_fields:
                    user_data.pop(field, None)
                
                result = {
                    'success': True,
                    'user_id': user_id,
                    'user': user_data
                }
                return jsonify(result)
            else:
                return jsonify({'error': f'Unsupported GET action: {action}'}), 400
                
        except Exception as ex:
            raise ex
                
        except Exception as ex:
            raise ex