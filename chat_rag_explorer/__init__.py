from flask import Flask
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from chat_rag_explorer.logging import setup_logging

    setup_logging(app)

    from chat_rag_explorer.routes import main_bp

    app.register_blueprint(main_bp)

    return app
