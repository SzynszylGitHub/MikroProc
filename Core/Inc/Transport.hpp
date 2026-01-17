/*
 * Transport.hpp
 *
 *  Created on: Jan 16, 2026
 *      Author: Szynszyl
 */

#pragma once

#include <cstdio>
#include <cstring>

struct UART_HandlerTypeDef;

class CsvLogger {
private:
    UART_HandleTypeDef* _huart; // Wskaźnik na uchwyt UART
    char _buffer[64];           // Bufor na tekst

public:
    CsvLogger(UART_HandleTypeDef* huart) : _huart(huart) {}

    void log(uint32_t timestamp, float value) {
        int len = snprintf(_buffer, sizeof(_buffer), "%lu, %.2f\r\n", timestamp, value);
        if (len > 0) {
            HAL_UART_Transmit(_huart, (uint8_t*)_buffer, (uint16_t)len, 100);
        }
    }

    void printHeader() {
        const char* header = "Time_ms, Voltage_V\r\n";
        HAL_UART_Transmit(_huart, (uint8_t*)header, strlen(header), 100);
    }
};
// ==================================================================================================================================
// example of use
//extern UART_HandleTypeDef hlpuart1;
///* USER CODE END PV */
//
//int main(void)
//{
//  /* ... (Tutaj jest kod inicjalizacji generowany przez CubeMX: HAL_Init, SystemClock_Config, MX_LPUART1_UART_Init itp.) ... */
//
//  /* USER CODE BEGIN 2 */
//
//  // 1. Tworzymy instancję loggera, przekazując adres naszego UARTu
//  // Dla Nucleo-H563ZI to zazwyczaj hlpuart1 (sprawdź w pliku main.h lub na górze main.cpp)
//  CsvLogger logger(&hlpuart1);
//
//  // Opcjonalnie wysyłamy nagłówek
//  logger.printHeader();
//
//  float voltage = 0.0f;
//  /* USER CODE END 2 */
//
//  /* Infinite loop */
//  /* USER CODE BEGIN WHILE */
//  while (1)
//  {
//      // 2. Pobieramy czas
//      uint32_t now = HAL_GetTick();
//
//      // 3. Symulacja danych (lub odczyt z czujnika)
//      voltage += 0.05f;
//      if (voltage > 3.3f) voltage = 0.0f;
//
//      // 4. Logujemy dane jednym eleganckim wywołaniem
//      logger.log(now, voltage);
//
//      // 5. Opóźnienie
//      HAL_Delay(50);
//
//    /* USER CODE END WHILE */
//  }
//}
//==============================================================================================
