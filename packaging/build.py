"""
康孪生 HealthTwin 桌面版一键构建脚本

用法（在项目根目录）：
    python packaging/build.py

流程：
  1. 读取 DeepSeek Key（系统环境变量 > .env），生成 _embedded_key.py 烧录进 exe
  2. 生成图标 -> PyInstaller 打包（onedir）
  3. 在 dist/HealthTwin/ 写入用户使用说明
  4. 压缩为 dist/HealthTwin-win64.zip —— 发这个文件给用户即可
"""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

project = Path(__file__).resolve().parent.parent
packaging = project / "packaging"
dist = project / "dist"
release_dir = dist / "HealthTwin"


def read_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        env_file = project / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    return key


def run(cmd, **kw):
    print(">", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, cwd=str(project), **kw)


def ensure_deps():
    """缺什么装什么；网络不好时允许使用已就位的依赖继续。"""
    import importlib.util

    needed = {"PyInstaller": "pyinstaller>=6.6", "webview": "pywebview>=5.0", "PIL": "pillow>=10.0"}
    missing = [spec for mod, spec in needed.items() if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    mirrors = [
        [],  # 默认源
        ["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
        ["-i", "https://mirrors.aliyun.com/pypi/simple/"],
    ]
    for extra in mirrors:
        try:
            run([sys.executable, "-m", "pip", "install", "-q", *extra, *missing])
            return
        except subprocess.CalledProcessError:
            continue
    raise SystemExit("打包依赖安装失败（网络问题），请手动安装：" + ", ".join(missing))


def main():
    # 1. 烧录密钥（只打印掩码）
    key = read_key()
    if not key:
        print("[警告] 未找到 DEEPSEEK_API_KEY（环境变量或 .env），打包出的版本 AI 未开通")
    else:
        masked = key[:6] + "..." + key[-4:] if len(key) > 12 else "(已配置)"
        print(f"[密钥] 将烧录进发行版：{masked}")
    (project / "_embedded_key.py").write_text(
        '"""构建时自动生成：内置发行密钥（勿提交到 git）"""\n'
        f'DEEPSEEK_API_KEY = "{key}"\n',
        encoding="utf-8",
    )

    # 2. 依赖 + 图标 + 打包
    ensure_deps()
    run([sys.executable, str(packaging / "make_icon.py")])
    run([sys.executable, "-m", "PyInstaller", str(packaging / "HealthTwin.spec"),
         "--noconfirm", "--clean"])

    # 4. 用户使用说明（面向完全不懂电脑的用户）
    (release_dir / "使用说明.txt").write_text(
        "康孪生 HealthTwin —— 个人健康管理系统\n"
        "=====================================\n"
        "\n"
        "怎么用：\n"
        "  1. 双击 HealthTwin.exe，等几秒钟会自动弹出应用窗口\n"
        "     （首次启动或杀毒软件扫描时可能等 10-20 秒，属正常）\n"
        "  2. 用完直接关窗口即可，所有数据自动保存在本机\n"
        "  3. AI 功能已内置开通，不需要设置任何东西\n"
        "\n"
        "数据在哪：\n"
        "  你的健康档案、血压血糖等记录，全部保存在本文件夹的 data 目录里，\n"
        "  不上传任何服务器。换电脑时把整个文件夹拷走即可。\n"
        "\n"
        "打不开怎么办：\n"
        "  - 等 30 秒再试一次\n"
        "  - 如果杀毒软件提示，选择「允许运行」（本软件不联网上传你的数据，\n"
        "    仅在你使用 AI 功能时把问题发给 DeepSeek 官方接口生成回答）\n"
        "  - 仍不行请联系提供者\n",
        encoding="utf-8",
    )

    # 5. 压缩发行包
    zip_path = dist / "HealthTwin-win64.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(release_dir.rglob("*")):
            zf.write(p, p.relative_to(dist))
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"\n[完成] 发行包：{zip_path}（{size_mb:.0f} MB）")
    print(f"[完成] 文件夹版：{release_dir}")


if __name__ == "__main__":
    main()
