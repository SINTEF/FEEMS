# Report: Support User-Defined Fuel with Arbitrary LHV and GHG Intensity

**Issue:** #80  
**Branch:** `feature/issue-80-user-defined-fuel`  
**Status:** Complete — ready for PR

---

## Summary

`FuelSpecifiedBy.USER` is now fully wired up across the FEEMS stack. Users can create fuels with
arbitrary LHV and GHG intensity by supplying a unique `name`, `lhv_mj_per_g`, and GHG emission
factors. These fuels are correctly distinguished during aggregation and serialized through the
protobuf result pipeline.

---

## Changes Made

| File | Change |
|------|--------|
| `feems/feems/fuel.py` | Added `name` field; `ValueError` for missing name on USER fuels; name-aware aggregation key in `FuelConsumption.__add__`; `name` propagated in `copy` |
| `feems/tests/test_fuel.py` | 6 new unit tests |
| `machinery-system-structure/proto/feems_result.proto` | `string name = 8` in `FuelScalar` and `FuelArray` |
| `machinery-system-structure/proto/system_structure.proto` | `string name = 3` in `Fuel` |
| `machinery-system-structure/MachSysS/feems_result_pb2.py` | Recompiled |
| `machinery-system-structure/MachSysS/feems_result_pb2.pyi` | Recompiled |
| `machinery-system-structure/MachSysS/system_structure_pb2.py` | Recompiled |
| `machinery-system-structure/MachSysS/system_structure_pb2.pyi` | Recompiled |
| `machinery-system-structure/MachSysS/convert_feems_result_to_proto.py` | `name=fuel.name` added to all `FuelArray`/`FuelScalar` constructions |

---

## Test Results

```
116 passed, 1 skipped, 36 subtests passed
```

---

## PDCA Links

- Backlog: `docs/backlog/2026-02-19-user-defined-fuel-support.md`
- Plan: `docs/01-plan/2026-02-19-user-defined-fuel-support.md`
- Design: `docs/02-design/2026-02-19-user-defined-fuel-support.md`
- Analysis: `docs/03-analysis/2026-02-19-user-defined-fuel-support.md`
