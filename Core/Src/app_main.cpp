/*
 * app_main.cpp
 *
 * Created on: Dec 27, 2025
 * Author: Szynszyl & Fixed by Gemini
 */
#include "app_main.hpp"
#include "main.h"

#include <cstdlib>
#include <cstring> // Poprawiono includy (cstring dla strcmp)
#include <string>
#include <numeric>
#include <cstdio>  // Dla sscanf
#include "BMPXX80.h"

#include "PID.hpp"
#include "Transport.hpp"

extern "C"{
    extern UART_HandleTypeDef huart3;
    extern I2C_HandleTypeDef hi2c1;
    extern TIM_HandleTypeDef htim2;

    extern float temperature;
    extern long pressure;
    extern int Utest;
}

// komunikacja
// ========================================================
struct ValueReceive{
    int received_number = 0;
    float receive_float_number = 0.f;
    bool new_data_ready = false;
    int command_type = 0;
};

volatile ValueReceive Rn;

// ----------------------------------- C style ------------------------------------
// ZWIĘKSZONO BUFOR - 10 znaków to za mało na "/set yr: 24.5"
constexpr std::size_t RX_BUFFER_SIZE = 32;
uint8_t rx_byte;
char rx_buffer[RX_BUFFER_SIZE];
uint8_t rx_index = 0;

extern "C" void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3) {
        // Sprawdzamy znak końca linii
        if (rx_byte == '\n' || rx_byte == '\r') {
            rx_buffer[rx_index] = '\0'; // Null-terminator

            if (rx_index > 0) {
                if (std::strcmp(rx_buffer, "/safeData") == 0) {
                    Rn.command_type = 1;
                    Rn.new_data_ready = true;
                }
                else if (std::strcmp(rx_buffer, "/stop") == 0) {
                    Rn.command_type = 2;
                    Rn.new_data_ready = true;
                }
                else if (std::strcmp(rx_buffer, "/monitor") == 0){
                    Rn.command_type = 3;
                    Rn.new_data_ready = true;
                }
                // Używamy spacji w formacie sscanf dla pewności
                else if (std::sscanf(rx_buffer, "/set yr: %f", &Rn.receive_float_number) == 1) {
                    Rn.command_type = 4;
                    Rn.new_data_ready = true;
                }
                else {
                    // Fallback dla samej liczby
                    Rn.received_number = std::atoi(rx_buffer);
                    Rn.command_type = 0;
                    Rn.new_data_ready = true;
                }
            }
            rx_index = 0; // Resetujemy bufor
        } else {
            // Zbieranie znaków do bufora z zabezpieczeniem overflow
            if (rx_index < RX_BUFFER_SIZE - 1) {
                rx_buffer[rx_index++] = (char)rx_byte;
            }
        }
        HAL_UART_Receive_IT(&huart3, &rx_byte, 1);
    }
}

// nastawy PID
//==========================================================================
constexpr float dt = 0.1f;       // Czas próbkowania w sekundach
constexpr uint32_t dt_ms = 100;  // Czas próbkowania w ms (dt * 1000)
constexpr uint16_t max_pwm = 1000;
constexpr uint16_t min_pwm = 0;
constexpr float Kp = 100;
constexpr float Ki = 0.1;
constexpr float Kd = 30;
constexpr float Tf = 0.05;

// =========================================================================
void app_main(void)
{
    // nasluchiwanie com start
    HAL_UART_Receive_IT(&huart3, &rx_byte, 1);

    // start pwm
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);

    // uruchomienie czujnika
    BMP280_Init(&hi2c1, BMP280_TEMPERATURE_16BIT, BMP280_STANDARD, BMP280_FORCEDMODE);

    // ======================================
    CsvLogger logger(&huart3);
    uint32_t now = 0;

    // Timery programowe (zamiast delay)
    uint32_t last_pid_time = 0;
    uint32_t last_monitor_time = 0;

    bool safeData = false;
    bool monitorData = false;
    // ======================================

    // ======================================================
    PID pid(dt, max_pwm, min_pwm, Kp, Ki, Kd, Tf);
    float yr = 28.f;
    int u = 0;
    uint16_t counter = 0;
    // ======================================================

    while(true)
    {
        // 1. Obsługa komend UART
        if(Rn.new_data_ready){
            switch(Rn.command_type){
                case 1:{ // start sharing data
                    safeData = true;
                    monitorData = false; // Zwykle chcemy albo jedno albo drugie
                    counter = 0; // Reset licznika przy starcie
                }break;
                case 2:{ // stop
                    safeData = false;
                    monitorData = false;
                    // Reset PID i PWM przy zatrzymaniu (bezpieczeństwo)
                    u = 0;
                    Utest = 0;
                    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
                }break;
                case 3:{ // monitor only
                    monitorData = true;
                    safeData = false;
                }break;
                case 4:{
                    yr = Rn.receive_float_number;
                }break;
                default:{
                    std::string msg = std::to_string(Rn.received_number);
                    HAL_UART_Transmit(&huart3, (uint8_t*)msg.c_str(), msg.length(), 100);
                }break;
            }
            Rn.new_data_ready = false;
        }

        // 2. Główna pętla czasowa (10Hz / 100ms) - PID i Odczyt
        if (HAL_GetTick() - last_pid_time >= dt_ms)
        {
            last_pid_time = HAL_GetTick(); // Aktualizacja czasu
            now = last_pid_time;

            // A. Odczyt temperatury (Zawsze, żeby mieć aktualne dane)
            temperature = BMP280_ReadTemperature();

            // B. Obsługa błędu -99 (Error Latching fix)
            if (temperature <= -90.0f) // Tolerancja dla float (-99)
            {
                // Resetujemy interfejs I2C
                HAL_I2C_DeInit(&hi2c1);
                HAL_Delay(10);
                HAL_I2C_Init(&hi2c1);
                BMP280_Init(&hi2c1, BMP280_TEMPERATURE_16BIT, BMP280_STANDARD, BMP280_FORCEDMODE);

                // Krótka pauza na wstanie czujnika
                HAL_Delay(50);

                // Nie wykonujemy PID ani logowania w tym cyklu!
                continue;
            }

            // C. Logika SafeData (PID + Logowanie szybkie)
            if(safeData){
                // Logowanie
                logger.log(now, temperature);

                // PID
                u = pid.calculate(yr, temperature);
                Utest = u;
                __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, u);

                // Auto-stop po 1000 próbkach
                if(counter >= 1050)
                {
                    // Symulacja komendy STOP
                    safeData = false;
                    u = 0;
                    Utest = 0;
                    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
                    counter = 0;
                }
                else {
                    counter++;
                }
            }
        }

        // 3. Logika MonitorData (Logowanie wolne - co 5s)
        // Wykonuje się niezależnie od pętli 100ms, ale nie blokuje procesora!
        if(monitorData)
        {
            if(HAL_GetTick() - last_monitor_time >= 5000)
            {
                last_monitor_time = HAL_GetTick();
                // Logujemy aktualną temperaturę (odczytaną w pętli powyżej)
                logger.log(last_monitor_time, temperature);
            }
        }
    }
}
