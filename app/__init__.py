from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
babel = Babel()
csrf = CSRFProtect()

def get_locale():
    # 优先使用session中的语言设置
    if 'language' in session:
        return session['language']
    # 其次使用浏览器语言偏好
    return request.accept_languages.best_match(['zh', 'en']) or 'en'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    csrf.init_app(app)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    @app.context_processor
    def inject_locale():
        locale = get_locale()
        return {'current_locale': locale}
    
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    return app