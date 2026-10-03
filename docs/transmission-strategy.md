# ZF 6HP / EGS integration plan

No EGS binary has been analyzed yet. Everything in this document is a design target until the exact transmission software is read and identified.

## Efficiency opportunities

- earlier low-load upshifts;
- earlier and longer torque-converter clutch engagement where NVH allows;
- reduced unnecessary TCC slip;
- larger upshift/downshift hysteresis to prevent hunting;
- avoid unnecessary downshifts when the engine can efficiently supply the requested torque;
- E-specific shift schedule;
- preserve immediate kickdown response.

## Important interaction with 4/8 and 6/8 firing

A fully locked converter transfers combustion torque pulsations directly into the driveline. 4/8 firing may therefore require either:

- a very carefully selected RPM/load window; or
- a small controlled amount of TCC slip for NVH damping.

The correct strategy must be determined from logging, not assumed.

## Required data

- exact EGS HW/SW identifiers and full/appropriate read;
- current gear;
- requested gear;
- input/output speed;
- TCC commanded state and actual slip;
- DME reported torque and EGS torque requests/interventions;
- D/S/M mode state and relevant CAN messages.
