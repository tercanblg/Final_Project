from plyer import notification
from static import icon_path
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.notifications_enabled = True

    def show_notification(self, title, message):
        if self.notifications_enabled:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_icon=icon_path,
                    timeout=10,
                )
                logger.info(f"Notification shown: {title} - {message}")
            except Exception:
                logger.error("Error showing notification")

    def disable_notifications(self):
        self.notifications_enabled = False

    def enable_notifications(self):
        self.notifications_enabled = True