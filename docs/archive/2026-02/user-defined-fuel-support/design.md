# Design: Support User-Defined Fuel with Arbitrary LHV and GHG Intensity

**Issue:** #80  
**Plan:** `docs/01-plan/2026-02-19-user-defined-fuel-support.md`  
**Branch:** `feature/issue-80-user-defined-fuel`

## Overview

This document describes the technical design for wiring up `FuelSpecifiedBy.USER` across the
FEEMS stack: the `Fuel` dataclass, aggregation logic, protobuf schema, and conversion functions.

---

## 1. `feems/feems/fuel.py`

### 1.1 `Fuel` dataclass — new `name` field

```python
@dataclass
class Fuel:
    ...
    name: str = ""          # required non-empty when fuel_specified_by == USER
```

**Constructor validation** (before existing assertions):

```python
if fuel_specified_by == FuelSpecifiedBy.USER and not name:
    raise ValueError("A non-empty 'name' is required when fuel_specified_by is USER.")
```

**`copy` property** — passes `name=self.name` to the `Fuel` constructor so copies preserve identity.

### 1.2 `FuelConsumption.__add__` — name-aware equality key

Current key: `(fuel_type, origin, fuel_specified_by)`

New key for USER fuels:

```python
and (
    each_fuel.fuel_specified_by != FuelSpecifiedBy.USER
    or x.name == each_fuel.name
)
```

This is additive — non-USER fuels are unaffected.

---

## 2. Proto schema changes

### 2.1 `feems_result.proto` — `FuelScalar` and `FuelArray`

Field tags 1–7 are already taken. Add at tag 8:

```protobuf
string name = 8;
```

Both messages receive this field. For non-USER fuels the field defaults to `""` (proto3 default),
so existing serialized data remains valid.

### 2.2 `system_structure.proto` — `Fuel` message

Tags 1–2 are taken. Add at tag 3:

```protobuf
string name = 3;
```

The `Fuel` message is used for component-level fuel spec (engine main/pilot fuel, fuel cell fuel).
The `name` field is available for round-trip fidelity when USER fuels are assigned to components
in future work.

---

## 3. Conversion functions

### 3.1 `convert_feems_result_to_proto.py`

Every `proto.FuelArray(...)` and `proto.FuelScalar(...)` construction receives `name=fuel.name`.
Non-USER fuels produce `name=""`, which serializes to the proto3 default (zero bytes on wire).

### 3.2 `convert_to_protobuf.py` / `convert_to_feems.py`

These files build `proto.Fuel` for component configuration using raw `fuel_type`/`fuel_origin`
enum values — no full `feems.fuel.Fuel` instance is involved. No changes required; the `name`
field in `proto.Fuel` defaults to `""` and is available for future component-level USER fuel
round-trips.

---

## 4. Proto recompilation

After modifying `.proto` files, run:

```bash
cd machinery-system-structure && bash compile_proto.sh
```

This regenerates `*_pb2.py` and `*_pb2.pyi` with the new `name` field.

---

## 5. Backward compatibility

| Concern | Impact |
|---------|--------|
| Existing `Fuel` callers | None — `name=""` default, no validation for non-USER |
| Existing proto messages | None — proto3 default `""` is wire-compatible |
| `FuelConsumption.__add__` | None — extra condition only activates for `USER` fuels |
| Unit tests | Pass unchanged (non-USER fuels unaffected) |

---

## 6. New unit tests (`feems/tests/test_fuel.py`)

| Test | What it verifies |
|------|-----------------|
| `test_user_fuel_name_required` | `ValueError` raised when `name=""` with `USER` |
| `test_user_fuel_name_stored_and_copied` | `name` set, preserved by `.copy` and `copy_except_mass_or_mass_fraction` |
| `test_non_user_fuel_name_defaults_empty` | IMO fuel defaults to `name=""` without error |
| `test_fuel_consumption_add_disambiguates_by_name` | Different names → 2 separate entries after `+` |
| `test_fuel_consumption_add_merges_same_name_user_fuel` | Same name → masses summed, 1 entry |
| `test_fuel_consumption_add_non_user_fuel_unaffected` | IMO fuels still merge by type/origin |
