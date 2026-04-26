// distance.ino
#include "Ultrasonic.h"

const int DISTANCE_PIN = 0;
Ultrasonic ultrasonic(DISTANCE_PIN);

long getDistanceCm() {
  long reading = ultrasonic.MeasureInCentimeters();

  if (reading < 2 || reading > 350) {
    return -1;
  }

  return reading;
}
