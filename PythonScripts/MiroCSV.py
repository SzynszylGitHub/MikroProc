import serial
import csv
import matplotlib.pyplot as plt
import time

def safeData(PORT="COM5", BAUD=115200, PLIK_WYNIKOWY="dane_stm32.csv", expected_data = 0):
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Otwieram plik {PLIK_WYNIKOWY}...")

        input("Naciśnij ENTER, aby wysłać komendę /safe data i rozpocząć pomiar...")

        ser.write(b'/safe data\n')
        print("Wysłano komendę startu. Czekam na dane...")

        time.sleep(0.1)
        ser.reset_input_buffer()
        count = 0
        with open(PLIK_WYNIKOWY, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            print("Zapisywanie danych (Ctrl+C aby przerwać)...")

            while True:
                if ser.in_waiting > 0:
                    try:
                        # Odczyt linii
                        line = ser.readline().decode('utf-8').strip()

                        # Czasami STM może odesłać echo komendy "10", ignorujemy to
                        if line == '10' or line == '':
                            continue

                        if count == 0.2*expected_data:
                            print("20% compled")
                        if count == 0.4 * expected_data:
                            print("40% compled")
                        if count == 0.6 * expected_data:
                            print("60% compled")
                        if count == 0.8 * expected_data:
                            print("80% compled")
                        if count == expected_data:
                            print("100% compled")
                            break

                        print(line)  # Podgląd

                        parts = line.split(',')
                        if len(parts) >= 2:
                            writer.writerow(parts)
                            count = count + 1

                    except UnicodeDecodeError:
                        # Czasami na początku wpadają śmieci, ignorujemy błąd dekodowania
                        pass

    except serial.SerialException:
        print(f"Błąd: Nie można otworzyć portu {PORT}. Upewnij się, że inne programy (RealTerm, Putty) są ZAMKNIĘTE.")
    except KeyboardInterrupt:
        print("\nZakończono zbieranie danych.")
        if 'ser' in locals() and ser.is_open:
            ser.close()


def createGraph(PLIK_WYNIKOWY="dane_stm32.csv"):
    czas = []
    wartosci = []

    print(f"Wczytuję dane z pliku: {PLIK_WYNIKOWY}...")

    try:
        with open(PLIK_WYNIKOWY, 'r') as csvfile:
            reader = csv.reader(csvfile)

            for row in reader:
                # Sprawdzamy, czy wiersz ma co najmniej 2 elementy
                if len(row) >= 2:
                    try:
                        # Konwersja tekstu na liczby
                        t = float(row[0])  # Pierwsza kolumna to czas (ms)
                        v = float(row[1])  # Druga kolumna to wartość

                        czas.append(t)
                        wartosci.append(v)
                    except ValueError:
                        # Ignorujemy linie, które nie są liczbami (np. nagłówki)
                        continue

        if not czas:
            print("Plik jest pusty lub nie zawiera poprawnych danych liczbowych.")
            return

        # --- Rysowanie Wykresu ---
        plt.figure(figsize=(10, 6))  # Rozmiar okna (opcjonalne)

        # Rysujemy: oś X, oś Y, styl linii (b- = blue line, o = kropki)
        plt.plot(czas, wartosci, linestyle='-', color='blue', label='Sygnał')

        # Opcjonalnie: Konwersja czasu na sekundy (jeśli STM32 wysyła ms)
        # plt.plot([t/1000 for t in czas], wartosci, ...)

        plt.title("Wykres danych z STM32")
        plt.xlabel("Czas [ms]")  # lub [s]
        plt.ylabel("Wartość")
        plt.grid(True)  # Siatka ułatwiająca odczyt
        plt.legend()

        print("Wyświetlam wykres...")
        plt.show()  # To polecenie otwiera okno z wykresem

    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku '{PLIK_WYNIKOWY}'. Uruchom najpierw safeData().")


if __name__ == "__main__":
    wybor = input("Wybierz opcję: \n [1] Zbieraj dane\n [2] Rysuj wykres\n"
                  " [3] Zbierz dane i wyrysuj Wykres\n [4] Odczytuj aktualne wartosci\n"
                  "twoja odpowiedz: ")

    match wybor:
        case '1':
            safeData(expected_data=990)  # Uruchamia Twoją funkcję zbierania
        case '2':
            createGraph()  # Uruchamia funkcję rysowania
        case '3':
            safeData(expected_data=990)
            createGraph()
        case '4':
            pass

        case _:
            print("Nieznana opcja.")
