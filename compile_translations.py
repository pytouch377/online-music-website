#!/usr/bin/env python
import os
import sys

def compile_po_files():
    """手动编译.po文件为.mo文件"""
    import polib
    
    translations_dir = os.path.join('app', 'translations')
    
    for lang in os.listdir(translations_dir):
        lang_dir = os.path.join(translations_dir, lang, 'LC_MESSAGES')
        po_file = os.path.join(lang_dir, 'messages.po')
        mo_file = os.path.join(lang_dir, 'messages.mo')
        
        if os.path.exists(po_file):
            try:
                po = polib.pofile(po_file)
                po.save_as_mofile(mo_file)
                print(f"Compiled {po_file} -> {mo_file}")
            except Exception as e:
                print(f"Error compiling {po_file}: {e}")

if __name__ == '__main__':
    try:
        import polib
    except ImportError:
        print("Installing polib...")
        os.system("pip install polib")
        import polib
    
    compile_po_files()