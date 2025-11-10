"""Tests for the Walutomat integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.walutomat.const import DOMAIN


@pytest.fixture
def mock_walutomat_client():
    """Mock the WalutomatClient."""
    with patch("custom_components.walutomat.WalutomatClient", autospec=True) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_balances.return_value = [
            {"currency": "PLN", "value": 1000.0},
            {"currency": "EUR", "value": 100.0},
        ]
        # Mock the static method for rates
        mock_client_class.get_public_rate = MagicMock(
            return_value={"buy_rate": 4.5, "sell_rate": 4.6}
        )
        yield mock_client_class


async def test_setup_entry_with_api_key(hass: HomeAssistant, mock_walutomat_client: MagicMock) -> None:
    """Test setting up the integration with an API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_api_key", "sandbox": False},
        options={
            "balances_update_interval": 5,
            "rates_update_interval": 1,
            "currency_pairs": ["EUR_PLN"],
        },
    )
    entry.add_to_hass(hass)

    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # Check that both coordinators are created and stored
    assert "rates_coordinator" in hass.data[DOMAIN]
    assert "balances_coordinator" in hass.data[DOMAIN][entry.entry_id]

    # Check that API calls were made for initial refresh
    mock_walutomat_client.get_public_rate.assert_called_once_with("EUR_PLN")
    mock_walutomat_client.return_value.get_balances.assert_called_once()


async def test_setup_entry_without_api_key(hass: HomeAssistant, mock_walutomat_client: MagicMock) -> None:
    """Test setting up the integration without an API key (for public rates only)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "", "sandbox": False},
        options={"rates_update_interval": 1, "currency_pairs": ["EUR_PLN"]},
    )
    entry.add_to_hass(hass)

    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # Only rates coordinator should exist
    assert "rates_coordinator" in hass.data[DOMAIN]
    # No balances coordinator should be created for this entry
    assert entry.entry_id not in hass.data[DOMAIN]

    # Check that only the public rate API was called
    mock_walutomat_client.get_public_rate.assert_called_once_with("EUR_PLN")
    mock_walutomat_client.return_value.get_balances.assert_not_called()


async def test_unload_entry(hass: HomeAssistant, mock_walutomat_client: MagicMock) -> None:
    """Test unloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test_api_key"},
    )
    entry.add_to_hass(hass)

    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.entry_id in hass.data[DOMAIN]

    # Unload the entry
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    # Entry specific data should be cleaned up
    assert entry.entry_id not in hass.data[DOMAIN]
    # Global rates coordinator might still exist, which is acceptable
    assert "rates_coordinator" in hass.data[DOMAIN]