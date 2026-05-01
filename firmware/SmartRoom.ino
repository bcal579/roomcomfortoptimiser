void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect.
  }
  Serial.println("Smart Room System Initialized.");
}

void loop() {
  // Main program loop
  delay(1000);
}
