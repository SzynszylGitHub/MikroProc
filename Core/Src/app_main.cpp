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
#include "Transport.hpp"

extern "C"{
	extern UART_HandleTypeDef huart3;
	extern I2C_HandleTypeDef hi2c1;
	extern TIM_HandleTypeDef htim1;
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
constexpr std::size_t RX_BUFFER_SIZE =  10; // maksymalny rozmiar wiadomosci
uint8_t rx_byte;              // Tu wpada 1 znak
char rx_buffer[RX_BUFFER_SIZE]; // Tu zbieramy napis
uint8_t rx_index = 0;         // Licznik pozycji w buforze

extern "C" void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3) {

        // Sprawdzamy znak końca linii
        if (rx_byte == '\n' || rx_byte == '\r') {

            rx_buffer[rx_index] = '\0';

//            if (rx_index > 0) {
//
//                if (std::strcmp(rx_buffer, "/safe data") == 0) {
//                    Rn.command_type = 1;
//                    Rn.new_data_ready = true;
//                }
//                else if (std::strcmp(rx_buffer, "/stop") == 0) {
//                    Rn.command_type = 2;
//                    Rn.new_data_ready = true;
//                }
//                else if (std::strcmp(rx_buffer, "/monitor") == 0){
//                	Rn.command_type = 3;
//                	Rn.new_data_ready = true;
//                }
//                else if (std::sscanf(rx_buffer, "/set yr: %f", &Rn.receive_float_number) == 1) {
//                    Rn.command_type = 4;
//                    Rn.new_data_ready = true;
//                }
//                else {
//                    Rn.received_number = std::atoi(rx_buffer);
//                    Rn.command_type = 0;
//                    Rn.new_data_ready = true;
//                }
//            }

            // Resetujemy bufor
            rx_index = 0;

        } else {
            // Zbieranie znaków do bufora
            if (rx_index < RX_BUFFER_SIZE - 1) {
                rx_buffer[rx_index++] = (char)rx_byte;
            }
        }

        // Ponowny nasłuch przerwania
        HAL_UART_Receive_IT(&huart3, &rx_byte, 1);
    }
}// -------------------------------------------------------------------------------------------------------
// nastawy PID narazie sa i tle
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

	// uruchomienie czujnika
	BMP280_Init(&hi2c1, BMP280_TEMPERATURE_16BIT, BMP280_STANDARD, BMP280_FORCEDMODE);

	// ======================================
	// transfer data mechanism
	CsvLogger logger(&huart3);
	uint32_t now = 0;

	bool safeData = false;
	bool monitorData = false;
	// ======================================

	// ======================================================
	// data to test safe mechanism
	float fake_data[] = {
	#include "../../PythonScripts/wynik.txt"
	};
	uint16_t idx = 0;
	// ======================================================


	// ======================================================
	// regulacja PID
	PID pid(dt,max_pwm,min_pwm,Kp,Ki,Kd,Tf);
	float yr = 28.f;
	float u = 0.f;
	// ======================================================
	while(true)
	{
// oczekujemy lepszej bramki np: nmos IRLML6402
		//BMP280_ReadTemperatureAndPressure(&temperature, &pressure);
		temperature = BMP280_ReadTemperature();
		u = pid.calculate(yr,temperature);
		Utest = u;
		__HAL_TIM_SET_COMPARE(&htim1 , TIM_CHANNEL_1 ,u);
		HAL_Delay(1000);

//		// obsluga komend
//				if(Rn.new_data_ready){
//					switch(Rn.command_type){
//						case 1:{ // start sharing data
//							safeData = true;
//						}break;
//						case 2:{ // stop sharing data
//							safeData = false;
//							monitorData = false;
//						}break;
//						case 3:{ // monitor data
//							monitorData = true;
//						}break;
//						case 4:{
//							yr = Rn.receive_float_number;
//						}
//						default:{// potwierdzenie odebrania wiadomosci
//							std::string msg = std::to_string(Rn.received_number);
//							HAL_UART_Transmit(&huart3, (uint8_t*)msg.c_str(), msg.length(), 100);
//						}break;
//					}
//					// pod odczycie zmieniamy wartosc na odczytana
//					Rn.new_data_ready = false;
//				}
//
//				if(safeData){
//					logger.log(now,fake_data[idx]);
//					idx++;
//
//					if(idx > 500){
//						safeData = false;
//						idx = 0;
//					}
//				}
//
//				if(monitorData)
//				{
//					now = HAL_GetTick();
//					logger.log(now,fake_data[idx]);
//					idx++;
//					if(idx > 500){
//						safeData = false;
//						idx = 0;
//					}
//					HAL_Delay(5000); // delay miedzy wiadomosciami 5 sek, aby nie zaspamic
//				}

	}
}
