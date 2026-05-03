// Humidity sensor configuration
// Following the same analog pattern as the temperature sensor.
// Assuming an analog humidity sensor (like HIH-4030) for consistency.

#define HUM_SENSOR_PIN A1

void setupHumiditySensor() {
  // Initialize the humidity sensor
  Serial.println("Humidity sensor (analog) initialized on pin A1.");
}

float readRoomHumidity() {
  int sensorValue = analogRead(HUM_SENSOR_PIN);
  
  // Convert the analog reading (0 - 1023) to a voltage (0 - 3.3V)
  float voltage = sensorValue * (3.3 / 1023.0);
  
  // Convert the voltage to humidity percentage
  // Typical linear mapping for some analog humidity sensors:
  // (Voltage / SupplyVoltage) * 100
  float humidityRH = (voltage / 3.3) * 100.0;
  
  // Ensure it stays within 0-100 range
  if (humidityRH > 100.0) humidityRH = 100.0;
  if (humidityRH < 0.0) humidityRH = 0.0;
  
  return humidityRH;
}
