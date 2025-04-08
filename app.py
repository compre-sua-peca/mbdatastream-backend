from flask_jwt_extended import JWTManager
from app import create_app
from flask_cors import CORS

app = create_app()

CORS(app)
jwt = JWTManager(app)

if __name__ == "__main__":
    app.run(debug=True)
