from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "ahsdgfkjaghdfkj"

    from .views import views
    from .AboutModel import AboutModel

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(AboutModel, url_prefix="/")

    return app
