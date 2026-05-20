"""Manual verification of per-component operating-average metrics (issue #97).

Self-contained script that exercises five component types end-to-end and prints
the four operating-average scalars for each, so a human can sanity-check the
implementation against the expected formulas:

  - operating_avg_power_kw
  - operating_avg_reversible_power_kw   (PTI direction for PTI/PTO; 0 elsewhere)
  - operating_avg_efficiency            (energy_out / energy_in)
  - operating_avg_sfc_g_per_kwh         (fuel × 1000 / useful_kWh)

Scenarios:
  1. COGES on an ElectricPowerSystem  — full system path + proto round-trip
  2. Genset                            — direct dispatcher call with off-state
  3. Main engine                       — direct call, off-state masking check
  4. PTI/PTO                           — mixed-sign signal exercises both fields
  5. SteamBoiler                       — bolted onto MechanicalPropulsionSystem

Not a pytest test (no `test_` prefix, no asserts). Run manually:

    uv run python feems/tests/verify_operating_avg_metrics.py
"""

import numpy as np
from feems.components_model.component_electric import (
    COGES,
    PTIPTO,
    ElectricComponent,
    ElectricMachine,
    Genset,
)
from feems.components_model.component_mechanical import (
    COGAS,
    Engine,
    MainEngineForMechanicalPropulsion,
    SteamBoiler,
)
from feems.components_model.node import get_fuel_emission_energy_balance_for_component
from feems.components_model.utility import IntegrationMethod
from feems.fuel import FuelOrigin, FuelSpecifiedBy, TypeFuel
from feems.system_model import ElectricPowerSystem, MechanicalPropulsionSystem
from feems.types_for_feems import Power_kW, Speed_rpm, TypeComponent, TypePower
from MachSysS.convert_feems_result_to_proto import FEEMSResultConverter

# ---------------------------------------------------------------------------
# Inline fixtures (no test-utility imports — keeps the script self-contained)
# ---------------------------------------------------------------------------

_FLAT_BSFC_CURVE = np.array(
    [
        [0.1, 200.0],
        [0.5, 200.0],
        [1.0, 200.0],
    ]
)


def _flat_eta(eta: float) -> np.ndarray:
    return np.array([[0.25, eta], [0.50, eta], [0.75, eta], [1.00, eta]])


def _make_pti_pto(rated_power: float = 3000.0) -> PTIPTO:
    """Inlined version of feems/tests/utility.py::create_a_pti_pto.

    Builds a synchronous machine + rectifier + inverter + transformer chain
    wrapped in a PTIPTO instance. Used so this verification script doesn't
    depend on the test-only `tests.utility` module.
    """
    rated_kw = Power_kW(rated_power)
    rated_rpm = Speed_rpm(900.0)
    eff_machine = np.array([[0.1, 0.95], [1.0, 0.97]])
    eff_converter = np.array(
        [
            [1.00, 0.98],
            [0.75, 0.972],
            [0.50, 0.97],
            [0.25, 0.96],
        ]
    )

    synch_machine = ElectricMachine(
        type_=TypeComponent.SYNCHRONOUS_MACHINE,
        power_type=TypePower.PTI_PTO,
        name="synch machine",
        rated_power=rated_kw,
        rated_speed=rated_rpm,
        eff_curve=eff_machine,
    )
    rectifier = ElectricComponent(
        type_=TypeComponent.RECTIFIER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="rectifier",
        rated_power=rated_kw,
        eff_curve=np.array([0.995]),
    )
    inverter = ElectricComponent(
        type_=TypeComponent.INVERTER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="inverter",
        rated_power=rated_kw,
        eff_curve=eff_converter,
    )
    transformer = ElectricComponent(
        type_=TypeComponent.TRANSFORMER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="transformer",
        rated_power=rated_kw,
        eff_curve=np.array([0.99]),
    )
    return PTIPTO(
        name="PTI/PTO",
        components=[transformer, inverter, rectifier, synch_machine],
        switchboard_id=1,
        rated_power=rated_kw,
        rated_speed=rated_rpm,
        shaft_line_id=1,
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def _print_metrics(res, expected_avg_power=None, expected_reversible=None) -> None:
    print(f"  operating_avg_power_kw            = {res.operating_avg_power_kw}")
    print(f"  operating_avg_reversible_power_kw = {res.operating_avg_reversible_power_kw}")
    print(f"  operating_avg_efficiency          = {res.operating_avg_efficiency}")
    print(f"  operating_avg_sfc_g_per_kwh       = {res.operating_avg_sfc_g_per_kwh}")
    if expected_avg_power is not None:
        match = np.isclose(res.operating_avg_power_kw, expected_avg_power)
        print(f"  → expected avg power = {expected_avg_power} kW  → match: {match}")
    if expected_reversible is not None:
        match = np.isclose(res.operating_avg_reversible_power_kw, expected_reversible)
        print(f"  → expected reversible = {expected_reversible} kW  → match: {match}")


# ---------------------------------------------------------------------------
# Scenario 1 — COGES (system-level + proto round-trip)
# ---------------------------------------------------------------------------


def scenario_coges() -> None:
    _section("SCENARIO 1 — COGES (ElectricPowerSystem end-to-end + proto round-trip)")

    cogas = COGAS(
        name="COGAS",
        rated_power=5000.0,
        rated_speed=3600.0,
        eff_curve=np.array([[0.1, 0.30], [0.5, 0.40], [1.0, 0.42]]),
        fuel_type=TypeFuel.NATURAL_GAS,
        fuel_origin=FuelOrigin.FOSSIL,
    )
    generator = ElectricMachine(
        type_=TypeComponent.SYNCHRONOUS_MACHINE,
        name="generator",
        rated_power=cogas.rated_power * 0.9,
        rated_speed=cogas.rated_speed,
        power_type=TypePower.POWER_SOURCE,
        eff_curve=np.array([[0.1, 0.97], [1.0, 0.97]]),
        switchboard_id=1,
    )
    coges = COGES(name="COGES", cogas=cogas, generator=generator)
    coges.power_output = np.array([2000.0, 3000.0])

    system = ElectricPowerSystem(
        name="EPS",
        power_plant_components=[coges],
        bus_tie_connections=[],
    )
    system.set_time_interval(
        time_interval_s=np.array([3600.0, 3600.0]),
        integration_method=IntegrationMethod.sum_with_time,
    )
    res = system.get_fuel_energy_consumption_running_time(fuel_specified_by=FuelSpecifiedBy.IMO)
    row = res.detail_result.loc[coges.name]

    print(f"  power_output             = {coges.power_output}")
    print(f"  operating avg power      = {row['operating avg power [kW]']} kW")
    print(f"  operating avg reversible = {row['operating avg reversible power [kW]']} kW")
    print(f"  operating avg efficiency = {row['operating avg efficiency']:.4f}")
    print(f"  operating avg SFC        = {row['operating avg SFC [g/kWh]']:.2f} g/kWh")

    converter = FEEMSResultConverter(
        feems_result=res, system_feems=system, fuel_specified_by=FuelSpecifiedBy.IMO
    )
    proto = converter.get_feems_result_proto(include_time_series_for_components=False)
    pr = [r for r in proto.electric_system.detailed_result if r.component_name == coges.name][0]
    matches = [
        np.isclose(row["operating avg power [kW]"], pr.operating_avg_power_kw),
        np.isclose(row["operating avg reversible power [kW]"], pr.operating_avg_reversible_power_kw),
        np.isclose(row["operating avg efficiency"], pr.operating_avg_efficiency),
        np.isclose(row["operating avg SFC [g/kWh]"], pr.operating_avg_sfc_g_per_kwh),
    ]
    print(f"  Proto round-trip — all 4 fields equal: {all(matches)}")


# ---------------------------------------------------------------------------
# Scenario 2 — Genset
# ---------------------------------------------------------------------------


def scenario_genset() -> None:
    _section("SCENARIO 2 — Genset (off / 3 × 800 kW / off — on-state mask excludes off)")

    aux_engine = Engine(
        type_=TypeComponent.AUXILIARY_ENGINE,
        name="aux",
        rated_power=Power_kW(1500.0),
        rated_speed=Speed_rpm(750.0),
        bsfc_curve=_FLAT_BSFC_CURVE,
        fuel_type=TypeFuel.DIESEL,
        fuel_origin=FuelOrigin.FOSSIL,
    )
    gen = ElectricMachine(
        type_=TypeComponent.GENERATOR,
        name="gen",
        rated_power=Power_kW(1500.0),
        rated_speed=Speed_rpm(750.0),
        power_type=TypePower.POWER_SOURCE,
        eff_curve=np.array([[0.1, 0.95], [1.0, 0.97]]),
        switchboard_id=1,
    )
    genset = Genset(name="GS1", aux_engine=aux_engine, generator=gen)
    genset.power_output = np.array([0.0, 800.0, 800.0, 800.0, 0.0])
    genset.status = (genset.power_output != 0).astype(bool)

    res = get_fuel_emission_energy_balance_for_component(
        component=genset,
        time_interval_s=3600.0,
        integration_method=IntegrationMethod.simpson,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )

    print(f"  power_output             = {genset.power_output} kW")
    print(f"  running_hours_genset_hr  = {res.running_hours_genset_total_hr}")
    _print_metrics(res, expected_avg_power=800.0)


# ---------------------------------------------------------------------------
# Scenario 3 — Main engine
# ---------------------------------------------------------------------------


def scenario_main_engine() -> None:
    _section("SCENARIO 3 — Main engine (off + 3 × 1500 kW — on-state mask excludes off)")

    engine = Engine(
        type_=TypeComponent.MAIN_ENGINE,
        name="me-inner",
        rated_power=Power_kW(2000.0),
        rated_speed=Speed_rpm(900.0),
        bsfc_curve=_FLAT_BSFC_CURVE,
        fuel_type=TypeFuel.DIESEL,
        fuel_origin=FuelOrigin.FOSSIL,
    )
    me = MainEngineForMechanicalPropulsion(name="ME1", engine=engine)
    me.power_output = np.array([0.0, 1500.0, 1500.0, 1500.0])
    me.engine.power_output = me.power_output
    me.engine.status = (me.power_output > 0).astype(bool)

    res = get_fuel_emission_energy_balance_for_component(
        component=me,
        time_interval_s=60.0,
        integration_method=IntegrationMethod.simpson,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )

    print(f"  power_output                  = {me.power_output} kW")
    print(f"  running_hours_main_engines_hr = {res.running_hours_main_engines_hr}")
    _print_metrics(res, expected_avg_power=1500.0)


# ---------------------------------------------------------------------------
# Scenario 4 — PTI/PTO (mixed-sign signal)
# ---------------------------------------------------------------------------


def scenario_pti_pto() -> None:
    _section(
        "SCENARIO 4 — PTI/PTO bidirectional split\n"
        "           (-300, -300, 0, +100, +100, +200 → PTO avg 300, PTI avg 133.33)"
    )

    pp = _make_pti_pto()
    # power_input > 0 → PTI (electric in); power_input < 0 → PTO (electric out)
    pp.power_input = np.array([-300.0, -300.0, 0.0, 100.0, 100.0, 200.0])
    pp.power_output = np.array([-270.0, -270.0, 0.0, 90.0, 90.0, 180.0])
    pp.full_pti_mode = np.array([False, False, False, True, True, True])
    pp.full_pto_mode = np.array([True, True, False, False, False, False])
    pp.status = (pp.power_input != 0).astype(bool)

    res = get_fuel_emission_energy_balance_for_component(
        component=pp,
        time_interval_s=60.0,
        integration_method=IntegrationMethod.simpson,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )

    print(f"  power_input            = {pp.power_input} kW")
    _print_metrics(
        res,
        expected_avg_power=300.0,
        expected_reversible=(100.0 + 100.0 + 200.0) / 3.0,
    )

    print()
    print("  Variant — pure PTO (no PTI; reversible must stay 0):")
    pp.power_input = np.array([-500.0, -500.0, 0.0, 0.0])
    pp.power_output = np.array([-450.0, -450.0, 0.0, 0.0])
    pp.full_pti_mode = np.zeros(4, dtype=bool)
    pp.full_pto_mode = np.array([True, True, False, False])
    pp.status = (pp.power_input != 0).astype(bool)
    res2 = get_fuel_emission_energy_balance_for_component(
        component=pp,
        time_interval_s=60.0,
        integration_method=IntegrationMethod.simpson,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )
    print(f"    power_input    = {pp.power_input}")
    print(f"    avg power      = {res2.operating_avg_power_kw} kW")
    print(f"    avg reversible = {res2.operating_avg_reversible_power_kw} kW")


# ---------------------------------------------------------------------------
# Scenario 5 — SteamBoiler (via MechanicalPropulsionSystem)
# ---------------------------------------------------------------------------


def scenario_boiler() -> None:
    _section(
        "SCENARIO 5 — SteamBoiler on MechanicalPropulsionSystem\n"
        "           (constant 10 000 kg/h steam, flat 85 % thermal efficiency)"
    )

    system = MechanicalPropulsionSystem(name="bare-mech", components_list=[])
    system.set_time_interval(
        time_interval_s=3600.0, integration_method=IntegrationMethod.sum_with_time
    )
    boiler = SteamBoiler(
        name="ship boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        thermal_efficiency_curve=_flat_eta(0.85),
    )
    boiler.steam_out_kg_per_h = np.array([10_000.0])
    system.boiler = boiler

    res = system.get_fuel_energy_consumption_running_time()
    row = res.detail_result.loc[boiler.name]

    steam_kg_per_s = boiler.steam_out_kg_per_h[0] / 3600.0
    expected_kw = steam_kg_per_s * boiler.delta_h_kj_per_kg

    print(f"  steam_out_kg_per_h        = {boiler.steam_out_kg_per_h}")
    print(f"  delta_h_kj_per_kg         = {boiler.delta_h_kj_per_kg:.2f}")
    print(f"  expected steam-thermal kW = {expected_kw:.2f}  (ṁ_steam × Δh)")
    print(f"  running_hours_boiler_hr   = {res.running_hours_boiler_total_hr}")
    print()
    print(f"  operating avg power [kW]            = {row['operating avg power [kW]']}")
    print(f"  operating avg reversible power [kW] = {row['operating avg reversible power [kW]']}")
    print(f"  operating avg efficiency            = {row['operating avg efficiency']}")
    print(f"  operating avg SFC [g/kWh]           = {row['operating avg SFC [g/kWh]']}")
    print()
    print(
        f"  Match: power = ṁ_steam × Δh  → "
        f"{np.isclose(float(row['operating avg power [kW]']), expected_kw)}"
    )
    print(
        f"  Match: efficiency ≈ 0.85     → "
        f"{0.80 < float(row['operating avg efficiency']) < 0.90}"
    )
    print(
        f"  Match: reversible == 0       → "
        f"{float(row['operating avg reversible power [kW]']) == 0.0}"
    )


# ---------------------------------------------------------------------------


def main() -> None:
    scenario_coges()
    scenario_genset()
    scenario_main_engine()
    scenario_pti_pto()
    scenario_boiler()


if __name__ == "__main__":
    main()
