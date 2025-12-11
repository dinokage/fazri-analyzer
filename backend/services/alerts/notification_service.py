"""
Notification Service for sending alerts through multiple channels.
Supports email, SMS, and push notifications with queue-based processing.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db.alerts import (
    Alert,
    StaffProfile,
    NotificationQueue,
    NotificationLog,
    NotificationChannel,
    NotificationStatus,
)
from config import settings

logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationService:
    """
    Service for managing and sending notifications.

    Handles:
    - Queuing notifications for delivery
    - Processing notification queue
    - Logging delivery status
    - Respecting staff contact preferences
    """

    def __init__(self, db: Session):
        self.db = db
        self.providers: Dict[NotificationChannel, 'BaseNotificationProvider'] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize notification providers based on configuration"""
        if settings.EMAIL_ENABLED:
            self.providers[NotificationChannel.EMAIL] = EmailProvider()
        if settings.SMS_ENABLED:
            self.providers[NotificationChannel.SMS] = SMSProvider()
        if settings.PUSH_ENABLED:
            self.providers[NotificationChannel.PUSH] = PushProvider()

        logger.info(f"Initialized notification providers: {list(self.providers.keys())}")

    def queue_notification(
        self,
        staff_id: UUID,
        alert_id: UUID,
        channel: NotificationChannel,
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationQueue:
        """
        Queue a notification for delivery.

        Args:
            staff_id: Target staff member
            alert_id: Related alert
            channel: Delivery channel (email, sms, push)
            subject: Notification subject/title
            message: Notification body
            priority: Delivery priority
            metadata: Additional data for the notification

        Returns:
            Created notification queue entry
        """
        from models.db.alerts import AlertSeverity

        # Map priority to AlertSeverity enum (used by the model)
        priority_map = {
            NotificationPriority.LOW: AlertSeverity.LOW,
            NotificationPriority.NORMAL: AlertSeverity.MEDIUM,
            NotificationPriority.HIGH: AlertSeverity.HIGH,
            NotificationPriority.CRITICAL: AlertSeverity.CRITICAL,
        }

        notification = NotificationQueue(
            recipient_id=staff_id,
            alert_id=alert_id,
            channel=channel,
            title=subject,
            body=message,
            priority=priority_map.get(priority, AlertSeverity.MEDIUM),
            data=metadata or {},
            status=NotificationStatus.PENDING,
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        logger.info(f"Queued {channel.value} notification for staff {staff_id}, alert {alert_id}")
        return notification

    def notify_staff_of_assignment(
        self,
        staff: StaffProfile,
        alert: Alert,
        is_critical: bool = False,
    ) -> List[NotificationQueue]:
        """
        Send notifications to staff about a new alert assignment.
        Respects staff contact preferences.

        Args:
            staff: Staff member being notified
            alert: The assigned alert
            is_critical: Whether this is a critical priority notification

        Returns:
            List of queued notifications
        """
        queued = []
        priority = NotificationPriority.CRITICAL if is_critical else NotificationPriority.HIGH

        # Build notification content
        subject = self._build_assignment_subject(alert)
        message = self._build_assignment_message(alert)

        preferences = staff.contact_preferences or {}

        # Queue notifications based on staff preferences
        if preferences.get("email", True) and NotificationChannel.EMAIL in self.providers:
            notif = self.queue_notification(
                staff_id=staff.id,
                alert_id=alert.id,
                channel=NotificationChannel.EMAIL,
                subject=subject,
                message=message,
                priority=priority,
                metadata={"alert_severity": alert.severity.value, "zone_id": (alert.location or {}).get("zone_id")},
            )
            queued.append(notif)

        if preferences.get("sms", True) and NotificationChannel.SMS in self.providers:
            # SMS gets shorter message
            sms_message = self._build_sms_message(alert)
            notif = self.queue_notification(
                staff_id=staff.id,
                alert_id=alert.id,
                channel=NotificationChannel.SMS,
                subject=subject,
                message=sms_message,
                priority=priority,
                metadata={"alert_severity": alert.severity.value},
            )
            queued.append(notif)

        if preferences.get("push", True) and NotificationChannel.PUSH in self.providers:
            notif = self.queue_notification(
                staff_id=staff.id,
                alert_id=alert.id,
                channel=NotificationChannel.PUSH,
                subject=subject,
                message=message[:200],  # Push notifications are short
                priority=priority,
                metadata={"alert_id": str(alert.id), "action": "view_alert"},
            )
            queued.append(notif)

        return queued

    def notify_escalation(
        self,
        staff: StaffProfile,
        alert: Alert,
        escalation_reason: str,
    ) -> List[NotificationQueue]:
        """
        Send escalation notifications to staff.

        Args:
            staff: Staff member receiving escalation
            alert: The escalated alert
            escalation_reason: Why the alert was escalated

        Returns:
            List of queued notifications
        """
        queued = []

        subject = f"ESCALATED: {alert.title}"
        message = self._build_escalation_message(alert, escalation_reason)

        preferences = staff.contact_preferences or {}

        # Always send email for escalations
        if NotificationChannel.EMAIL in self.providers:
            notif = self.queue_notification(
                staff_id=staff.id,
                alert_id=alert.id,
                channel=NotificationChannel.EMAIL,
                subject=subject,
                message=message,
                priority=NotificationPriority.CRITICAL,
                metadata={"escalation_reason": escalation_reason},
            )
            queued.append(notif)

        # SMS for escalations if enabled
        if preferences.get("sms", True) and NotificationChannel.SMS in self.providers:
            sms_message = f"ESCALATED ALERT: {alert.title}. {escalation_reason}. Immediate response required."
            notif = self.queue_notification(
                staff_id=staff.id,
                alert_id=alert.id,
                channel=NotificationChannel.SMS,
                subject=subject,
                message=sms_message,
                priority=NotificationPriority.CRITICAL,
            )
            queued.append(notif)

        return queued

    def process_queue(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Process pending notifications in the queue.

        Args:
            batch_size: Maximum notifications to process

        Returns:
            Dictionary with processing results
        """
        results = {"sent": 0, "failed": 0, "skipped": 0}

        # Get pending notifications ordered by priority and creation time
        pending = (
            self.db.query(NotificationQueue)
            .filter(NotificationQueue.status == NotificationStatus.PENDING)
            .order_by(
                NotificationQueue.priority.desc(),
                NotificationQueue.created_at.asc()
            )
            .limit(batch_size)
            .all()
        )

        for notification in pending:
            try:
                success = self._send_notification(notification)
                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()
                    results["sent"] += 1
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.retry_count += 1
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing notification {notification.id}: {e}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
                notification.retry_count += 1
                results["failed"] += 1

        self.db.commit()
        logger.info(f"Processed notification queue: {results}")
        return results

    def _send_notification(self, notification: NotificationQueue) -> bool:
        """
        Send a single notification through the appropriate provider.

        Args:
            notification: The notification to send

        Returns:
            True if sent successfully
        """
        provider = self.providers.get(notification.channel)
        if not provider:
            logger.warning(f"No provider for channel {notification.channel}")
            return False

        # Get staff details for sending
        staff = self.db.query(StaffProfile).get(notification.recipient_id)
        if not staff:
            logger.error(f"Staff {notification.recipient_id} not found")
            return False

        # Send through provider
        success = provider.send(
            recipient=staff,
            subject=notification.title,
            message=notification.body,
            metadata=notification.data,
        )

        # Log the delivery attempt
        self._log_notification(notification, staff, success)

        return success

    def _log_notification(
        self,
        notification: NotificationQueue,
        staff: StaffProfile,
        success: bool,
    ):
        """Log notification delivery attempt"""
        log = NotificationLog(
            notification_id=notification.id,
            recipient_id=staff.id,
            channel=notification.channel,
            recipient_address=self._get_recipient_address(staff, notification.channel),
            status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
            sent_at=datetime.utcnow() if success else None,
        )
        self.db.add(log)

    def _get_recipient_address(self, staff: StaffProfile, channel: NotificationChannel) -> str:
        """Get recipient address based on channel"""
        if channel == NotificationChannel.EMAIL:
            return staff.email
        elif channel == NotificationChannel.SMS:
            return staff.phone or ""
        elif channel == NotificationChannel.PUSH:
            return f"push:{staff.id}"
        return ""

    def _build_assignment_subject(self, alert: Alert) -> str:
        """Build notification subject for alert assignment"""
        severity_prefix = {
            "critical": "CRITICAL ALERT",
            "high": "HIGH PRIORITY",
            "medium": "ALERT",
            "low": "Notice",
        }
        prefix = severity_prefix.get(alert.severity.value, "ALERT")
        return f"{prefix}: {alert.title}"

    def _build_assignment_message(self, alert: Alert) -> str:
        """Build full notification message for alert assignment"""
        location = alert.location or {}
        building = location.get("building", "Unknown")
        zone_id = location.get("zone_id", "Unknown")

        return f"""You have been assigned to respond to an alert.

Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Location: {building}, Zone {zone_id}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Description:
{alert.description}

Please acknowledge this alert and respond immediately.

---
Fazri Security System
"""

    def _build_sms_message(self, alert: Alert) -> str:
        """Build short SMS message for alert assignment"""
        zone_id = (alert.location or {}).get("zone_id", "Unknown")
        return f"FAZRI ALERT [{alert.severity.value.upper()}]: {alert.title}. Location: {zone_id}. Respond immediately."

    def _build_escalation_message(self, alert: Alert, reason: str) -> str:
        """Build escalation notification message"""
        location = alert.location or {}
        building = location.get("building", "Unknown")
        zone_id = location.get("zone_id", "Unknown")

        return f"""ESCALATED ALERT - Immediate Response Required

Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Location: {building}, Zone {zone_id}
Escalation Reason: {reason}
Escalation Count: {alert.escalation_count}

Description:
{alert.description}

This alert has been escalated to you due to {reason}. Please respond immediately.

---
Fazri Security System
"""

    def get_notification_history(
        self,
        staff_id: Optional[UUID] = None,
        alert_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[NotificationLog]:
        """
        Get notification history with optional filters.

        Args:
            staff_id: Filter by staff member
            alert_id: Filter by alert
            limit: Maximum records to return

        Returns:
            List of notification logs
        """
        query = self.db.query(NotificationLog)

        if staff_id:
            query = query.filter(NotificationLog.staff_id == staff_id)
        if alert_id:
            query = query.filter(NotificationLog.alert_id == alert_id)

        return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current notification queue status"""
        from sqlalchemy import func

        pending = self.db.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == NotificationStatus.PENDING
        ).scalar()

        failed = self.db.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == NotificationStatus.FAILED
        ).scalar()

        sent_today = self.db.query(func.count(NotificationLog.id)).filter(
            and_(
                NotificationLog.status == NotificationStatus.SENT,
                NotificationLog.sent_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            )
        ).scalar()

        return {
            "pending": pending,
            "failed": failed,
            "sent_today": sent_today,
            "providers_enabled": [c.value for c in self.providers.keys()],
        }


class BaseNotificationProvider:
    """Base class for notification providers"""

    def send(
        self,
        recipient: StaffProfile,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification. Override in subclasses."""
        raise NotImplementedError


class EmailProvider(BaseNotificationProvider):
    """Email notification provider"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_address = settings.EMAIL_FROM_ADDRESS

    def send(
        self,
        recipient: StaffProfile,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send email notification"""
        if not recipient.email:
            logger.warning(f"No email for staff {recipient.id}")
            return False

        # In demo/mock mode, just log the email
        if settings.NOTIFICATION_MOCK_MODE:
            logger.info(f"[MOCK EMAIL] To: {recipient.email}, Subject: {subject}")
            return True

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = recipient.email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipient.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient.email}: {e}")
            return False


class SMSProvider(BaseNotificationProvider):
    """SMS notification provider (Twilio-compatible)"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER

    def send(
        self,
        recipient: StaffProfile,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send SMS notification"""
        if not recipient.phone:
            logger.warning(f"No phone for staff {recipient.id}")
            return False

        # In demo/mock mode, just log the SMS
        if settings.NOTIFICATION_MOCK_MODE:
            logger.info(f"[MOCK SMS] To: {recipient.phone}, Message: {message[:100]}...")
            return True

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)
            sms = client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient.phone
            )

            logger.info(f"SMS sent to {recipient.phone}, SID: {sms.sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {recipient.phone}: {e}")
            return False


class PushProvider(BaseNotificationProvider):
    """Push notification provider (Firebase-compatible)"""

    def __init__(self):
        self.firebase_credentials = settings.FIREBASE_CREDENTIALS_PATH
        self._initialized = False

    def _init_firebase(self):
        """Lazy initialization of Firebase"""
        if self._initialized:
            return

        if settings.NOTIFICATION_MOCK_MODE:
            self._initialized = True
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            if self.firebase_credentials:
                cred = credentials.Certificate(self.firebase_credentials)
                firebase_admin.initialize_app(cred)
                self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

    def send(
        self,
        recipient: StaffProfile,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send push notification"""
        # In demo/mock mode, just log the push
        if settings.NOTIFICATION_MOCK_MODE:
            logger.info(f"[MOCK PUSH] To: {recipient.name}, Title: {subject}")
            return True

        self._init_firebase()

        try:
            from firebase_admin import messaging

            # Get device token from staff profile (would be stored in contact_preferences)
            device_token = (recipient.contact_preferences or {}).get("device_token")
            if not device_token:
                logger.warning(f"No device token for staff {recipient.id}")
                return False

            notification = messaging.Message(
                notification=messaging.Notification(
                    title=subject,
                    body=message,
                ),
                data=metadata or {},
                token=device_token,
            )

            response = messaging.send(notification)
            logger.info(f"Push sent to {recipient.name}, Response: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send push to {recipient.name}: {e}")
            return False
