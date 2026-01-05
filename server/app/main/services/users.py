"""
User Management Service

This module provides the User class for managing user authentication, 
permissions, profile data, and billing information in the Vhub Admin Backend.

The User class integrates with Firebase Authentication and Firestore for 
user data management, and includes BigQuery operations for analytics.
"""

from app.main.utils.authentication import db, credentials_gcp, client
import firebase_admin
from firebase_admin import credentials, firestore, auth
import datetime
import pandas_gbq
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple

project_id = credentials_gcp.project_id


class User:
    """
    User model class for managing user authentication, profile data, and permissions.
    
    This class represents a user in the Vhub Admin Backend system, handling
    authentication via Firebase, user profile management via Firestore,
    permissions and access control, and billing/credit management.
    
    The class automatically loads user data from Firebase Auth and Firestore,
    sets default values for missing fields, and maintains synchronization
    between different data stores.
    
    Attributes:
        id (str): Unique user identifier from Firebase Auth
        email (str): User's email address
        displayName (str): User's display name
        emailVerified (bool): Whether the user's email is verified
        accountType (str): Type of user account ('free', 'premium', etc.)
        accountCategory (str): Category classification for the user
        permissions (dict): User permissions mapping for access control
        meteredBilling (dict): Billing information with credits and usage
        createdAt (int): Account creation timestamp
        last_login (int): Last login timestamp
        doc_ref: Firestore document reference for this user
        doc_exists (bool): Whether the user document exists in Firestore
        
    Example:
        >>> user = User('firebase_user_id_123')
        >>> if user.permissions.get('admin_access', False):
        ...     # User has admin access
        ...     pass
        >>> print(f"User {user.displayName} has {user.meteredBilling['TotalCredits']} credits")
    """
    
    def __init__(self, user_id: str):
        """
        Initialize a User object by loading data from Firebase Auth and Firestore.
        
        This constructor performs the following operations:
        1. Loads user authentication data from Firebase Auth
        2. Loads user profile data from Firestore (if exists)
        3. Sets default values for missing profile fields
        4. Synchronizes data between Firebase Auth and Firestore
        5. Loads and validates user permissions
        
        Args:
            user_id (str): The Firebase user ID to load
            
        Raises:
            firebase_admin.exceptions.FirebaseError: If user doesn't exist or auth fails
        """
        if user_id:
            # Load user authentication data from Firebase Auth
            user = auth.get_user(user_id)
            self.last_login = user.user_metadata.last_sign_in_timestamp
            
            # Set up Firestore document reference
            doc_ref = db.collection('users').document(user_id)
            self.doc_ref = doc_ref
            self.id = user_id
            doc_snap = doc_ref.get()
            
            # Load basic auth information
            user = auth.get_user(user_id)  # TODO: Remove duplicate call
            self.email = user.email
            self.createdAt = user.user_metadata.creation_timestamp
            
            # Load or initialize Firestore document data
            if doc_snap.exists:
                self.doc_exists = True
                self.__dict__.update(doc_snap.to_dict())
            else:
                self.doc_exists = False
                
            # Set default values for profile fields if missing
            self._set_default_profile_fields()
            
            # Update last login timestamp
            if hasattr(self, 'last_updated_at') is False:
                self.last_updated_at = self.last_login/1000
                
            # Synchronize data to Firestore
            doc_data = {k: self.__dict__[k] for k in self.__dict__.keys() 
                       if k not in ['doc_ref', 'doc_exists', 'doc_snap']}
            self.doc_ref.set(doc_data)
            
            # Load and validate permissions
            self.permissions_list = ['active'] + [
                key for key, value in self.permissions.items() if value
            ] if hasattr(self, 'permissions') and self.permissions else []
            self.set_permissions()
            
    def _set_default_profile_fields(self):
        """
        Set default values for user profile fields if they don't exist.
        
        This method ensures all expected user profile fields have default values
        to prevent attribute errors and maintain data consistency.
        """
        default_fields = {
            'accountCategory': '',
            'accountType': '',
            'phoneNumber': '',
            'source': '',
            'emailVerified': False,
            'username': '',
            'displayName': '',
            'meteredBilling': {'TotalCredits': 0, 'creditsUsed': 0}
        }
        
        for field, default_value in default_fields.items():
            if not hasattr(self, field):
                setattr(self, field, default_value)

    def set_permissions(self):
        permission_keys = [
            'admin_flag',
            'campaigns_admin_access', 'campaigns_view_access',
            'discovery_access',
            'users_admin_access',
            'lists_admin_access', 'lists_view_access',
            'projects_admin_access','projects_dash_access',
            'operations_admin_access','operations_dash_access',
            'zoho_admin_access','zoho_dash_access',
            'scraping_admin_access', 'scraping_dash_access',
            'tables_admin_access',
            'followers_admin_access',
            'tagging_admin_access', 'tagging_access',
            'vqs_access',
            'organisation_admin_access',
            'admin_sales_access','sales_dash_access',
            'email_access','payment_access'
        ]
        if 'permissions' not in self.__dict__.keys():
            self.permissions = {'admin_flag': False}
        if self.permissions:
            if self.permissions.get('admin_flag', False) == True:
                self.permissions.update({key: True for key in permission_keys})
            else:
                if self.permissions.get('lists_admin_access', False) == True:
                    self.permissions.update({'lists_view_access': True})
                if self.permissions.get('campaigns_admin_access', False) == True:
                    self.permissions.update({'campaigns_view_access': True})
                if self.permissions.get('projects_admin_access', False) == True:
                    self.permissions.update({'projects_dash_access': True})
                if self.permissions.get('operations_admin_access', False) == True:
                    self.permissions.update({'operations_dash_access': True})
                if self.permissions.get('scraping_admin_access', False) == True:
                    self.permissions.update({'scraping_dash_access': True})
                if self.permissions.get('tagging_admin_access', False) == True:
                    self.permissions.update({'tagging_access': True})
                if self.permissions.get('zoho_admin_access', False) == True:
                    self.permissions.update({'zoho_dash_access':True})
                if self.permissions.get('admin_sales_access', False) == True:
                    self.permissions.update({'sales_dash_access': True})
            print(self.permissions)
            self.__dict__.update({'permissions':self.permissions})
            self.doc_ref.set(self.__dict__)
            return {'status': 'success', 'message': 'Permissions updated', 'uid': self.id}

    def fetch_user_doc(self):
        user_data = {k: v for k, v in self.__dict__.items() if k not in ['doc_ref', 'search_history', 'last_login_history']}
        if user_data:
            self.update_last_activity()
            return user_data
        return {"Error":"user document not found!"}

    def update_last_activity(self):
        users = self.doc_ref
        user_doc = users.get().to_dict()

        users.update({
            'last_activity_time': datetime.datetime.now().timestamp(),
            'status': 'logged_in'
        })

    def get_user_search_history(self):
        usernames = []
        search_history = self.doc_ref.collection('extraData').document("search_history").get()
        if search_history.exists:
            history = search_history.to_dict().get("history", [])
            usernames = [entry.get("username") for entry in history if "username" in entry]
        return usernames

    def add_to_search_history(self,profile):
        search_history_ref = self.doc_ref.collection('extraData').document("search_history")
    
        search_history_doc = search_history_ref.get()
        history = search_history_doc.to_dict().get("history", []) if search_history_doc.exists else []

        new_profile = {
            "username": profile.username,
            "followers": profile.followers,
            "id": profile.id,
            "timestamp": datetime.datetime.now().timestamp()
        }
        history.append(new_profile)
        search_history_ref.set({"history": history}, merge=True)

    def add_user_activity(self, api_name, feature_id):
        query = f"""
        INSERT INTO `Profiles.user_activity_admin` (uid, time_stamp, api_name, feature_id)
        VALUES ('{self.id}', '{datetime.datetime.now().timestamp()}', '{api_name}', '{feature_id}')
        """
        try:
            client.query(query).result()
        except Exception as e:
            print(f"Error inserting row: {e}")

    def edit_user_by_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit this user's document with provided data.
        
        Args:
            data: Dictionary containing key-value pairs of fields to update
            
        Returns:
            Dictionary containing success/error message and updated data
        """
        try:
            update_data = data.get('data', {}) if 'data' in data else data
            
            if not update_data:
                return {
                    'error': 'data field with update values is required',
                    'success': False
                }
            
            if not self.doc_exists:
                return {
                    'error': f'User with ID {self.id} not found',
                    'user_id': self.id,
                    'success': False
                }
            
            # Update last_updated_at timestamp
            update_data['last_updated_at'] = datetime.datetime.now().timestamp()
            
            # Update the document in Firestore
            self.doc_ref.update(update_data)
            
            # Update the user instance with new data
            self.__dict__.update(update_data)
            
            return {
                'success': True,
                'message': f'User {self.id} updated successfully',
                'user_id': self.id,
                'updated_fields': list(update_data.keys()),
                'updated_data': update_data
            }
            
        except Exception as e:
            return {
                'error': f'Failed to update user: {str(e)}',
                'user_id': self.id,
                'success': False
            }

    def get_search_history_with_pagination(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get this user's search history with pagination.
        
        Args:
            data: Dictionary containing pagination parameters:
                - page: Page number (1-based)
                - page_size: Number of records per page
                - start_after: Document ID to start after for cursor-based pagination
            
        Returns:
            Dictionary containing search history data and pagination info
        """
        try:
            page_size = data.get('page_size', 10)
            page = data.get('page', 1)
            start_after = data.get('start_after')
            
            if not self.doc_exists:
                return {'error': 'User not found'}, 404
            
            # Query the search_history subcollection
            search_history_ref = self.doc_ref.collection('search_history')
            
            # Order by timestamp in descending order (newest first)
            query = search_history_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            # Apply pagination
            if start_after:
                # Cursor-based pagination using start_after
                start_after_doc = search_history_ref.document(start_after).get()
                if start_after_doc.exists:
                    query = query.start_after(start_after_doc)
                query = query.limit(page_size)
            else:
                # Page-based pagination
                offset = (page - 1) * page_size
                query = query.offset(offset).limit(page_size)
            
            # Execute query
            docs = query.get()
            
            search_history = []
            last_doc_id = None
            
            for doc in docs:
                doc_data = doc.to_dict()
                search_history.append({
                    'id': doc.id,
                    'username': doc_data.get('username', ''),
                    'followers': doc_data.get('followers', 0),
                    'profile_id': doc_data.get('id', ''),
                    'timestamp': doc_data.get('timestamp', 0)
                })
                last_doc_id = doc.id
            
            # Get total count of documents in the search_history subcollection
            total_count = len(list(search_history_ref.get()))
            
            result = {
                'search_history': search_history,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,  # Calculate total pages
                'has_next': page * page_size < total_count,
                'has_prev': page > 1
            }
            
            if last_doc_id and start_after:
                result['next_start_after'] = last_doc_id
                
            return result
            
        except Exception as e:
            return {'error': str(e)}, 500

    
def fetch_email_from_uid(uids):
    query = queries.p16.format(tables.table16,uids)
    df = pandas_gbq.read_gbq(query, project_id=project_id, credentials=credentials_gcp)
    return df.to_dict('records')

def add_user_activity_website(data, api_name, feature_id):
        user_value = data['user'] if 'user' in data and data['user'] else 'unknown'

        query = f"""
        INSERT INTO `Profiles.user_activity_website` (user, time_stamp, api_name, feature_id)
        VALUES ('{user_value}', '{datetime.datetime.now().timestamp()}', '{api_name}', '{feature_id}')
        """
        try:
            client.query(query).result()
        except Exception as e:
            print(f"Error inserting row: {e}")

def get_users_with_pagination(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch users from Firestore with pagination and filtering support.
    
    This function applies filters first at the query level where possible,
    then handles pagination on the filtered results for better performance
    and more accurate page sizes.
    
    Args:
        data: Dictionary containing pagination and filter parameters:
            - filters: Dict with 'query' field for case-insensitive search in displayName and email
            - sort_by: Field to sort by (createdAt, last_updated_at)
            - sort_order: Sort order (only 'desc' allowed)
            - page_size: Number of records per page (default: 20)
            - page: Page number (1-based, default: 1)
    
    Returns:
        Dictionary containing:
            - users: List of user documents with filtered fields
            - pagination: Pagination metadata
            - total_count: Total number of matching users
    """
    try:
        # Extract parameters with defaults
        filters = data.get('filters', {})
        sort_by = data.get('sort_by', 'createdAt')
        sort_order = data.get('sort_order', 'desc')
        page_size = min(data.get('page_size', 20), 100)  # Limit max page size to 100
        page = max(data.get('page', 1), 1)  # Ensure page is at least 1
        
        # Validate sort_by parameter
        valid_sort_fields = ['createdAt', 'last_updated_at']
        if sort_by not in valid_sort_fields:
            sort_by = 'createdAt'
        
        # Validate sort_order parameter (only desc allowed)
        if sort_order != 'desc':
            sort_order = 'desc'
        
        # Extract search query for case-insensitive search
        search_query = None
        if 'query' in filters and filters['query']:
            search_query = filters['query'].strip().lower()
        
        # Start building the query
        users_ref = db.collection('users')
        query = users_ref
        
        # Add condition to ensure createdAt is a number (exists and greater than 0)
        query = query.where('createdAt', '>', 0)
        
        # Apply sorting
        direction = firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING
        query = query.order_by(sort_by, direction=direction)
        
        # Get all documents that match base criteria first
        all_docs = list(query.stream())
        
        # Apply client-side filtering if search query exists
        if search_query:
            filtered_docs = []
            for doc in all_docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                
                # Safe handling of potentially None values
                display_name = (user_data.get('displayName') or '').lower()
                email = (user_data.get('email') or '').lower()
                
                # Check if search query matches displayName or email (case-insensitive)
                if search_query in display_name or search_query in email:
                    filtered_docs.append((doc, user_data))
        else:
            # No filtering needed, use all docs
            filtered_docs = [(doc, {**doc.to_dict(), 'id': doc.id}) for doc in all_docs]
        
        # Calculate pagination on filtered results
        total_count = len(filtered_docs)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        # Get the page of filtered results
        page_docs = filtered_docs[start_index:end_index]
        
        # Process the page documents
        users_list = []
        for doc, user_data in page_docs:
            # Define the fields to return
            allowed_fields = [
                'displayName', 'id', 'email', 'source', 'photoUrl', 
                'meteredBilling', 'method', 'createdAt', 'last_login', 'last_updated_at'
            ]
            
            # Filter user data to only include allowed fields
            filtered_user_data = {}
            for field in allowed_fields:
                if field in user_data:
                    filtered_user_data[field] = user_data[field]
            
            # Convert timestamp fields to readable format if they exist
            for timestamp_field in ['createdAt', 'last_login', 'last_updated_at']:
                if timestamp_field in filtered_user_data and filtered_user_data[timestamp_field]:
                    try:
                        # Handle both Firestore timestamp and Unix timestamp
                        if hasattr(filtered_user_data[timestamp_field], 'timestamp'):
                            filtered_user_data[timestamp_field] = filtered_user_data[timestamp_field].timestamp()
                        elif isinstance(filtered_user_data[timestamp_field], (int, float)):
                            # Already a timestamp
                            pass
                    except Exception:
                        # Keep original value if conversion fails
                        pass
            
            users_list.append(filtered_user_data)
        
        # Prepare pagination metadata
        has_next = end_index < total_count
        pagination_info = {
            'page': page,
            'page_size': page_size,
            'has_next': has_next,
            'total_pages': (total_count + page_size - 1) // page_size
        }
        
        return {
            'users': users_list,
            'pagination': pagination_info,
            'total_count': total_count,
            'filters_applied': filters,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
    except Exception as e:
        # Log the error and return a structured error response
        print(f"Error in get_users_with_pagination: {str(e)}")
        return {
            'error': f'Failed to fetch users: {str(e)}',
            'users': [],
            'pagination': {
                'page': data.get('page', 1),
                'page_size': data.get('page_size', 20),
                'has_next': False,
                'total_pages': 0
            },
            'total_count': 0
        }