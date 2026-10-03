# Active hypotheses

## H1 — E-mode efficiency through 4/8 and 6/8 firing density

The Bosch torque-reduction machinery can likely be reused for controlled skip-fire, but it needs a separate load/torque strategy so wheel torque is not simply reduced. Benefit is unknown until measured.

## H2 — Rotating skip-fire is preferable to fixed V4

Alternating firing masks should avoid keeping the same cylinders cold/unfired continuously and may reduce bank/lambda imbalance. This does not remove pumping losses because valves remain active.

## H3 — Native kickdown is the correct E -> POWER override trigger

`B_kd` is already calculated by the ECU. A latched E request plus temporary native kickdown override should feel OEM and avoid inventing a pedal threshold.

## H4 — Mild lean cruise adds incremental efficiency

A small lean shift may improve steady-state BSFC if combustion remains stable, but it must be implemented through the lambda target/coordinator and validated independently from firing-density experiments.

## H5 — EGS/TCC calibration can add meaningful whole-trip efficiency

Especially at 60-100 km/h, earlier TCC engagement and better hysteresis may reduce converter losses. At steady highway speed with the converter already locked, little additional gain should be expected.

## H6 — Generator load can be time-shifted

OEM generator-shedding primitives suggest a strategy that minimizes alternator load during acceleration and recovers charging during deceleration/overrun when electrical conditions permit.

## H7 — 95-RON-safe performance with adaptive benefit on better fuel

Build the hard limits around 95 RON and let existing knock adaptation retain more advance on better fuel rather than requiring a manual 95/98 switch.
