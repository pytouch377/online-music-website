from app import create_app, db
from app.models import Song
import os

def force_delete_test_audio():
    app = create_app()
    
    with app.app_context():
        try:
            # 找到所有测试音频（可能有多个）
            test_songs = Song.query.filter(Song.title.like('%Test Audio%')).all()
            
            if test_songs:
                for song in test_songs:
                    print(f"🗑️ Deleting: {song.title} (ID: {song.id})")
                    
                    # 删除物理文件（如果存在）
                    if song.file_path and os.path.exists(os.path.join('app/static', song.file_path)):
                        os.remove(os.path.join('app/static', song.file_path))
                        print(f"   - Deleted file: {song.file_path}")
                    
                    # 删除数据库记录
                    db.session.delete(song)
                
                db.session.commit()
                print(f"✅ Deleted {len(test_songs)} test audio(s)")
            else:
                print("❌ No test audio found to delete")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    force_delete_test_audio()