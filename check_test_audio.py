from app import create_app, db
from app.models import Song, User

def check_test_audio():
    app = create_app()
    
    with app.app_context():
        try:
            # 找到测试音频
            test_song = Song.query.filter_by(title='Test Audio').first()
            if test_song:
                owner = User.query.get(test_song.user_id)
                print(f"🎵 Test Audio Info:")
                print(f"   - ID: {test_song.id}")
                print(f"   - Title: {test_song.title}")
                print(f"   - Owner: {owner.username} (ID: {owner.id})")
                print(f"   - Visibility: {test_song.visibility}")
                print(f"   - File Path: {test_song.file_path}")
            else:
                print("❌ Test audio not found in database")
                
            # 列出所有歌曲
            print("\n📋 All songs in database:")
            songs = Song.query.all()
            for song in songs:
                owner = User.query.get(song.user_id)
                print(f"   - {song.title} (by {owner.username}, visibility: {song.visibility})")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_test_audio()