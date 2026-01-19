/*
 * app_main.cpp
 *
 *  Created on: Dec 27, 2025
 *      Author: Szynszyl
 */
#include "app_main.hpp"
#include "main.h"
#include <cstdlib>
#include <string>
#include <numeric>
#include "BMPXX80.h"
#include "PID.hpp"

extern "C"{
	extern UART_HandleTypeDef huart3;
	extern I2C_HandleTypeDef hi2c1;
	extern TIM_HandleTypeDef htim1;
	extern float temperature;
	extern long pressure;
	extern float Utest;
}
// komunikacja
// ========================================================
struct ValueReceive{
	int received_number = 0;
	bool new_number_ready = false;
};

volatile ValueReceive Rn;

// ----------------------------------- C style ------------------------------------
constexpr std::size_t RX_BUFFER_SIZE =  10; // maksymalny rozmiar wiadomosci
uint8_t rx_byte;              // Tu wpada 1 znak
char rx_buffer[RX_BUFFER_SIZE]; // Tu zbieramy napis
uint8_t rx_index = 0;         // Licznik pozycji w buforze

extern "C" void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{

	if (huart->Instance == USART3) {

        if (rx_byte == '\n' || rx_byte == '\r') {

            rx_buffer[rx_index] = '\0';

            if (rx_index > 0) {
                Rn.received_number = std::atoi(rx_buffer);
                Rn.new_number_ready = true;
            }

            rx_index = 0;
           // memset(rx_buffer, 0, RX_BUFFER_SIZE);


        } else {
            if (rx_index < RX_BUFFER_SIZE - 1) {
                rx_buffer[rx_index++] = (char)rx_byte;
            }
        }

        HAL_UART_Receive_IT(&huart3, &rx_byte, 1);
    }
}
// -------------------------------------------------------------------------------------------------------
// nastawy PID
//==========================================================================
constexpr float dt = 0.1;
constexpr int dt_sleep = dt*1000;
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
	BMP280_Init(&hi2c1, BMP280_TEMPERATURE_16BIT, BMP280_STANDARD, BMP280_FORCEDMODE);

	PID pid(dt,max_pwm,min_pwm,Kp,Ki,Kd,Tf);
	float yr = 25;
	uint16_t u = 0;
	uint16_t lu = 0;
	float lt = 0;
	uint32_t time_stemp = 0;
	uint32_t last_time = 0 ;

	while(1)
	{
// oczekujemy lepszej bramki np: nmos IRLML6402
		//BMP280_ReadTemperatureAndPressure(&temperature, &pressure);
		temperature = BMP280_ReadTemperature();

		    // SPRAWDZENIE BŁĘDU I RESET I2C
		    if (temperature == -99)
		    {
		        // 1. Opcjonalnie: mrugnij diodą, żebyś widział, że był błąd
		        //HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);

		        // 2. Resetujemy interfejs I2C
		        HAL_I2C_DeInit(&hi2c1);  // Wyłącz I2C (zwolnij piny)
		        HAL_Delay(10);           // Krótka przerwa
		        HAL_I2C_Init(&hi2c1);    // Włącz I2C na nowo (zastąp &hi2c1 swoją nazwą)

		        // 3. Ewentualnie ponowna inicjalizacja czujnika, jeśli wymaga
		        BMP280_Init(&hi2c1, BMP280_TEMPERATURE_16BIT, BMP280_STANDARD, BMP280_FORCEDMODE);


		        HAL_Delay(100); // Daj chwilę na ustabilizowanie
		        continue;       // Spróbuj ponownie w następnej pętli
		    }

		    // Dalsza część kodu wykonuje się tylko, jeśli pomiar był OK
		    u = pid.calculate(yr, temperature);
		    Utest = u;
		    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, u);

		// potwierdzenie odebrania wiadomosci
		if(lu != u || lt != temperature) {

			//int number_to_process = Rn.received_number;
			//Rn.new_number_ready = false;

			std::string msg = "u:{"+ std::to_string(int(u)) + "},t:{" + std::to_string(int(temperature)) + "}";
			HAL_UART_Transmit(&huart3, (uint8_t*)msg.c_str(), msg.length(), 100);

		}

		if(time_stemp >= last_time + 1000)
		{
			std::string msg = "time:" + std::to_string(time_stemp);
			HAL_UART_Transmit(&huart3, (uint8_t*)msg.c_str(), msg.length(), 100);
			last_time = time_stemp;
		}

		time_stemp += dt_sleep;
		HAL_Delay(dt_sleep);
	}
}


