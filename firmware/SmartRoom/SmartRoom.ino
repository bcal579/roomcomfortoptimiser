#include <rpcWiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "config.h"

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect.
  }
  Serial.println("Smart Room System Initialized.");

  // Scan available WiFi networks to debug SSID
  Serial.println("Scanning WiFi networks...");
  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++) {
    Serial.print(i);
    Serial.print(": ");
    Serial.print(WiFi.SSID(i));
    Serial.print(" (RSSI: ");
    Serial.print(WiFi.RSSI(i));
    Serial.println(")");
  }
  Serial.println("---");

  // Connect to WiFi
  setupWiFi();

  // Initialize MQTT connection
  setupMQTT();

  // Initialize the temperature sensor
  setupTemperatureSensor();
}

void loop() {
  // Ensure MQTT stays connected
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // Read and log the room temperature
  float currentTemp = readRoomTemperature();
  Serial.print("Current Room Temperature: ");
  Serial.print(currentTemp);
  Serial.println(" C");

  // Publish temperature to HiveMQ
  publishTemperature(currentTemp);

  delay(5000); // Wait 5 seconds before next reading
}
