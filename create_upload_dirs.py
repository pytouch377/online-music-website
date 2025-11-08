import os

def create_upload_directories():
    """创建上传所需的目录结构"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dirs = [
        os.path.join(base_dir, 'app', 'static', 'uploads', 'audio'),
        os.path.join(base_dir, 'app', 'static', 'uploads', 'covers')
    ]
    
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    print("✅ Upload directory structure created successfully!")

if __name__ == '__main__':
    create_upload_directories()