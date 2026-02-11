from typing import List
from mcp.server.fastmcp import FastMCP
import numpy as np
from feems.components_model import Engine
from feems.types_for_feems import TypeComponent

# Initialize FastMCP server
mcp = FastMCP("feems-server")

@mcp.tool()
def list_component_types() -> str:
    """
    List all available component types in FEEMS.
    """
    return "\n".join([f"{t.name}: {t.value}" for t in TypeComponent])

@mcp.tool()
def calculate_engine_fuel_consumption(
    rated_power_kw: float,
    rated_speed_rpm: float,
    current_load_kw: float,
    bsfc_curve_load_points: List[float],
    bsfc_curve_values: List[float],
    component_type: str = "MAIN_ENGINE"
) -> str:
    """
    Calculate fuel consumption for a marine engine based on its specific fuel consumption (BSFC) curve.
    
    Args:
        rated_power_kw: Rated power of the engine in kW.
        rated_speed_rpm: Rated speed of the engine in RPM.
        current_load_kw: The current power output to calculate consumption for (in kW).
        bsfc_curve_load_points: List of load points (ratios 0.0-1.0) for the BSFC curve.
        bsfc_curve_values: List of BSFC values (g/kWh) corresponding to the load points.
        component_type: Type of the engine (MAIN_ENGINE, AUXILIARY_ENGINE, MAIN_ENGINE_WITH_GEARBOX). Default: MAIN_ENGINE.
    """
    # Validate component type
    try:
        type_enum = TypeComponent[component_type]
    except KeyError:
        return f"Error: Invalid component_type '{component_type}'. Available types: {', '.join([t.name for t in TypeComponent])}"

    # Reconstruct the BSFC curve array expected by FEEMS
    # FEEMS expects a 2D array: column 0 is load ratio, column 1 is BSFC
    if len(bsfc_curve_load_points) != len(bsfc_curve_values):
        return "Error: bsfc_curve_load_points and bsfc_curve_values must have the same length."

    bsfc_curve = np.column_stack((bsfc_curve_load_points, bsfc_curve_values))
    
    try:
        # Create the Engine component
        engine = Engine(
            type_=type_enum,
            name="Simulated Engine",
            rated_power=rated_power_kw,
            rated_speed=rated_speed_rpm,
            bsfc_curve=bsfc_curve
        )
        
        # Get the run point
        run_point = engine.get_engine_run_point_from_power_out_kw(current_load_kw)
        
        # Extract results
        fuel_flow_kg_s = run_point.fuel_flow_rate_kg_per_s.fuels[0].mass_or_mass_fraction
        bsfc_g_kwh = run_point.bsfc_g_per_kWh
        load_ratio_percent = run_point.load_ratio * 100
        
        return (
            f"--- Engine Performance Calculation ---\n"
            f"Component Type: {component_type}\n"
            f"Rated Power: {rated_power_kw} kW\n"
            f"Current Load: {current_load_kw} kW ({load_ratio_percent:.2f}%)\n"
            f"Fuel Consumption: {fuel_flow_kg_s:.6f} kg/s\n"
            f"Specific Consumption (BSFC): {bsfc_g_kwh:.2f} g/kWh"
        )
    except Exception as e:
        return f"Error calculating fuel consumption: {str(e)}"

if __name__ == "__main__":
    mcp.run()
