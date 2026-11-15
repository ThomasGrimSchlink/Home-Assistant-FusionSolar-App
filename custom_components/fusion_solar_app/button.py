"""Manual battery control buttons using the tested V2 services."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add manual buttons only for real connected entries."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    if runtime.mock_transition:
        return
    async_add_entities([BatteryCommandButton(entry.entry_id, action) for action in ("charge", "discharge", "stop")])


class BatteryCommandButton(ButtonEntity):
    """Send a command through the existing V2 action implementation."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, action: str) -> None:
        self._entry_id = entry_id
        self._action = action
        self._attr_unique_id = f"{entry_id}_battery_control_{action}"
        self._attr_name = f"Battery {action}"
        self._attr_icon = {
            "charge": "mdi:battery-arrow-up",
            "discharge": "mdi:battery-arrow-down",
            "stop": "mdi:stop-circle-outline",
        }[action]

    async def async_press(self) -> None:
        payload = {"config_entry_id": self._entry_id}
        if self._action != "stop":
            registry = er.async_get(self.hass)
            unique_id = f"{self._entry_id}_battery_control_target_soc"
            entity_id = registry.async_get_entity_id("number", DOMAIN, unique_id)
            if not entity_id:
                raise HomeAssistantError("Battery target SOC entity not found")
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                raise HomeAssistantError("Battery target SOC is unavailable")
            try:
                target = float(state.state)
            except (TypeError, ValueError) as err:
                raise HomeAssistantError("Invalid battery target SOC") from err
            if not 1 <= target <= 100 or not target.is_integer():
                raise HomeAssistantError("Target SOC must be an integer from 1 to 100")
            payload["target_soc"] = int(target)
            power_id = registry.async_get_entity_id(
                "number", DOMAIN, f"{self._entry_id}_battery_control_target_power"
            )
            if not power_id:
                raise HomeAssistantError("Battery target power entity not found")
            power_state = self.hass.states.get(power_id)
            if power_state is None or power_state.state in ("unknown", "unavailable"):
                raise HomeAssistantError("Battery target power is unavailable")
            from decimal import Decimal, InvalidOperation
            try:
                power = Decimal(power_state.state)
            except (InvalidOperation, ValueError) as err:
                raise HomeAssistantError("Invalid battery target power") from err
            if not power.is_finite() or not Decimal("0.001") <= power <= Decimal("5") or power != power.quantize(Decimal("0.001")):
                raise HomeAssistantError("Target power must be between 0.001 and 5.000 kW")
            payload["target_power"] = float(power)
        await self.hass.services.async_call(
            DOMAIN, f"battery_{self._action}", payload, blocking=True
        )
