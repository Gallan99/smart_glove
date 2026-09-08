#include <Arduino.h>

// =========================
// ΡΥΘΜΙΣΕΙΣ
// =========================

const uint8_t NUM_SENSORS = 5;
const uint8_t SENSOR_PINS[NUM_SENSORS] = {A0, A1, A2, A3, A4};

// ΠΡΑΓΜΑΤΙΚΕΣ ΜΕΤΡΗΣΕΙΣ ΑΝΑ ΚΑΝΑΛΙ
float RSET_OHMS[NUM_SENSORS] = {
  326900.0f, 325100.0f, 327600.0f, 335100.0f, 320500.0f
};

float VNODE_VOLTS[NUM_SENSORS] = {
  0.1044f, 0.1044f, 0.1044f, 0.1044f, 0.1044f
};

// Το πραγματικό 5V του Uno
const float ADC_REF_VOLTS = 4.970f;

// Ρυθμός εξόδου
const uint32_t REPORT_INTERVAL_MS = 100;

// Samples ανά κανάλι σε κάθε περίοδο
const uint16_t SAMPLES_PER_CHANNEL = 12;

// Smoothing
const float IIR_ALPHA = 0.08f;

// =========================
// ΚΑΤΑΣΤΑΣΗ
// =========================

float rsFilteredOhm[NUM_SENSORS];
bool  rsFilterInit[NUM_SENSORS];

unsigned long t0_ms = 0;
unsigned long next_ms = 0;

// =========================
// ΒΟΗΘΗΤΙΚΑ
// =========================

float codeToVolts(float code) {
  return (code * ADC_REF_VOLTS) / 1023.0f;
}

void selectDefaultRef() {
  analogReference(DEFAULT);
  delay(2);
}

float readTrimmedMeanChannel(uint8_t pin, uint16_t samples) {
  // dummy read μετά από αλλαγή καναλιού
  analogRead(pin);
  delayMicroseconds(200);

  uint32_t sum = 0;
  int minVal = 1023;
  int maxVal = 0;

  for (uint16_t i = 0; i < samples; i++) {
    int v = analogRead(pin);

    sum += v;
    if (v < minVal) minVal = v;
    if (v > maxVal) maxVal = v;

    delayMicroseconds(200);
  }

  if (samples >= 4) {
    sum -= minVal;
    sum -= maxVal;
    return (float)sum / (float)(samples - 2);
  }

  return (float)sum / (float)samples;
}

void printHeader() {
  Serial.println(
    F("t_ms,"
      "adc0,Vout0_V,Rs0_MOhm,Rs0Filt_MOhm,status0,"
      "adc1,Vout1_V,Rs1_MOhm,Rs1Filt_MOhm,status1,"
      "adc2,Vout2_V,Rs2_MOhm,Rs2Filt_MOhm,status2,"
      "adc3,Vout3_V,Rs3_MOhm,Rs3Filt_MOhm,status3,"
      "adc4,Vout4_V,Rs4_MOhm,Rs4Filt_MOhm,status4")
  );
}

void setup() {
  Serial.begin(115200);

  selectDefaultRef();

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    rsFilteredOhm[i] = NAN;
    rsFilterInit[i] = false;
  }

  // πέτα μερικές αρχικές μετρήσεις
  for (int k = 0; k < 10; k++) {
    for (uint8_t i = 0; i < NUM_SENSORS; i++) {
      analogRead(SENSOR_PINS[i]);
    }
    delay(5);
  }

  t0_ms = millis();
  next_ms = t0_ms + REPORT_INTERVAL_MS;

  printHeader();
}

void loop() {
  unsigned long now = millis();
  if ((long)(now - next_ms) < 0) {
    return;
  }

  float adcMean[NUM_SENSORS];
  float vOut[NUM_SENSORS];
  float iSetA[NUM_SENSORS];
  float rsOhm[NUM_SENSORS];
  float rsMOhm[NUM_SENSORS];
  float rsFiltMOhm[NUM_SENSORS];
  const char* status[NUM_SENSORS];

  selectDefaultRef();

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    adcMean[i] = NAN;
    vOut[i] = NAN;
    iSetA[i] = NAN;
    rsOhm[i] = NAN;
    rsMOhm[i] = NAN;
    rsFiltMOhm[i] = NAN;
    status[i] = "OK";

    adcMean[i] = readTrimmedMeanChannel(SENSOR_PINS[i], SAMPLES_PER_CHANNEL);
    vOut[i] = codeToVolts(adcMean[i]);

    if (adcMean[i] < 2.0f) {
      status[i] = "WARN:NEAR_ZERO";
    } else if (adcMean[i] > 1020.0f) {
      status[i] = "WARN:NEAR_FS";
    }

    if (VNODE_VOLTS[i] <= 0.0f || RSET_OHMS[i] <= 0.0f) {
      status[i] = "ERROR:BAD_CFG";
      continue;
    }

    iSetA[i] = VNODE_VOLTS[i] / RSET_OHMS[i];

    if (vOut[i] <= VNODE_VOLTS[i]) {
      status[i] = "WARN:VOUT<=VREF";
      continue;
    }

    rsOhm[i] = (vOut[i] - VNODE_VOLTS[i]) / iSetA[i];
    rsMOhm[i] = rsOhm[i] / 1e6f;

    if (!rsFilterInit[i] || !isfinite(rsFilteredOhm[i])) {
      rsFilteredOhm[i] = rsOhm[i];
      rsFilterInit[i] = true;
    } else {
      rsFilteredOhm[i] =
        (1.0f - IIR_ALPHA) * rsFilteredOhm[i] + IIR_ALPHA * rsOhm[i];
    }

    rsFiltMOhm[i] = rsFilteredOhm[i] / 1e6f;
  }

  // Εκτύπωση CSV
  Serial.print(now - t0_ms);

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    Serial.print(',');

    if (isnan(adcMean[i])) Serial.print(F("nan"));
    else Serial.print(adcMean[i], 2);
    Serial.print(',');

    if (isnan(vOut[i])) Serial.print(F("nan"));
    else Serial.print(vOut[i], 6);
    Serial.print(',');

    if (isnan(rsMOhm[i])) Serial.print(F("nan"));
    else Serial.print(rsMOhm[i], 6);
    Serial.print(',');

    if (isnan(rsFiltMOhm[i])) Serial.print(F("nan"));
    else Serial.print(rsFiltMOhm[i], 6);
    Serial.print(',');

    Serial.print(status[i]);
  }

  Serial.println();

  next_ms += REPORT_INTERVAL_MS;
  if ((long)(now - next_ms) >= 0) {
    next_ms = now + REPORT_INTERVAL_MS;
  }
}