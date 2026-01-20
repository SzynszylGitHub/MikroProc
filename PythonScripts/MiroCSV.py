import serial
import csv
import matplotlib.pyplot as plt
import time
import sys

# Domyślne ustawienia
DEFAULT_PORT = "COM5"  # Zmień na swój port
DEFAULT_BAUD = 115200
DEFAULT_FILE = "dane_stm32.csv"


def send_command(ser, command):
    """Pomocnicza funkcja do wysyłania komend z nową linią"""
    full_command = command + "\n"
    ser.write(full_command.encode('utf-8'))
    print(f"-> Wysłano: {command.strip()}")


def set_target_temperature(target_val, PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD):
    """
    Wysyła nową nastawę yr do PID.
    Teraz przyjmuje target_val jako argument, zamiast pytać input().
    """
    try:
        # Walidacja czy to liczba (dla pewności, choć GUI też to sprawdzi)
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
        print("Zamknij okno konsoli lub użyj Stop w GUI (jeśli zaimplementowane) aby przerwać.")

        send_command(ser, "/monitor")

        # UWAGA: To jest pętla nieskończona blokująca wątek.
        # W prostym GUI z OpenCV spowoduje to zamrożenie okna,
        # dopóki nie przerwiesz (chyba że użyjesz wątków).
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[STM32]: {line}")
                except UnicodeDecodeError:
                    pass
            time.sleep(0.01)  # Krótszy sleep dla płynności

    except serial.SerialException:
        print(f"Nie można otworzyć portu {PORT}.")
    except KeyboardInterrupt:
        print("\nZatrzymywanie monitorowania...")
        send_command(ser, "/stop")
        ser.close()


def safeData(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD, PLIK_WYNIKOWY=DEFAULT_FILE, expected_data=0):
    """
    Tryb zbierania danych do CSV.
    Usunięto input() pytający o zmianę temperatury i potwierdzenie ENTER.
    Rusza od razu po wywołaniu.
    """
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Otwieram plik {PLIK_WYNIKOWY}...")

        # Usunięto logikę pytania o temperaturę - to robimy osobnym przyciskiem w menu

        print("Rozpoczynam pomiar...")
        command = "/safeData: " + str(expected_data)
        send_command(ser, command)

        time.sleep(0.1)
        ser.reset_input_buffer()
        count = 0
        last_valid_temp = None

        with open(PLIK_WYNIKOWY, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            print("Zapisywanie danych...")
            empty_lines = 0

            while True:
                # Dodano timeout dla pętli odczytu, aby nie wisiała w nieskończoność przy braku danych
                if ser.in_waiting > 0 or True:
                    try:
                        line = ser.readline().decode('utf-8').strip()

                        if not line:
                            empty_lines += 1
                            if empty_lines > 30:  # Zwiększono tolerancję (ok 3 sekundy przy sleep 0.1 w read)
                                print("\n--- Koniec transmisji (timeout) ---")
                                send_command(ser, "/stop")
                                break
                            continue
                        else:
                            empty_lines = 0

                        if line == '10': continue

                        parts = line.split(',')
                        if len(parts) >= 2:
                            try:
                                current_temp = float(parts[1])
                                is_valid = True

                                # --- Prosty filtr ---
                                if last_valid_temp is not None:
                                    diff = abs(current_temp - last_valid_temp)
                                    if diff > max(0.5, abs(last_valid_temp * 0.05)):  # Poluzowany filtr
                                        is_valid = False
                                elif current_temp < -50 or current_temp > 250:
                                    is_valid = False

                                if is_valid:
                                    last_valid_temp = current_temp
                                    writer.writerow(parts)

                                    if expected_data > 0 and count >= expected_data:
                                        print("--- Cel osiągnięty ---")
                                        send_command(ser, "/stop")
                                        break

                                    print(f"#{count}: {line}")
                                    count += 1

                            except ValueError:
                                pass
                    except Exception as e:
                        pass
    except serial.SerialException:
        print(f"Błąd portu {PORT}.")
    except KeyboardInterrupt:
        print("\nPrzerwano.")
        if 'ser' in locals() and ser.is_open:
            send_command(ser, "/stop")
            ser.close()


def createGraph(PLIK_WYNIKOWY=DEFAULT_FILE):
    """Rysuje wykres z pliku"""
    czas = []
    wartosci = []
    try:
        with open(PLIK_WYNIKOWY, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 2:
                    try:
                        czas.append(float(row[0]))
                        wartosci.append(float(row[1]))
                    except ValueError:
                        continue

        if not czas:
            print("Brak danych.")
            return

        plt.figure(figsize=(10, 6))
        plt.plot(czas, wartosci, '-r', label='Temp [C]')
        plt.title("Wykres PID")
        plt.grid(True)
        plt.legend()
        plt.show()  # To otworzy okno matplotlib
    except FileNotFoundError:
        print("Brak pliku.")