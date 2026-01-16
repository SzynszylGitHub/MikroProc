import serial
import csv
import matplotlib.pyplot as plt

def safeData(PORT = "COM5",BAUD = 115200 ,PLIK_WYNIKOWY = "dane_stm32.csv"):
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Połączono z {PORT}. Zapisuję do {PLIK_WYNIKOWY}...")
        print("Naciśnij Ctrl+C, aby zakończyć.")

        with open(PLIK_WYNIKOWY, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Opcjonalnie: dodaj nagłówek, jeśli CsvLogger go nie wysyła
            # writer.writerow(['Czas_ms', 'Napiecie_V'])

            while True:
                if ser.in_waiting > 0:
                    # Odczyt linii z STM32
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(line)  # Podgląd na ekranie
                        # Zapis do pliku (dzielimy po przecinku)
                        parts = line.split(',')
                        if len(parts) >= 2:
                            writer.writerow(parts)

    except serial.SerialException:
        print(f"Błąd: Nie można otworzyć portu {PORT}. Sprawdź czy nie jest zajęty.")
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
    wybor = input("Wybierz opcję: [1]\nZbieraj dane, [2] Rysuj wykres \n "
                  "[3] Zbierz dane i wyrysuj Wykres\n"
                  "twoja odpowiedz: ")

    match wybor:
        case '1':
            safeData()  # Uruchamia Twoją funkcję zbierania
        case '2':
            createGraph()  # Uruchamia funkcję rysowania
        case '3':
            safeData()
            createGraph()
        case _:
            print("Nieznana opcja.")
