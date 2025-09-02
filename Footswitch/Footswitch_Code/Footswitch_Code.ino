/*
 * Footswitch firmware for the MultiFX pedal.
 * Each of six digital inputs toggles a MIDI note on/off message on its channel.
 * The logic is interrupt-driven; main loop remains empty.
 */

#include <Arduino.h>

volatile bool offStates[6] = {true, true, true, true, true, true};
const uint8_t pins[6] = {D0, D1, D2, D3, D4, D5};

void setup() {
  Serial.begin(9600);
  Serial1.begin(31250);
  for (byte i = 0; i < 6; ++i) {
    pinMode(pins[i], INPUT);
  }
  attachInterrupt(digitalPinToInterrupt(pins[0]), ISR0, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pins[1]), ISR1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pins[2]), ISR2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pins[3]), ISR3, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pins[4]), ISR4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pins[5]), ISR5, CHANGE);
}

void sendMIDINoteOn(byte channel) {
  byte msg[] = { (byte)(0x90 | (channel & 0x0F)) };
  Serial1.write(msg, sizeof(msg));
  Serial.print("MIDI Note On Sent Channel ");
  Serial.println(channel);
}

void sendMIDINoteOff(byte channel) {
  byte msg[] = { (byte)(0x80 | (channel & 0x0F)) };
  Serial1.write(msg, sizeof(msg));
  Serial.print("MIDI Note Off Sent Channel ");
  Serial.println(channel);
}

void handleISR(byte channel) {
  if (offStates[channel]) {
    sendMIDINoteOn(channel);
  } else {
    sendMIDINoteOff(channel);
  }
  offStates[channel] = !offStates[channel];
}

void ISR0() { handleISR(0); }
void ISR1() { handleISR(1); }
void ISR2() { handleISR(2); }
void ISR3() { handleISR(3); }
void ISR4() { handleISR(4); }
void ISR5() { handleISR(5); }

void loop() {
  // Main loop intentionally empty; all logic handled in interrupts
}
