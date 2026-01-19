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


def set_target_temperature(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD):
    """Wysyła nową nastawę yr do PID"""
    try:
        target = input("Podaj nową temperaturę zadaną (np. 35.5): ")
        # Walidacja czy to liczba
        float(target)

        with serial.Serial(PORT, BAUD, timeout=1) as ser:
            # Format zgodny z Twoim sscanf: "/set yr: %f"
            cmd = f"/set yr: {target}"
            send_command(ser, cmd)
            time.sleep(0.5)  # Czekamy na ewentualne potwierdzenie
            print("Nastawa zaktualizowana.")

    except ValueError:
        print("Błąd: Podana wartość nie jest liczbą.")
    except serial.SerialException:
        print(f"Błąd portu {PORT}.")


def monitorData(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD):
    """Tryb podglądu (wysyła /monitor) - odczyt co 5s"""
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Tryb MONITOROWANIA.")
        print("Naciśnij Ctrl+C, aby zakończyć.")

        # Wyślij komendę monitor
        send_command(ser, "/monitor")

        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[STM32]: {line}")
                except UnicodeDecodeError:
                    pass
            time.sleep(0.1)

    except serial.SerialException:
        print(f"Nie można otworzyć portu {PORT}.")
    except KeyboardInterrupt:
        print("\nZatrzymywanie monitorowania...")
        send_command(ser, "/stop")  # Ważne: Wyłączamy grzanie przy wyjściu
        ser.close()


def safeData(PORT=DEFAULT_PORT, BAUD=DEFAULT_BAUD, PLIK_WYNIKOWY=DEFAULT_FILE, expected_data=0):
    """Tryb zbierania danych do CSV (wysyła /safeData) z filtrowaniem zakłóceń"""
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Otwieram plik {PLIK_WYNIKOWY}...")

        # Opcjonalnie zapytaj o zmianę temperatury przed startem
        change_temp = input("Czy chcesz ustawić nową temp. zadaną przed startem? (t/n): ")
        if change_temp.lower() == 't':
            val = input("Podaj temp: ")
            send_command(ser, f"/set yr: {val}")
            time.sleep(0.5)

        input("Naciśnij ENTER, aby wysłać komendę /safeData i rozpocząć pomiar...")

        send_command(ser, "/safeData")
        print("Czekam na dane...")

        time.sleep(0.1)
        ser.reset_input_buffer()
        count = 0

        # ZMIENNA DO FILTROWANIA
        last_valid_temp = None

        with open(PLIK_WYNIKOWY, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            print("Zapisywanie danych (Ctrl+C aby przerwać)...")

            # Licznik ciszy (timeoutu transmisji)
            empty_lines = 0

            while True:
                if ser.in_waiting > 0 or True:  # Wymuszamy wejście do readline
                    try:
                        line = ser.readline().decode('utf-8').strip()

                        # --- DETEKCJA KONCA TRANSMISJI ---
                        if not line:
                            empty_lines += 1
                            if empty_lines > 3:  # Jeśli 3 razy z rzędu (3 sekundy) pusto
                                print("\n--- Wykryto koniec transmisji (timeout) ---")
                                print(f"Odebrano {count} z oczekiwanych {expected_data} próbek.")
                                send_command(ser, "/stop")
                                break
                            continue  # Pusta linia, próbujemy dalej
                        else:
                            empty_lines = 0  # Resetujemy licznik, bo przyszły dane
                        # ----------------------------------

                        # Ignorujemy echo "10"
                        if line == '10':
                            continue

                        # Parsowanie danych
                        parts = line.split(',')

                        if len(parts) >= 2:
                            try:
                                current_temp = float(parts[1])

                                # --- FILTR ANTY-ZAKŁÓCENIOWY (30%) ---
                                is_valid = True

                                if last_valid_temp is not None:
                                    # Obliczamy dopuszczalną zmianę (30% poprzedniej wartości)
                                    # Dodajemy minimalny próg 2 stopnie, żeby nie blokować zmian przy małych wartościach (np. start od 0)
                                    threshold = abs(last_valid_temp * 0.003)
                                    if threshold < 0.5:
                                        threshold = 0.5

                                    diff = abs(current_temp - last_valid_temp)

                                    if diff > threshold:
                                        print(
                                            f" [FILTR] Odrzucono zakłócenie: {current_temp} (Poprzednia: {last_valid_temp})")
                                        is_valid = False

                                # Pierwsza próbka - odrzucamy tylko skrajne błędy (np. -99 lub > 200)
                                elif last_valid_temp is None:
                                    if current_temp < -50 or current_temp > 200:
                                        is_valid = False

                                # Decyzja o zapisie
                                if is_valid:
                                    last_valid_temp = current_temp  # Aktualizujemy wzorzec
                                    writer.writerow(parts)

                                    # Logika paska postępu
                                    if expected_data > 0:
                                        if count >= expected_data:
                                            print("--- 100% Zakończono ---")
                                            send_command(ser, "/stop")
                                            break

                                    print(f"#{count}: {line}")
                                    count += 1
                                else:
                                    # Jeśli odrzucono, nie zwiększamy licznika 'count'
                                    continue

                            except ValueError:
                                pass  # Błąd konwersji float, ignorujemy linię

                    except UnicodeDecodeError:
                        print("! Błąd dekodowania ramki (pominięto) !")
                        pass
                    except ValueError:
                        pass

    except serial.SerialException:
        print(f"Błąd: Nie można otworzyć portu {PORT}. Zamknij inne terminale.")
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika.")
        if 'ser' in locals() and ser.is_open:
            send_command(ser, "/stop")  # Bezpieczne wyłączenie grzałki
            ser.close()
            print("Wysłano /stop i zamknięto port.")


def createGraph(PLIK_WYNIKOWY=DEFAULT_FILE):
    czas = []
    wartosci = []

    print(f"Wczytuję dane z pliku: {PLIK_WYNIKOWY}...")

    try:
        with open(PLIK_WYNIKOWY, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 2:
                    try:
                        t = float(row[0])
                        v = float(row[1])
                        czas.append(t)
                        wartosci.append(v)
                    except ValueError:
                        continue

        if not czas:
            print("Brak poprawnych danych do wyrysowania.")
            return

        plt.figure(figsize=(10, 6))
        # Rysujemy samą linię, bez kropek dla czytelności przy dużej ilości danych
        plt.plot(czas, wartosci, linestyle='-', color='red', label='Temperatura [C]')

        plt.title("Wykres PID - STM32")
        plt.xlabel("Czas [ms]")
        plt.ylabel("Temperatura [C]")
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.legend()
        plt.tight_layout()
        print("Wyświetlam wykres...")
        plt.show()

    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku '{PLIK_WYNIKOWY}'.")


if __name__ == "__main__":
    while True:
        print("\n--- MENU STEROWANIA STM32 ---")
        print(" [1] Zbieraj dane (/safeData -> CSV)")
        print(" [2] Rysuj wykres z pliku")
        print(" [3] Zbierz dane i od razu rysuj")
        print(" [4] Monitoruj dane na żywo (/monitor)")
        print(" [5] Ustaw temperaturę zadaną (/set yr)")
        print(" [0] Wyjście")

        wybor = input("Twój wybór: ")

        match wybor:
            case '1':
                # Pytamy ile próbek
                try:
                    n = int(input("Ile próbek zebrać? (wpisz 0 dla pętli nieskończonej): ") or 1000)
                except:
                    n = 1000
                safeData(expected_data=n)
            case '2':
                createGraph()
            case '3':
                safeData(expected_data=1000)
                createGraph()
            case '4':
                monitorData()
            case '5':
                set_target_temperature()
            case '0':
                print("Do widzenia.")
                sys.exit()
            case _:
                print("Nieznana opcja.")