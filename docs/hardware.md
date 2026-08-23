# Hardware and firmware notes

## Analog front end

The PCB implements five parallel readout channels, one for each glove sensor. Each channel uses a CA3140 BiMOS operational amplifier. A 330 kΩ-class precision resistor and a nominal 104 mV reference establish a sensor current of approximately 315 nA.

The board is powered from 12 V and regulates a stable 5 V rail with an L78L05. A 47 kΩ / 1 kΩ precision divider generates the reference voltage. The five analog outputs connect to Arduino Uno inputs A0–A4. The HC-05 Bluetooth module connects through crossed UART TX/RX lines at 115200 bit/s. The AFE and Arduino must share a common ground.

The fabricated board measures approximately 215.25 mm × 96.5 mm. The source design is in `hardware/kicad/` and was last saved with KiCad 10.

## Channel calculation

For channel `i`, the firmware calculates:

```text
Iset[i] = Vnode[i] / Rset[i]
Rs[i]   = (Vout[i] - Vnode[i]) / Iset[i]
```

The current source is intended for the approximate 1–15 MΩ operating range of the glove sensors. A different range requires renewed component selection and calibration.

## Firmware signal conditioning

The committed five-channel firmware:

1. performs a dummy ADC read after each channel change;
2. collects 12 samples per channel;
3. removes the minimum and maximum samples before averaging;
4. converts the ADC estimate to resistance using measured channel constants;
5. applies an IIR filter with `alpha = 0.08`;
6. emits one synchronized CSV row for S0–S4 every 50 ms;
7. reports channel status flags for invalid configuration, near-zero/full-scale ADC values, and output values below the reference.

## Calibration checklist

- Measure the 5 V ADC reference at the Arduino board.
- Measure each `RSET_OHMS` resistor individually.
- Measure the reference node for each channel and update `VNODE_VOLTS`.
- Verify that the full sensor range keeps `Vout` above `Vnode` and below ADC full scale.
- Compare representative resistance plateaus with a calibrated instrument.
- Re-run a static noise capture after any board, supply, wiring, or enclosure change.

## Design files

The repository includes the editable schematic, PCB, and project file, plus an exported schematic PDF. Local KiCad state, automatic backups, and intermediate manufacturing archives are excluded from version control.
