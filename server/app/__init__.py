"""
Vhub Admin Backend API Blueprint Configuration

This module sets up the main API blueprint and registers all namespace APIs
for the Vhub Admin Backend. It uses Flask-RESTPlus for Swagger documentation
and organizes endpoints into logical namespaces by business domain.

The API is versioned and includes comprehensive Swagger documentation
accessible at /vedasis/swagger/ endpoint.
"""

from flask_restplus import Api
from flask import Blueprint

# Import all API namespaces

from .main.apis.email import api as api_email


# Create main API blueprint with versioned URL prefix
blueprint = Blueprint('api', __name__, url_prefix="/vedasis")

# Configure Swagger API documentation
api = Api(
    blueprint, 
    version='1.0', 
    title='Vedasis Search Engine',
    description='Vhub Admin Backend API - Comprehensive platform for managing influencers, campaigns, and social media data',
    doc='/swagger/',
    authorizations={
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Firebase JWT token for authentication'
        }
    },
)



# email APIs
api.add_namespace(api_email, path='/email')  # Email handling APIs


