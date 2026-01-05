import flask
from flask_cors import CORS
from app import blueprint
# Create Flask application instance
app = flask.Flask(__name__)
# Flask Configuration
app.config["DEBUG"] = True  # Enable debug mode for development
app.config['JSON_SORT_KEYS'] = False  # Preserve JSON key order for consistent API responses
# Enable Cross-Origin Resource Sharing for frontend integration
CORS(app)
# Register the main API blueprint with all namespace routes
app.register_blueprint(blueprint)
if __name__ == "__main__":
    # Run the application in debug mode for development
    # In production, this should be served by a WSGI server like gunicorn
    app.run(debug=True)
