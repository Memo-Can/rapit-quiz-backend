from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class _SettingsRateThrottle(AnonRateThrottle):
    """Oranı Django ayarından (çalışma zamanında) okur."""

    setting_name = ""

    def get_rate(self):
        return getattr(settings, self.setting_name)


class SessionStartThrottle(_SettingsRateThrottle):
    scope = "session_start"
    setting_name = "THROTTLE_SESSION_START"


class ScoreSubmitThrottle(_SettingsRateThrottle):
    scope = "score_submit"
    setting_name = "THROTTLE_SCORE_SUBMIT"
