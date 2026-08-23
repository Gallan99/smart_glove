# Five-channel serial protocol

The firmware emits UTF-8-compatible ASCII CSV at 115200 bit/s. A header is printed once after reset, followed by one synchronized row per acquisition frame.

## Row format

```text
t_ms,
adc0,Vout0_V,Rs0_MOhm,Rs0Filt_MOhm,status0,
adc1,Vout1_V,Rs1_MOhm,Rs1Filt_MOhm,status1,
adc2,Vout2_V,Rs2_MOhm,Rs2Filt_MOhm,status2,
adc3,Vout3_V,Rs3_MOhm,Rs3Filt_MOhm,status3,
adc4,Vout4_V,Rs4_MOhm,Rs4Filt_MOhm,status4
```

Line breaks above are for readability; the firmware writes one 26-field CSV row.

## Status values

| Status | Meaning |
|---|---|
| `OK` | Channel passed the firmware checks |
| `WARN:NEAR_ZERO` | ADC code is close to zero |
| `WARN:NEAR_FS` | ADC code is close to full scale |
| `WARN:VOUT<=VREF` | Resistance cannot be calculated from the present values |
| `ERROR:BAD_CFG` | Reference voltage or set resistor is not positive |

Invalid numerical outputs are written as `nan`. The Python parser accepts the frame for diagnostics but marks it invalid for data capture and inference.

## Host-side units

- The live monitor displays and logs filtered resistance in MΩ.
- The ML capture command converts filtered values to Ω before writing the research-dataset schema.
- The bundled Random Forest was designed for Ω-valued S0–S4 features. Mixing Ω and MΩ will invalidate predictions.
