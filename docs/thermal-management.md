# Thermal management

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [thermal-management.md](../research/thermal-management.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


The N62 uses map-controlled thermal management. The project should preserve the efficiency benefit of higher coolant temperature at low load while allowing lower targets under sustained high load where appropriate.

Potential strategy:

- **E / light cruise:** retain OEM-like high-efficiency thermal target.
- **D:** near-OEM.
- **S / kickdown:** transition toward the appropriate performance/protection thermal target.

Do not replace this with a single globally low thermostat target without evidence; that can sacrifice efficiency and does not reproduce the intended load-dependent strategy.
