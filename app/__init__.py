from flask import Flask
from config import Config


app = Flask(__name__)
app.config.from_object(Config)

from app.routes import bp as routes_bp
app.register_blueprint(routes_bp)
