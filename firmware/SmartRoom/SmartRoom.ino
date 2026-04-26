long getDistanceCm();
int getLightLevel();

void setup() {
  Serial.begin(9600);
}

void loop() {
  long distanceCm = getDistanceCm();

  if (distanceCm == -1) {
    Serial.println("Distance invalid.");
  } else {
    Serial.print("Distance: ");
    Serial.print(distanceCm);
    Serial.println(" cm");
  }

  int lightLevel = getLightLevel();

  if (lightLevel == -1) {
    Serial.println("Light level invalid.");
  } else {
    Serial.print("Light level: ");
    Serial.println(lightLevel);
  }

  delay(200);
}
