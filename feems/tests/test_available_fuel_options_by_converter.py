import unittest
import numpy as np

from feems.components_model.component_electric import (
    ElectricMachine,
    Genset,
    FuelCellSystem,
    FuelCell,
    ElectricComponent,
)
from feems.components_model.component_mechanical import (
    Engine,
    MainEngineForMechanicalPropulsion,
    EngineDualFuel,
    EngineMultiFuel,
    FuelCharacteristics,
)
from feems.system_model import ElectricPowerSystem, MechanicalPropulsionSystem, FuelOption
from feems.types_for_feems import TypePower, TypeComponent
from feems.fuel import TypeFuel, FuelOrigin


class TestAvailableFuelOptions(unittest.TestCase):
    def setUp(self):
        self.dummy_bsfc = np.array([[0, 200], [1, 200]])
        self.dummy_eff = np.array([[0, 0.95], [1, 0.95]])

    def create_generator(self, name):
        return ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name=name,
            rated_power=1000,
            rated_speed=900,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=1,
        )

    def test_genset_options(self):
        # 1. Standard Diesel Genset
        engine_diesel = Engine(
            type_=TypeComponent.AUXILIARY_ENGINE,
            name="Diesel Engine",
            rated_power=1000,
            rated_speed=900,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
            bsfc_curve=self.dummy_bsfc,
        )
        genset_diesel = Genset("Diesel Genset", engine_diesel, self.create_generator("Gen1"))

        # 2. Dual Fuel Genset (LNG + Diesel Pilot)
        engine_df = EngineDualFuel(
            type_=TypeComponent.AUXILIARY_ENGINE,
            name="DF Engine",
            rated_power=1000,
            rated_speed=900,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
            pilot_fuel_type=TypeFuel.DIESEL,
            pilot_fuel_origin=FuelOrigin.FOSSIL,
            bsfc_curve=self.dummy_bsfc,
            bspfc_curve=np.array([[0, 2], [1, 2]]),
        )
        genset_df = Genset("DF Genset", engine_df, self.create_generator("Gen2"))

        # 3. Multi Fuel Genset (Methanol + Diesel)
        characteristics = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.METHANOL,
                main_fuel_origin=FuelOrigin.BIO,
                bsfc_curve=self.dummy_bsfc,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.DIESEL,
                main_fuel_origin=FuelOrigin.FOSSIL,
                bsfc_curve=self.dummy_bsfc,
            ),
        ]
        engine_mf = EngineMultiFuel(
            type_=TypeComponent.AUXILIARY_ENGINE,
            name="MF Engine",
            rated_power=1000,
            rated_speed=900,
            multi_fuel_characteristics=characteristics,
        )
        genset_mf = Genset("MF Genset", engine_mf, self.create_generator("Gen3"))

        eps = ElectricPowerSystem(
            name="EPS Gensets",
            power_plant_components=[genset_diesel, genset_df, genset_mf],
            bus_tie_connections=[],
        )

        options = eps.available_fuel_options_by_converter.get("genset", [])

        # Verify Diesel (Fossil) - Primary=True (from Standard)
        diesel_fossil_primary = FuelOption(TypeFuel.DIESEL, FuelOrigin.FOSSIL, False, True)
        self.assertIn(diesel_fossil_primary, options)

        # Verify Diesel (Fossil) - Pilot (from DF)
        diesel_fossil_pilot = FuelOption(TypeFuel.DIESEL, FuelOrigin.FOSSIL, True, True)
        self.assertIn(diesel_fossil_pilot, options)

        # Verify LNG (Fossil) - Primary=True (from DF)
        lng_fossil = FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True)
        self.assertIn(lng_fossil, options)

        # Verify Methanol (Bio) - Primary=True (from MF 1st option)
        methanol_bio = FuelOption(TypeFuel.METHANOL, FuelOrigin.BIO, False, True)
        self.assertIn(methanol_bio, options)

        # Verify Diesel (Fossil) - from MF 2nd option.
        diesel_fossil_mf = FuelOption(TypeFuel.DIESEL, FuelOrigin.FOSSIL, False, False)
        self.assertIn(diesel_fossil_mf, options)

        # Check for duplicates by ensuring the length matches the unique set
        self.assertEqual(
            len(options), len(set(options)), "Duplicate fuel options found for gensets"
        )

    def test_fuel_cell_options(self):
        fc1 = FuelCell(
            name="FC H2",
            rated_power=500,
            eff_curve=self.dummy_eff,
            fuel_type=TypeFuel.HYDROGEN,
            fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
        )
        fcs1 = FuelCellSystem(
            name="FCS H2",
            fuel_cell_module=fc1,
            converter=ElectricComponent(
                type_=TypeComponent.POWER_CONVERTER,
                name="Conv1",
                rated_power=500,
                power_type=TypePower.POWER_SOURCE,
                switchboard_id=1,
                eff_curve=self.dummy_eff,
            ),
            switchboard_id=1,
        )

        fc2 = FuelCell(
            name="FC NH3",
            rated_power=500,
            eff_curve=self.dummy_eff,
            fuel_type=TypeFuel.AMMONIA,
            fuel_origin=FuelOrigin.BIO,
        )
        fcs2 = FuelCellSystem(
            name="FCS NH3",
            fuel_cell_module=fc2,
            converter=ElectricComponent(
                type_=TypeComponent.POWER_CONVERTER,
                name="Conv2",
                rated_power=500,
                power_type=TypePower.POWER_SOURCE,
                switchboard_id=1,
                eff_curve=self.dummy_eff,
            ),
            switchboard_id=1,
        )

        eps = ElectricPowerSystem(
            name="EPS FC", power_plant_components=[fcs1, fcs2], bus_tie_connections=[]
        )

        options = eps.available_fuel_options_by_converter.get("fuel_cell", [])
        self.assertEqual(len(options), 2)

        h2_opt = FuelOption(TypeFuel.HYDROGEN, FuelOrigin.RENEWABLE_NON_BIO, False, True)
        nh3_opt = FuelOption(TypeFuel.AMMONIA, FuelOrigin.BIO, False, True)

        self.assertIn(h2_opt, options)
        self.assertIn(nh3_opt, options)

        # Check for duplicates
        self.assertEqual(
            len(options), len(set(options)), "Duplicate fuel options found for fuel cells"
        )

    def test_mechanical_propulsion_options(self):
        # 1. Main Engine Dual Fuel
        engine_df = EngineDualFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="DF Main",
            rated_power=5000,
            rated_speed=100,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
            pilot_fuel_type=TypeFuel.DIESEL,
            pilot_fuel_origin=FuelOrigin.FOSSIL,
            bsfc_curve=self.dummy_bsfc,
            bspfc_curve=np.array([[0, 2], [1, 2]]),
        )
        me_df = MainEngineForMechanicalPropulsion("ME DF", engine_df, 1)

        mps = MechanicalPropulsionSystem(name="MPS Test", components_list=[me_df])

        options = mps.available_fuel_options_by_converter.get("main_engine", [])

        ng_opt = FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True)
        diesel_pilot_opt = FuelOption(TypeFuel.DIESEL, FuelOrigin.FOSSIL, True, True)

        self.assertIn(ng_opt, options)
        self.assertIn(diesel_pilot_opt, options)

        # Check for duplicates
        self.assertEqual(
            len(options),
            len(set(options)),
            "Duplicate fuel options found for mechanical propulsion",
        )


if __name__ == "__main__":
    unittest.main()
