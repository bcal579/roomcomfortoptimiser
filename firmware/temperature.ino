// Temperature sensor configuration
// Assuming an LM35 or similar analog temperature sensor for simplicity.
// Can be changed to DHT or other sensors if needed.

#define TEMP_SENSOR_PIN A0

void setupTemperatureSensor() {
  // Initialize the temperature sensor
  Serial.println("Temperature sensor (analog) initialized on pin A0.");
}

float readRoomTemperature() {
  int sensorValue = analogRead(TEMP_SENSOR_PIN);
  
  // Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V)
  float voltage = sensorValue * (5.0 / 1023.0);
  
  // Convert the voltage to temperature in Celsius
  // For an LM35 sensor, 10mV = 1 degree Celsius
  float temperatureC = voltage * 100.0;
  
  return temperatureC;
}
