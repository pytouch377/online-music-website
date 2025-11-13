import os
from app import create_app, db
from app.models import User, Song

def add_test_audio():
    app = create_app()
    
    with app.app_context():
        try:
            user = User.query.filter_by(username='demo').first()
            if not user:
                print("Demo user not found, creating...")
                user = User(username='demo', email='demo@example.com')
                user.set_password('demo123')
                db.session.add(user)
                db.session.commit()
            
            # 检查是否已有测试歌曲
            existing_song = Song.query.filter_by(title='Test Audio').first()
            if existing_song:
                print("Test audio already exists")
                return
            
            # 创建一个测试歌曲记录（使用占位符路径）
            test_song = Song(
                title='Test Audio',
                artist='Test Artist',
                album='Test Album',
                genre='Test',
                file_path='uploads/audio/test.mp3',  # 占位符路径
                user_id=user.id,
                visibility='public'
            )
            
            db.session.add(test_song)
            db.session.commit()
            print("✅ Test audio record added")
            print("Note: You'll need to upload a real MP3 file for playback to work")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    add_test_audio()