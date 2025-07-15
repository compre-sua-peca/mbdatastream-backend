from functools import wraps
import os
from flask import request, jsonify


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('API-Key')
        
        if not api_key:
            return jsonify({"error": "API key is required"}), 401
        
        # Validate API key
        if not is_valid_api_key(api_key):
            return jsonify({"error": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def is_valid_api_key(api_key):
    return api_key == os.environ.get("API_TOKEN")