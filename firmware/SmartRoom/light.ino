// light.ino
const int LIGHT_PIN = A2;

int getLightLevel() {
  int reading = analogRead(LIGHT_PIN);

  if (reading < 0 || reading > 1023) {
    return -1;
  }

  return reading;
}
