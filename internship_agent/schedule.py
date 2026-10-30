"""只生成 macOS 定时任务文件，不安装或启动任何后台任务。"""
import plistlib
import sys
from pathlib import Path

from .llm import ROOT


def template(root, hour, minute, send=False):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "-m", "internship_agent", "--data-dir", str(root), "daily"]
    if send:
        args.append("--send")
    value = {"Label": "local.internship-radar.daily", "ProgramArguments": args,
             "WorkingDirectory": str(ROOT), "StartCalendarInterval": {"Hour": hour, "Minute": minute},
             "StandardOutPath": str(root / "daily.stdout.log"),
             "StandardErrorPath": str(root / "daily.stderr.log")}
    path = root / "local.internship-radar.daily.plist"
    # 不覆盖已有调度配置。
    with path.open("xb") as stream:
        plistlib.dump(value, stream)
    path.chmod(0o600)
    return path
