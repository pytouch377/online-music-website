from app import create_app, db
from app.models import User

def create_user():
    app = create_app()
    
    with app.app_context():
        # 删除已存在的测试用户（可选）
        existing_user = User.query.filter_by(username='demo').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
            print("Removed existing demo user")
        
        # 创建新用户
        user = User(username='demo', email='demo@example.com')
        user.set_password('demo123')
        db.session.add(user)
        db.session.commit()
        
        print("✅ Demo user created successfully!")
        print("Username: demo")
        print("Password: demo123")
        print("Email: demo@example.com")

if __name__ == '__main__':
    create_user()