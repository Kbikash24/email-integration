"""
Authentication and Authorization Decorators

This module provides decorators for handling JWT authentication, user loading,
permission checking, and request data extraction in the Vhub Admin Backend API.

The main decorator `require_permission` is used throughout the API endpoints
to ensure secure access control and consistent authentication patterns.
"""

import flask
from flask import jsonify
from .firebase import verify_token_and_get_doc 
from functools import wraps
from ..services import users 
from typing import Callable, Any, Optional, Dict, Union


def require_permission(permission_key: str, expects_request_data: bool = False) -> Callable:
    """
    Decorator to handle JWT authentication, user loading, permission checking,
    and optionally extracting request data (headers for GET, JSON for POST/PUT/PATCH).
    
    This decorator provides a comprehensive authentication and authorization
    layer for API endpoints. It verifies JWT tokens, loads user objects,
    checks permissions, and optionally extracts request data based on HTTP method.
    
    Args:
        permission_key (str): The permission key to check in user's permissions.
            Special key 'self_profile_access' skips permission check after authentication.
        expects_request_data (bool): Whether to extract and pass request data to the
            decorated function. For GET requests, extracts headers; for POST/PUT/PATCH
            requests, extracts JSON body. Defaults to False.
    
    Returns:
        Callable: The decorated function with authentication and authorization applied.
    
    Raises:
        401: When authorization header is missing or token is invalid
        403: When user lacks required permissions
        
    Usage Examples:
        @require_permission('users_admin_access', expects_request_data=False)
        def get_admin_data(self, method_data=None, current_user_obj=None, auth_token_data=None):
            # Only users with 'users_admin_access' permission can access this
            return jsonify(admin_data)
            
        @require_permission('lists_view_access', expects_request_data=True)
        def get_list_details(self, method_data=None, current_user_obj=None, auth_token_data=None):
            # method_data contains request headers (GET) or JSON body (POST)
            list_id = method_data.get('list_id')
            return jsonify(list_details)
    
    The decorated function receives these additional parameters:
        - method_data: Request data (headers for GET, JSON for POST/PUT/PATCH) if expects_request_data=True
        - current_user_obj: User object with loaded permissions and profile data
        - auth_token_data: Raw JWT token payload for additional context
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(self, *args, **kwargs) -> Any:
            try:
                # Extract and validate Authorization header
                auth_header = flask.request.headers.get('Authorization')
                if not auth_header:
                    return jsonify({'Message': 'Authorization header missing'}), 401

                # Verify JWT token and extract user data
                auth_token_data_payload = verify_token_and_get_doc(auth_header)
                if not auth_token_data_payload or 'user_id' not in auth_token_data_payload:
                     return jsonify({'Message': 'Invalid token or user_id missing from token'}), 401

                # Load user object with permissions and profile data
                current_user = users.User(auth_token_data_payload['user_id'])

                # Check permissions (skip for self_profile_access)
                if permission_key != 'self_profile_access':
                    if not current_user.permissions.get(permission_key, False):
                        return jsonify({'Message': 'You do not have access.!'}), 403
                # Note: For 'self_profile_access', we assume the user always has access 
                # to their own profile data after successful authentication

                # Extract request data based on HTTP method if requested
                method_payload_data = None
                if expects_request_data:
                    if flask.request.method in ['POST', 'PUT', 'PATCH']:
                        # Extract JSON body for modification requests
                        method_payload_data = flask.request.json
                    elif flask.request.method == 'GET':
                        # Extract headers for read requests (e.g., list_id, filters)
                        method_payload_data = flask.request.headers

                # Call the original function with authentication context
                return f(
                    self, 
                    *args, 
                    method_data=method_payload_data, 
                    current_user_obj=current_user, 
                    auth_token_data=auth_token_data_payload, 
                    **kwargs
                )
            except Exception as ex:
                # Re-raise to be handled by Flask's error handling
                raise ex  
        return decorated_function
    return decorator