/*
 * app_main.cpp
 *
 * Created on: Dec 27, 2025
 * Author: Szynszyl
 */
#include "app_main.hpp"
#include "main.h"

#include <cstdlib>
#include <cstring>
#include <string>
#include <numeric>
#include <cstdio>
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
                if (std::sscanf(rx_buffer, "/safeData: %d", &Rn.received_number)) {
                    constexpr uint16_t probes = 1000;
                	if(!Rn.receive_float_number) Rn.receive_number = probes;
                	Rn.command_type = 1;
                    Rn.new_data_ready = true;
                }
                else if (!std::strcmp(rx_buffer, "/stop")) {
                    Rn.command_type = 2;
                    Rn.new_data_ready = true;
                }
                else if (!std::strcmp(rx_buffer, "/monitor")){
                    Rn.command_type = 3;
                    Rn.new_data_ready = true;
                }
                else if (std::sscanf(rx_buffer, "/set yr: %f", &Rn.receive_float_number)) {
                    Rn.command_type = 4;
                    Rn.new_data_ready = true;
                }
                else {
                    // Fallback dla samej liczby
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

constexpr float threshold = 2; //value%

float filtrLast(float val){
	constexpr float thresholdUp = 1 + (threshold / 100.f);
	constexpr float thresholdDown = 1 - (threshold/100.f);

	static float last_verify = val;
	if(val * thresholdDown > last_verify || val * thresholdUp < last_verify )
	{
		last_verify = val;
		return val;
	}
	else
	{
		return last_verify;
	}
}

// nastawy PID
//==========================================================================
constexpr float dt = 0.1f; // Czas próbkowania w sekundach
constexpr uint32_t dt_ms = dt * 1000;  // Czas próbkowania w ms
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

    uint32_t last_pid_time = 0;
    uint32_t last_monitor_time = 0;

    bool safeData = false;
    uint16_t numOfProbes = 0;
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
        if(Rn.new_data_ready){
            switch(Rn.command_type){
                case 1:{ // start sharing data
                    safeData = true;
                    monitorData = false;
                    numOfProbes = Rn.received_number;
                    counter = 0;
                }break;
                case 2:{ // stop
                    safeData = false;
                    monitorData = false;
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
                    constexpr char msg[] = "nie znane polecenie";
                    HAL_UART_Transmit(&huart3, (uint8_t*)msg, strlen(msg), 100);
                }break;
            }
            Rn.new_data_ready = false;
        }

        if (HAL_GetTick() - last_pid_time >= dt_ms)
        {
            last_pid_time = HAL_GetTick(); // Aktualizacja czasu
            now = last_pid_time;

            temperature = BMP280_ReadTemperature();
            temperature = filtrLast(temperature); // if temperature > threshold return last;

            if (temperature <= -90.0f)
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

            u = pid.calculate(yr, temperature);
		    Utest = u;
		    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, u);

            if(safeData){
                logger.log(now, temperature);
                constexpr uint8_t safe_baundry = 50;
                if(counter >= numOfProbes + safe_baundry)
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

        if(monitorData)
        {
            if(HAL_GetTick() - last_monitor_time >= 5000)
            {
                last_monitor_time = HAL_GetTick();
                logger.log(last_monitor_time, temperature);
            }
        }
    }
}
