import logging
from .perific import Client, Item, LatestItemPackets, Token
from .perific.client import AuthenticationError

_LOGGER = logging.getLogger(__name__)


class Hub:

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host
        self.client = Client(host)
        self.token: Token = None
        self.username: str = None
        self.password: str = None

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the Perific API and store the token."""
        try:
            self.token = await self.client.authenticate(username, password)
            if not self.token:
                _LOGGER.error("Authentication failed")
                return False
        except Exception as e:
            _LOGGER.error("Error during authentication: %s", e)
            return False
        self.username = username
        self.password = password
        _LOGGER.info("Authentication successful for user: %s", username)
        return True

    async def fetch_devices(self) -> list[Item]:
        """Fetch all items from the account overview."""
        overview = await self.client.getAccountOverview(self.token.token)
        return overview.items

    async def get_sensor_data(self) -> list[LatestItemPackets] | None:
        """Fetch latest meter packets, re-authenticating once on 401."""
        try:
            return await self.client.getLatestPackets(self.token.token)
        except AuthenticationError:
            _LOGGER.warning("Token expired fetching sensor data — re-authenticating")
            if not self.username or not self.password:
                _LOGGER.error("Credentials missing, cannot re-authenticate")
                return None
            await self.authenticate(self.username, self.password)
            return await self.client.getLatestPackets(self.token.token)
        except Exception as e:
            _LOGGER.exception("Unhandled error in get_sensor_data for user '%s': %s", self.username, e)
            return None

    async def get_reporter_settings(self) -> dict | None:
        """Fetch Zaptec reporter settings from /getreporterssettingsforuser.

        Returns the first ZaptecReporter entry's SimpleSettings and
        UserSettings merged as a flat dict, or None if the list is empty.
        Re-authenticates once on 401, matching the pattern used by
        get_sensor_data().
        """
        try:
            return await self.client.getReporterSettings(self.token.token)
        except AuthenticationError:
            _LOGGER.warning("Token expired fetching reporter settings — re-authenticating")
            if not self.username or not self.password:
                _LOGGER.error("Credentials missing, cannot re-authenticate")
                return None
            await self.authenticate(self.username, self.password)
            return await self.client.getReporterSettings(self.token.token)
        except Exception as e:
            _LOGGER.exception("Unhandled error in get_reporter_settings for user '%s': %s", self.username, e)
            return None
