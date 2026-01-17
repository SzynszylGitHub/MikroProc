import numpy as np

def zapisz_do_c_include(tablica, nazwa_pliku, elementy_w_wierszu=10):
    with open(nazwa_pliku, 'w') as f:
        dlugosc = len(tablica)

        for i, wartosc in enumerate(tablica):
            # Formatowanie:
            # Użyj str(wartosc) dla liczb dziesiętnych (int/float)
            # Użyj f"0x{wartosc:02X}" dla hexów (np. bajtów)

            f.write(str(wartosc))

            # Dodaj przecinek, jeśli to nie jest ostatni element
            if i < dlugosc - 1:
                f.write(", ")

            # Złam linię co N elementów (dla czytelności)
            if (i + 1) % elementy_w_wierszu == 0:
                f.write("\n")


def foo():
    start,stop,precision = [0,10,1000]
    t = np.linspace(start, stop,precision)

    table = 20*np.sin(60*t)
    zapisz_do_c_include(table,"wynik.txt",20)



if __name__ == "__main__":
    foo()