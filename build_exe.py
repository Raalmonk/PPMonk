import PyInstaller.__main__
import os
import shutil

def build():
    # Clean previous build
    if os.path.exists('build'): shutil.rmtree('build')
    if os.path.exists('dist'): shutil.rmtree('dist')

    # Define assets separator
    sep = ';' if os.name == 'nt' else ':'

    spec_content = r"""
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

datas = []
binaries = []
hiddenimports = []

# Collect packages with known DLL issues or hidden imports
packages_to_collect = [
    'customtkinter',
    'torch',
    'sb3_contrib',
    'stable_baselines3',
    'gymnasium',
    'pandas',
    'numpy',
    'PIL'
]

for pkg in packages_to_collect:
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception as e:
        print(f"Warning: could not collect {pkg}: {e}")

# Add manual assets
# Assume running from repo root
datas += [('assets', 'assets')]

block_cipher = None

a = Analysis(
    ['ui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='PPMonkSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

    with open('PPMonk_Sim.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("Running PyInstaller...")
    # Run PyInstaller with the generated spec file
    PyInstaller.__main__.run([
        'PPMonk_Sim.spec',
        '--clean',
        '--noconfirm'
    ])

if __name__ == "__main__":
    build()
