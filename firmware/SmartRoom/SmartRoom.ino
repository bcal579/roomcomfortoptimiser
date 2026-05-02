void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect.
  }
  Serial.println("Smart Room System Initialized.");
  
  // Initialize the temperature sensor
  setupTemperatureSensor();
}

void loop() {
  // Read and log the room temperature
  float currentTemp = readRoomTemperature();
  Serial.print("Current Room Temperature: ");
  Serial.print(currentTemp);
  Serial.println(" C");

  delay(2000); // Wait 2 seconds before next reading
}
