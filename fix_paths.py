#!/usr/bin/env python
"""批量修复数据库中的路径分隔符"""
from app import create_app, db
from app.models import Song

app = create_app()
with app.app_context():
    fixed_count = 0
    for song in Song.query.all():
        if song.file_path and '\\' in song.file_path:
            song.file_path = song.file_path.replace('\\', '/')
            fixed_count += 1
        if song.cover_image and '\\' in song.cover_image:
            song.cover_image = song.cover_image.replace('\\', '/')
            fixed_count += 1
    
    if fixed_count > 0:
        db.session.commit()
        print(f"✅ 成功修复 {fixed_count} 条路径记录")
    else:
        print("✅ 没有需要修复的路径")
