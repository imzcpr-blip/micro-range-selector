"""Desktop / console alerts when the recommended micro changes."""

from __future__ import annotations

import sys
from typing import Optional

from config import APP_NOTIFY_NAME, PROTOCOL_SHORT


def notify(title: str, message: str) -> None:
    """Best-effort Windows desktop notification + console bell."""
    print(f"\a[{title}] {message}")
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message[:250],
            app_name=APP_NOTIFY_NAME,
            timeout=12,
        )
        return
    except Exception:
        pass

    # Fallback: Windows toast via PowerShell (no extra deps)
    if sys.platform == "win32":
        try:
            import subprocess

            # Escape single quotes for PowerShell
            t = title.replace("'", "''")
            m = message[:200].replace("'", "''")
            app = APP_NOTIFY_NAME.replace("'", "''")
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] > $null; "
                "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$text = $template.GetElementsByTagName('text'); "
                f"$text.Item(0).AppendChild($template.CreateTextNode('{t}')) | Out-Null; "
                f"$text.Item(1).AppendChild($template.CreateTextNode('{m}')) | Out-Null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app}')"
                ".Show($toast);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass


class RecommendationTracker:
    def __init__(self) -> None:
        self.last_key: Optional[str] = None

    def maybe_alert(self, recommended: Optional[str], sit_out: bool, message: str) -> bool:
        key = "SIT_OUT" if sit_out or not recommended else recommended
        if key != self.last_key:
            self.last_key = key
            title = f"{PROTOCOL_SHORT} — Session Pick"
            notify(title, message)
            return True
        return False
