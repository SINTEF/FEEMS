import unittest

import numpy as np
from feems.components_model.component_electric import (
    COGES,
    ElectricComponent,
    ElectricMachine,
    FuelCell,
    FuelCellSystem,
    Genset,
)
from feems.components_model.component_mechanical import (
    COGAS,
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
    FuelCharacteristics,
    MainEngineForMechanicalPropulsion,
)
from feems.fuel import FuelOrigin, TypeFuel
from feems.system_model import ElectricPowerSystem, FuelOption, MechanicalPropulsionSystem
from feems.types_for_feems import TypeComponent, TypePower


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


class TestCOGESFuelOptions(unittest.TestCase):
    """Tests for available_fuel_options_by_converter / available_fuel_options /
    multi_fuel_engine_inventory when the electric power system contains COGES units."""

    DUMMY_EFF = np.array([[0.0, 0.30], [0.5, 0.40], [1.0, 0.44]])

    def _make_generator(self, name: str = "Gen", switchboard_id: int = 1) -> ElectricMachine:
        return ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name=name,
            rated_power=1000,
            rated_speed=3000,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=switchboard_id,
        )

    def _make_coges(
        self,
        fuel_type: TypeFuel = TypeFuel.NATURAL_GAS,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        multi_fuel_characteristics=None,
    ) -> COGES:
        cogas = COGAS(
            name="COGAS",
            rated_power=1000,
            rated_speed=3000,
            eff_curve=self.DUMMY_EFF,
            fuel_type=fuel_type,
            fuel_origin=fuel_origin,
            multi_fuel_characteristics=multi_fuel_characteristics,
        )
        return COGES(name="COGES unit", cogas=cogas, generator=self._make_generator())

    def test_single_fuel_coges_by_converter(self):
        coges = self._make_coges(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )

        options = eps.available_fuel_options_by_converter.get("coges", [])
        self.assertEqual(len(options), 1)
        self.assertIn(FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True), options)

    def test_multi_fuel_coges_by_converter(self):
        chars = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=self.DUMMY_EFF,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
                eff_curve=self.DUMMY_EFF,
            ),
        ]
        coges = self._make_coges(multi_fuel_characteristics=chars)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )

        options = eps.available_fuel_options_by_converter.get("coges", [])
        self.assertEqual(len(options), 2)
        self.assertIn(FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True), options)
        self.assertIn(
            FuelOption(TypeFuel.HYDROGEN, FuelOrigin.RENEWABLE_NON_BIO, False, False), options
        )
        self.assertEqual(len(options), len(set(options)), "Duplicate fuel options found")

    def test_multi_fuel_coges_inventory(self):
        chars = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=self.DUMMY_EFF,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
                eff_curve=self.DUMMY_EFF,
            ),
        ]
        coges = self._make_coges(multi_fuel_characteristics=chars)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )

        inventory = eps.multi_fuel_engine_inventory
        self.assertIn("COGES unit", inventory)
        self.assertEqual(len(inventory["COGES unit"]), 2)

    def test_single_fuel_coges_not_in_inventory(self):
        coges = self._make_coges(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )
        self.assertEqual(eps.multi_fuel_engine_inventory, {})

    def test_available_fuel_options_multi_fuel_coges(self):
        chars = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=self.DUMMY_EFF,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
                eff_curve=self.DUMMY_EFF,
            ),
        ]
        coges = self._make_coges(multi_fuel_characteristics=chars)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )

        options = eps.available_fuel_options
        self.assertIn(FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True), options)
        self.assertIn(
            FuelOption(TypeFuel.HYDROGEN, FuelOrigin.RENEWABLE_NON_BIO, False, False), options
        )
        self.assertEqual(len(options), len(set(options)), "Duplicate fuel options found")

    def test_coges_secondary_fuel_in_by_converter(self):
        chars = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=self.DUMMY_EFF,
                pilot_fuel_type=TypeFuel.DIESEL,
                pilot_fuel_origin=FuelOrigin.FOSSIL,
            ),
        ]
        coges = self._make_coges(multi_fuel_characteristics=chars)
        eps = ElectricPowerSystem(
            name="EPS", power_plant_components=[coges], bus_tie_connections=[]
        )

        options = eps.available_fuel_options_by_converter.get("coges", [])
        self.assertIn(FuelOption(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, False, True), options)
        self.assertIn(FuelOption(TypeFuel.DIESEL, FuelOrigin.FOSSIL, True, True), options)


if __name__ == "__main__":
    unittest.main()
