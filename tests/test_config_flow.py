"""Test the Walutomat config flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from walutomat_py import WalutomatAPIError

from custom_components.walutomat.const import DOMAIN


@pytest.fixture
def mock_walutomat_client_setup():
    """Mock the WalutomatClient for config flow tests."""
    with patch("custom_components.walutomat.config_flow.WalutomatClient", autospec=True) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_balances = AsyncMock(return_value=[])
        yield mock_client_class


async def test_form_user_with_api_key(hass: HomeAssistant, mock_walutomat_client_setup: AsyncMock) -> None:
    """Test we get the form and can create an entry with an API key."""
    await setup.async_setup_component(hass, DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: "test-api-key",
            "sandbox": False,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert "Account (...-key)" in result2["title"]
    assert result2["data"] == {
        CONF_API_KEY: "test-api-key",
        "sandbox": False,
    }


async def test_form_user_no_api_key(hass: HomeAssistant, mock_walutomat_client_setup: AsyncMock) -> None:
    """Test we can create an entry without an API key for public rates."""
    await setup.async_setup_component(hass, DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: ""},
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Walutomat Public Rates"
    assert result2["data"] == {
        CONF_API_KEY: "",
        "sandbox": False,
    }
    # Ensure the validation function was not called with an empty key
    mock_walutomat_client_setup.return_value.get_balances.assert_not_called()


async def test_form_user_cannot_connect(hass: HomeAssistant, mock_walutomat_client_setup: AsyncMock) -> None:
    """Test we handle cannot connect error."""
    await setup.async_setup_component(hass, DOMAIN, {})
    mock_walutomat_client_setup.return_value.get_balances.side_effect = WalutomatAPIError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-api-key"},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_user_unknown_exception(hass: HomeAssistant, mock_walutomat_client_setup: AsyncMock) -> None:
    """Test we handle unknown exceptions."""
    await setup.async_setup_component(hass, DOMAIN, {})
    mock_walutomat_client_setup.return_value.get_balances.side_effect = Exception

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-api-key"},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test we can configure options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Check that both interval options are present
    schema = result["data_schema"].schema
    assert "balances_update_interval" in schema
    assert "rates_update_interval" in schema
    assert "currency_pairs" in schema

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "balances_update_interval": 10,
            "rates_update_interval": 2,
            "currency_pairs": ["USD_PLN"],
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "balances_update_interval": 10,
        "rates_update_interval": 2,
        "currency_pairs": ["USD_PLN"],
    }
