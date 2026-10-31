# Williams %R evidence mask

A zone question needs only its last N Williams %R values. The adapter also
fetched a preceding anchor for indicator context, then rejected the whole
series if any fetched range was zero. That invalidated a defined zone window
when the unused anchor alone had zero range.

The regression has14 initial bars with O=H=L=C=100, then11 bars with C=100,
H=110 and L=90. At slot23, all ten zone values are the registered -50 and
MOSTLY_MID should answer YES. The old adapter returns all NOT_EVALUABLE.
The cross question legitimately remains unknown at23 because it uses the
undefined slot13 anchor. Both questions are defined at24.

The adapter now retains native TA-Lib WILLR values unchanged and supplies a
separate per-bar zero-range mask. Existing consumers apply it only to their
declared N or N+1 evidence. Defined0 and-100 remain known. No epsilon,
cutoff, question identity, frozen producer or canonical CSV changes.

Tests authenticate frozen7dc native source, compare all numeric bits including
the undefined-range native zero, reproduce the zone/anchor boundary, retain
unknown crosses and test defined0/-100. This is a reference adapter correction;
real DERIVE, global PIT, chart and scoring gates remain unchanged.
