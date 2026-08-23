# Bill of materials summary

This summary is derived from the committed KiCad schematic. Confirm footprints, voltage ratings, packages, and the zener-diode part number before ordering or manufacturing.

| Quantity | References | Value / function |
|---:|---|---|
| 6 | U1, U3–U6 plus reference stage | CA3140 BiMOS operational amplifier |
| 1 | U2 | L78L05 5 V regulator, TO-92 footprint |
| 1 | R1 | 47 kΩ, reference divider |
| 7 | R2, R3, R6, R8, R10, R12, R13 | 1 kΩ |
| 6 | R4, R5, R7, R9, R11, R14 | 330 kΩ |
| 1 | C1 | 0.33 µF |
| 1 | C2 | 0.1 µF |
| 5 | C4, C9, C13, C17, C21 | 100 nF |
| 5 | C6, C10, C14, C18, C22 | 10 nF |
| 5 | C3, C7, C11, C15, C19 | 47 pF |
| 5 | C5, C8, C12, C16, C20 | 10 µF |
| 5 | D1–D5 | Zener diode; select the validated part number |
| 1 | J1 | Two-position screw terminal for power |
| 5 | J2, J4–J7 | Two-position sensor connectors |
| 1 | J3 | Six-position Arduino analog interface |
| 1 | J8 | Six-position auxiliary interface |
| 1 | J9 | Three-position Bluetooth/UART interface |

The physical prototype used precision resistors in the analog signal path. Measured per-channel set-resistor values are stored in the firmware and should be updated for every assembled board.
