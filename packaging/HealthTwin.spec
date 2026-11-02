# -*- mode: python ; coding: utf-8 -*-
"""康孪生 HealthTwin 桌面版 PyInstaller 打包配置。

构建：python packaging/build.py（内部调用本 spec）
产物：dist/HealthTwin/HealthTwin.exe（onedir，整个文件夹即发行版）
"""
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

project = Path(SPECPATH).resolve().parent

# ---------------- 应用源码作为数据文件（Streamlit 运行时按脚本加载） ----------------
datas = [
    (str(project / "app.py"), "."),
    (str(project / "config.py"), "."),
    (str(project / "knowledge" / "departments.json"), "knowledge"),
    (str(project / ".streamlit" / "config.toml"), ".streamlit"),
]
for pkg_dir in ("core", "twin", "agents", "ui"):
    for py in sorted((project / pkg_dir).glob("*.py")):
        datas.append((str(py), pkg_dir))
# 构建时生成的内置密钥（若存在）
embedded = project / "_embedded_key.py"
if embedded.exists():
    datas.append((str(embedded), "."))

# ---------------- 运行时依赖完整收集（app 源码不参与静态分析，必须显式收集） ----------------
_runtime_pkgs = [
    "streamlit", "altair", "pydeck", "pyarrow",
    "pandas", "numpy", "PIL",
    "langchain", "langchain_core", "langchain_community",
    "langchain_openai", "langchain_text_splitters",
    "openai", "pydantic",
    "jieba", "pypdf", "dotenv",
    "webview", "pythonnet",
]
binaries = []
hiddenimports = ["rank_bm25", "clr"]
for pkg in _runtime_pkgs:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    [str(Path(SPECPATH) / "launcher.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HealthTwin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # 桌面应用：不弹黑窗
    icon=str(Path(SPECPATH) / "app_icon.ico") if (Path(SPECPATH) / "app_icon.ico").exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HealthTwin",
)
