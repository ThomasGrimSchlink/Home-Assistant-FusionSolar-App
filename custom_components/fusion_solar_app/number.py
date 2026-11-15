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
    async_add_entities([BatteryTargetSOC(entry.entry_id), BatteryTargetPower(entry.entry_id)])


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


class BatteryTargetPower(NumberEntity, RestoreEntity):
    """Local power setpoint in kW; sent only when charge/discharge is pressed."""

    _attr_has_entity_name = True
    _attr_name = "Battery target power"
    _attr_icon = "mdi:flash"
    _attr_native_min_value = 0.001
    _attr_native_max_value = 5.0
    _attr_native_step = 0.001
    _attr_native_unit_of_measurement = "kW"
    _attr_mode = NumberMode.BOX

    def __init__(self, entry_id: str) -> None:
        self._attr_unique_id = f"{entry_id}_battery_control_target_power"
        self._attr_native_value = 2.5

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous is not None:
            try:
                value = float(previous.state)
                if 0.001 <= value <= 5.0 and round(value * 1000) == value * 1000:
                    self._attr_native_value = value
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        from decimal import Decimal
        power = Decimal(str(value))
        if not power.is_finite() or not Decimal("0.001") <= power <= Decimal("5") or power != power.quantize(Decimal("0.001")):
            raise ValueError("Target power must be between 0.001 and 5.000 kW in 0.001 kW steps")
        self._attr_native_value = float(power)
        self.async_write_ha_state()
