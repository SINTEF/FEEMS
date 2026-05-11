# Archive Index — 2026-02

| Feature | Archived At | Issue | Branch | Match Rate |
|---------|-------------|-------|--------|------------|
| user-defined-fuel-support | 2026-02-22 | #80 | feature/issue-80-user-defined-fuel | ≥90% |
| engine-emission-curve-ghg-override | 2026-02-22 | #85 | feature/issue-85-engine-emission-curve-ghg-override | 100% |

## user-defined-fuel-support

- **Summary**: Full support for `FuelSpecifiedBy.USER` fuels with arbitrary LHV and GHG intensity, threaded through the entire FEEMS stack including protobuf serialization.
- **Documents**: [plan](user-defined-fuel-support/plan.md) · [design](user-defined-fuel-support/design.md) · [analysis](user-defined-fuel-support/analysis.md) · [report](user-defined-fuel-support/report.md)

## engine-emission-curve-ghg-override

- **Summary**: Engine-defined CH4/N2O emission curves now override the flat GHG factors in `GhgEmissionFactorTankToWake` at each run-point, resolving the inconsistency between `total_emission_kg` and CO2eq accounting. `c_slip_percent` is zeroed when CH4 is overridden to prevent double-counting.
- **Documents**: [backlog](engine-emission-curve-ghg-override/2026-02-22-engine-emission-curve-ghg-override.md) · [plan](engine-emission-curve-ghg-override/2026-02-22-engine-emission-curve-ghg-override.md) · [design](engine-emission-curve-ghg-override/2026-02-22-engine-emission-curve-ghg-override.md) · [analysis](engine-emission-curve-ghg-override/engine-emission-curve-ghg-override.analysis.md) · [report](engine-emission-curve-ghg-override/engine-emission-curve-ghg-override.report.md)
