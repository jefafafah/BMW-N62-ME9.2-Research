# Lambda strategy

## Goals

- Keep stock protection and high-load enrichment intact.
- Use lambda = 1 as the initial baseline for all firing-density testing.
- Investigate mild lean cruise only after the requested-lambda path is understood.
- Never fake lean operation by simply subtracting fuel while closed-loop control is still commanding stoichiometric operation.

## Relevant reference symbols

- `KFLAMFA` — driver-wish lambda map.
- `KFDLASO` / `KFDLASO2` — requested-lambda correction for continuous lambda control.
- `LASOABML` — requested lambda during bank shutoff.
- `IMLEVABS` / `IMLEVABS2` — integrated-air-mass threshold before lambda control is released after cylinder blanking.

These symbols indicate that the software already contains explicit coordination between cylinder blanking and lambda regulation.

## Experimental progression

1. 8/8 at lambda 1.00.
2. 6/8 at lambda 1.00.
3. 4/8 at lambda 1.00.
4. 8/8 mild lean (`~1.03-1.05`) in a narrow stable cruise window.
5. Extend only if combustion stability, knock, EGT/catalyst behaviour and fuel economy improve.
6. Combine mild lean with 6/8, then 4/8, only after isolated tests succeed.

Values above are development starting points, not a published final calibration.
