# Shore Power Connection Guide

This guide explains how to build electric power systems with shore power connections in FEEMS.

## What is Shore Power?

Shore power (also called "cold ironing" or "alternative maritime power") allows ships to shut down their auxiliary engines and connect to land-based electrical power while at berth. This eliminates fuel consumption and reduces emissions in port areas.

## Benefits of Shore Power

- **Zero fuel consumption** while connected
- **Zero emissions** (CO2, NOx, SOx, PM) at berth
- **Reduced noise** pollution
- **Lower operational costs** in many ports
- **Compliance** with environmental regulations

## Basic Shore Power Connection

The simplest shore power connection requires three parameters:

```python
from feems.components_model.component_electric import ShorePowerConnection
from feems.types_for_feems import Power_kW, SwbId

shore_power = ShorePowerConnection(
    name="Shore Power",
    rated_power=Power_kW(1000),      # 1 MW capacity
    switchboard_id=SwbId(1)          # Connect to switchboard 1
)
```

This creates a power source that can supply up to 1000 kW to the ship's electrical system.

## Shore Power System with Converter

In real installations, shore power typically includes a converter to match voltage and frequency:

```python
from feems.components_model.component_electric import (
    ElectricComponent,
    ShorePowerConnection,
    ShorePowerConnectionSystem,
)
from feems.types_for_feems import TypeComponent, TypePower
import numpy as np

# 1. Create the shore connection
shore_connection = ShorePowerConnection(
    name="Shore Power Connection",
    rated_power=Power_kW(1200),
    switchboard_id=SwbId(1)
)

# 2. Create a converter (for voltage/frequency matching)
converter = ElectricComponent(
    type_=TypeComponent.POWER_CONVERTER,
    name="Shore Power Converter",
    rated_power=Power_kW(1200),
    power_type=TypePower.POWER_TRANSMISSION,
    switchboard_id=SwbId(1),
    # Efficiency curve: [load%, efficiency]
    eff_curve=np.array([
        [0.25, 0.5, 0.75, 1.0],
        [0.96, 0.97, 0.98, 0.98]
    ]).T
)

# 3. Combine into a shore power system
shore_power_system = ShorePowerConnectionSystem(
    name="Shore Power System",
    shore_power_connection=shore_connection,
    converter=converter,
    switchboard_id=SwbId(1)
)
```

The converter accounts for efficiency losses during power conversion (typically 96-98% efficient).

## Complete System Example

Here's how to create a complete system with shore power and backup gensets:

```python
from feems.system_model import ElectricPowerSystem

# Create components (shore power, gensets, loads)
components = [
    shore_power_system,  # Primary power at berth
    genset_1,           # Backup/sea operation
    genset_2,           # Backup/sea operation
    auxiliary_load      # Hotel loads
]

# Create the power system
power_system = ElectricPowerSystem(
    name="Ship Power System",
    power_plant_components=components,
    bus_tie_connections=[]  # Single bus configuration
)
```

## Running Simulations

### Shore Power Operation (at berth)

```python
import numpy as np
from feems.types_for_feems import TypePower
from feems.system_model import IntegrationMethod

n_points = 100  # Simulation time points

# Set load profile
load_profile = 200 + 100 * np.random.random(n_points)  # 200-300 kW
power_system.set_power_input_from_power_output_by_switchboard_id_type_name(
    power_output=load_profile,
    switchboard_id=1,
    type_=TypePower.POWER_CONSUMER,
    name="Auxiliary Load"
)

# Set power source status: Shore ON, Gensets OFF
shore_on = np.ones([n_points, 1]).astype(bool)    # Shore power ON
genset1_off = np.zeros([n_points, 1]).astype(bool)  # Genset 1 OFF
genset2_off = np.zeros([n_points, 1]).astype(bool)  # Genset 2 OFF

status = np.hstack([shore_on, genset1_off, genset2_off])
power_system.set_status_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    status=status
)

# Set load sharing (0 = equal sharing among active sources)
load_sharing = np.zeros([n_points, 3])
power_system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    load_sharing_mode=load_sharing
)

# Run simulation
power_system.set_time_interval(60, integration_method=IntegrationMethod.simpson)
power_system.do_power_balance_calculation()

# Get results
result = power_system.get_fuel_energy_consumption_running_time()
```

### Results Interpretation

```python
# Fuel consumption (should be 0 with shore power)
fuel_kg = result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction

# CO2 emissions (should be 0 with shore power)
co2_kg = result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel

# Running hours
genset_hours = result.running_hours_genset_total_hr

print(f"Fuel consumption: {fuel_kg:.2f} kg")
print(f"CO2 emissions: {co2_kg:.2f} kg")
print(f"Genset running hours: {genset_hours:.2f} hr")
```

## Transition Scenarios

### Arrival at Port (Genset → Shore Power)

```python
# Transition point (e.g., at 60% of simulation)
transition = int(n_points * 0.6)

# Status before transition: Genset ON
# Status after transition: Shore power ON
shore_status = np.zeros([n_points, 1]).astype(bool)
shore_status[transition:] = True

genset_status = np.ones([n_points, 1]).astype(bool)
genset_status[transition:] = False

status = np.hstack([shore_status, genset_status])
```

### Departure from Port (Shore Power → Genset)

```python
# Transition point
transition = int(n_points * 0.4)

# Status before transition: Shore power ON
# Status after transition: Genset ON
shore_status = np.ones([n_points, 1]).astype(bool)
shore_status[transition:] = False

genset_status = np.zeros([n_points, 1]).astype(bool)
genset_status[transition:] = True

status = np.hstack([shore_status, genset_status])
```

## Key Parameters

### Shore Power Rating

Typical shore power ratings for different vessel types:

| Vessel Type | Typical Rating |
|-------------|---------------|
| Small ferries | 200-500 kW |
| Cruise ships | 5-20 MW |
| Container ships | 1-5 MW |
| Tankers | 500-2000 kW |
| Ro-Ro vessels | 1-3 MW |

### Converter Efficiency

Typical efficiency values:

- **Low load (25%)**: 96%
- **Medium load (50%)**: 97%
- **High load (75%)**: 98%
- **Full load (100%)**: 98%

### Load Profiles at Berth

Typical hotel loads while at berth:

- **HVAC systems**: 40-60% of total load
- **Lighting**: 15-25%
- **Refrigeration**: 10-20%
- **Galley equipment**: 5-15%
- **Other systems**: 10-20%

## Common Issues and Solutions

### Issue: Power balance error

**Symptom**: Warning about power balance not achieved

**Solution**: Ensure shore power rating is sufficient for the load:
```python
max_load = np.max(load_profile)
if shore_power.rated_power < max_load:
    print(f"Warning: Shore power ({shore_power.rated_power} kW) "
          f"insufficient for peak load ({max_load:.1f} kW)")
```

### Issue: No fuel savings shown

**Symptom**: Fuel consumption > 0 with shore power

**Solution**: Verify shore power is actually ON:
```python
# Check shore power status
shore_output = power_system.power_sources[0].power_output
if np.sum(shore_output) == 0:
    print("Shore power is not active!")
```

### Issue: Converter losses too high

**Symptom**: Unexpected power losses

**Solution**: Check and adjust converter efficiency curve:
```python
# Check converter efficiency at current load
load_ratio = current_power / converter.rated_power
efficiency = converter.get_efficiency_from_load_percentage(load_ratio)
print(f"Converter efficiency: {efficiency*100:.1f}%")
```

## Environmental Impact Calculation

### Fuel Savings

```python
# Compare shore power vs genset operation
fuel_saved_kg = fuel_genset - fuel_shore
fuel_saved_percentage = (fuel_saved_kg / fuel_genset) * 100

# Extrapolate to annual savings
port_days_per_year = 100
hours_per_port_visit = 12
annual_fuel_saved = fuel_saved_kg * (port_days_per_year * hours_per_port_visit / simulation_hours)
```

### Emission Reductions

```python
# CO2 reduction
co2_saved_kg = co2_genset - co2_shore
co2_saved_tonnes = co2_saved_kg / 1000

# NOx reduction (if available)
if len(result_genset.total_emission_kg) > 0:
    nox_saved_kg = list(result_genset.total_emission_kg.values())[0] - \
                   list(result_shore.total_emission_kg.values())[0]
```

### Cost Analysis

```python
# Fuel cost savings
fuel_price_per_kg = 0.80  # USD/kg (example)
fuel_cost_saved = fuel_saved_kg * fuel_price_per_kg

# Shore power cost
shore_power_kwh = np.sum(shore_power_output) * time_step_s / 3600  # kWh
shore_power_rate = 0.15  # USD/kWh (example)
shore_power_cost = shore_power_kwh * shore_power_rate

# Net savings
net_savings = fuel_cost_saved - shore_power_cost
```

## Best Practices

1. **Size shore power appropriately**: Use peak load + 20% safety margin
2. **Include converter losses**: Model realistic efficiency curves
3. **Model transitions**: Include ramp-up/ramp-down periods
4. **Consider redundancy**: Keep one genset available as backup
5. **Validate results**: Check power balance is maintained
6. **Document assumptions**: Record converter efficiency, load profiles, etc.

## Example Results

Running the `shore_power_simple.py` script with typical loads shows:

```
Shore Power Operation:
  Fuel consumption: 0.000 kg
  CO2 emissions: 0.000 kg

Genset Operation:
  Fuel consumption: 97.355 kg
  CO2 emissions: 312.119 kg

Savings with Shore Power:
  Fuel saved: 97.355 kg (100%)
  CO2 avoided: 312.119 kg (100%)
```

For a 100-minute simulation, this demonstrates complete elimination of fuel consumption and emissions during port stays.

## Related Examples

- **02_Shore_Power_Example.ipynb**: Interactive notebook with visualizations
- **shore_power_simple.py**: Simple script version
- **00_Basic_Example.ipynb**: General FEEMS introduction

## References

- IEC/IEEE 80005-1: High Voltage Shore Connection Systems
- ISO 16903: Shore-side electricity
- IMO Resolution MEPC.323(74): Emission reduction measures

## Support

For questions or issues:
- See examples in `examples/` directory
- Check [GitHub issues](https://github.com/SINTEF/FEEMS/issues)
- Review component source code in `feems/components_model/component_electric.py`
