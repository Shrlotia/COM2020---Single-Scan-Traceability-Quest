from flask import Flask
from sstq.config import Config
from sstq.extensions import db, login_manager

def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

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
    from sstq.routes.scan_barcode import scan_barcode_bp
    from sstq.routes.scan_picture import scan_picture_bp
    from sstq.routes.search_product import search_product_bp
    from sstq.routes.timeline import timeline_bp
    from sstq.routes.tracequest import tracequest_bp
    from sstq.routes.misson import misson_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(helper_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(scan_barcode_bp)
    app.register_blueprint(scan_picture_bp)
    app.register_blueprint(search_product_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(tracequest_bp)
    app.register_blueprint(misson_bp)

    with app.app_context():
        db.create_all()

    return app
