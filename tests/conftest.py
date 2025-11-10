"""Global fixtures for Walutomat integration tests."""
import pytest
from pytest_homeassistant_custom_component.common import patch

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent notifications.
# @see https://github.com/home-assistant/core/blob/dev/homeassistant/components/persistent_notification/__init__.py#L126
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield
