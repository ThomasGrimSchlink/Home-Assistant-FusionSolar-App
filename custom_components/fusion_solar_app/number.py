"""Target SOC setting for manual FusionSolar battery control."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add a locally stored target SOC for a real FusionSolar entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    if runtime.mock_transition:
        return
    async_add_entities([BatteryTargetSOC(entry.entry_id)])


class BatteryTargetSOC(NumberEntity, RestoreEntity):
    """Local setpoint; changing it alone does not send a cloud command."""

    _attr_has_entity_name = True
    _attr_name = "Battery target SOC"
    _attr_icon = "mdi:battery-charging-80"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, entry_id: str) -> None:
        self._attr_unique_id = f"{entry_id}_battery_control_target_soc"
        self._attr_native_value = 80

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous is not None:
            try:
                value = float(previous.state)
                if 1 <= value <= 100 and value.is_integer():
                    self._attr_native_value = int(value)
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        if not 1 <= value <= 100 or not float(value).is_integer():
            raise ValueError("Target SOC must be an integer from 1 to 100")
        self._attr_native_value = int(value)
        self.async_write_ha_state()
