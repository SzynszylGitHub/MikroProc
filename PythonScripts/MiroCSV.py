import serial
import csv
import matplotlib.pyplot as plt
import time
import sys

# Domyślne ustawienia
DEFAULT_PORT = "COM5"  # Sprawdź w Menedżerze urządzeń
DEFAULT_BAUD = 115200
DEFAULT_FILE = "dane_stm32.csv"


def send_command(ser, command):
    """Pomocnicza funkcja do wysyłania komend z nową linią"""
    full_command = command + "\n"
    ser.write(full_command.encode('utf-8'))
    print(f"-> Wysłano: {command.strip()}")


def set_target_temperature(target_val, PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD):
    """Wysyła nową nastawę yr do PID."""
    try:
        val = float(target_val)
        with serial.Serial(PORT, BAUD, timeout=1) as ser:
            cmd = f"/set yr: {val}"
            send_command(ser, cmd)
            time.sleep(0.5)
            print(f"Nastawa zaktualizowana na: {val}")

    except ValueError:
        print("Błąd: Podana wartość nie jest liczbą.")
    except serial.SerialException:
        print(f"Błąd portu {PORT}.")


def monitorData(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD):
    """Tryb podglądu (wysyła /monitor)"""
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Tryb MONITOROWANIA.")
        print("Ctrl+C aby przerwać.")

        send_command(ser, "/monitor")

        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[STM32]: {line}")
                except UnicodeDecodeError:
                    pass
            time.sleep(0.01)

    except serial.SerialException:
        print(f"Nie można otworzyć portu {PORT}.")
    except KeyboardInterrupt:
        print("\nZatrzymywanie monitorowania...")
        if 'ser' in locals() and ser.is_open:
            send_command(ser, "/stop")
            ser.close()


def safeData(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD, PLIK_WYNIKOWY=DEFAULT_FILE, expected_data=0):
    """
    Wersja poprawiona: Odporna na reset STM32, parsująca format Tick,Temp,U
    Zawiera filtr odrzucający skoki temperatury > 10%.
    """
    try:
        print(f"1. Otwieram port {PORT}...")
        ser = serial.Serial(PORT, BAUD, timeout=1)

        print("2. Czekam 2 sekundy na restart STM32...")
        time.sleep(2.0)
        ser.reset_input_buffer()

        print("3. Wysyłam komendę startu...")
        command = "/safeData: " + str(expected_data)
        send_command(ser, command)

        print(f"4. Nasłuchuję danych. Zapis do: {PLIK_WYNIKOWY}")
        print("   (Format: Tick, Temp, U. Filtr: max 10% skoku)")

        # Zmienna do przechowywania ostatniej dobrej temperatury
        last_valid_temp = None

        with open(PLIK_WYNIKOWY, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            count = 0
            empty_lines = 0

            while True:
                try:
                    line_bytes = ser.readline()
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except serial.SerialException:
                    print("Błąd odczytu portu.")
                    break

                if not line:
                    empty_lines += 1
                    if empty_lines > 10:
                        pass
                    continue

                empty_lines = 0

                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        try:
                            tick_val = float(parts[0])
                            temp_val = float(parts[1])
                            u_val = float(parts[2])

                            # --- SEKCJA FILTRACJI ---
                            accept_sample = True

                            if last_valid_temp is not None:
                                # Obliczamy dopuszczalny błąd (10% ostatniej wartości)
                                # Używamy max(1.0, ...), żeby nie zablokować się przy temperaturze bliskiej 0
                                margin = max(1.0, abs(last_valid_temp * 0.10))

                                diff = abs(temp_val - last_valid_temp)

                                if diff > margin:
                                    print(
                                        f"    [FILTR] Odrzucono skok: {last_valid_temp:.2f} -> {temp_val:.2f} (Delta: {diff:.2f})")
                                    accept_sample = False

                            # Opcjonalnie: Odrzuć nierealne wartości na start (np. błędy czujnika -999 lub 5000)
                            if accept_sample and (temp_val < -50 or temp_val > 500):
                                print(f"    [FILTR] Odrzucono zakres: {temp_val:.2f}")
                                accept_sample = False

                            if accept_sample:
                                # Aktualizujemy ostatnią poprawną temperaturę
                                last_valid_temp = temp_val

                                writer.writerow([tick_val, temp_val, u_val])
                                print(f"#{count} [{tick_val}] T={temp_val:.2f} | U={u_val:.2f}")

                                count += 1
                                if expected_data > 0 and count >= expected_data:
                                    print("--- Cel osiągnięty ---")
                                    send_command(ser, "/stop")
                                    break
                            # ------------------------

                        except ValueError:
                            print(f"Ignoruję linię (nie liczby): {line}")
                            pass
                    else:
                        print(f"Niepełna linia: {line}")
                else:
                    print(f"INFO z STM32: {line}")

    except serial.SerialException:
        print(f"Błąd: Nie można otworzyć portu {PORT}.")
    except KeyboardInterrupt:
        print("\nZatrzymano przez użytkownika.")
        if 'ser' in locals() and ser.is_open:
            send_command(ser, "/stop")
            ser.close()

def createGraph(PLIK_WYNIKOWY=DEFAULT_FILE):
    """Rysuje wykres Temp i U na dwóch osiach Y"""
    czas = []
    temp = []
    sterowanie = []

    try:
        with open(PLIK_WYNIKOWY, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Oczekujemy co najmniej 3 kolumn
                if len(row) >= 3:
                    try:
                        czas.append(float(row[0]))
                        temp.append(float(row[1]))
                        sterowanie.append(float(row[2]))
                    except ValueError:
                        continue
                # Kompatybilność wsteczna (gdyby w pliku były stare dane 2-kolumnowe)
                elif len(row) == 2:
                    try:
                        czas.append(float(row[0]))
                        temp.append(float(row[1]))
                        sterowanie.append(0)  # Brak danych o U
                    except ValueError:
                        continue

        if not czas:
            print("Brak danych w pliku do wyrysowania.")
            return

        # Tworzenie wykresu z dwiema osiami Y
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Oś temperatury (lewa, czerwona)
        color = 'tab:red'
        ax1.set_xlabel('Czas [s]')
        ax1.set_ylabel('Temperatura [C]', color=color)
        ax1.plot(czas, temp, color=color, label='Temp')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle='--', alpha=0.6)

        # Oś sterowania (prawa, niebieska)
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Sterowanie U', color=color)
        ax2.plot(czas, sterowanie, color=color, linestyle='-', alpha=0.5, label='U')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title("Wykres PID: Temperatura i Sterowanie")
        fig.tight_layout()  # Żeby napisy się nie nakładały
        plt.show()

    except FileNotFoundError:
        print(f"Nie znaleziono pliku {PLIK_WYNIKOWY}.")


# Przykład użycia (jeśli uruchamiasz ten plik bezpośrednio)
if __name__ == "__main__":
    # createGraph() # Odkomentuj by przetestować sam wykres
    pass