import sys
import subprocess


def notify(title: str, message: str):
    """
    Cross-platform notifications that won't crash:
    - macOS: AppleScript (reliable)
    - Windows: win10toast
    - Fallback: no-op
    """
    try:
        if sys.platform == "darwin":
            # macOS: reliable Notification Center via AppleScript
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=False)
            return

        if sys.platform.startswith("win"):
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=5, threaded=True)
            except Exception:
                pass

    except Exception:
        pass