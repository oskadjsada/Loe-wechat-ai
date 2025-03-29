# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('config.json', '.'),
    ('bot/', 'bot'),
    ('channel/', 'channel'),
    ('common/', 'common'),
    ('app_icons.py', '.'),
    ('b_2c9004e0db255943ebd53561315853a5.jpg', '.')  # 确保图标文件被打包
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['win32gui', 'win32con', 'win32api', 'pystray', 'PIL.Image', 'win32com', 'win32com.client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wechat-deepseek',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # 移除显式图标设置，使用代码中的内置图标
) 