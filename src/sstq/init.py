from flask import Flask
from sstq.config import Config
from sstq.extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extension
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # import models 
    from sstq import models

    # register blueprints
    from sstq.routes.admin import admin_bp
    from sstq.routes.auth import auth_bp
    from sstq.routes.helper import helper_bp
    from sstq.routes.home import home_bp
    from sstq.routes.product import product_bp
    from sstq.routes.profile import profile_bp
    from sstq.routes.scan import scan_bp
    from sstq.routes.timeline import timeline_bp
    from sstq.routes.tracequest import tracequest_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(helper_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(tracequest_bp)

    return app