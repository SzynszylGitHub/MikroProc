import cv2
import numpy as np
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
import MiroCSV as mcs  # Importujemy poprawiony moduł

# --- KONFIGURACJA GUI ---
BUTTON_WIDTH = 300
BUTTON_HEIGHT = 50
MARGIN = 20
FONT = cv2.FONT_HERSHEY_SIMPLEX

MENU_OPTIONS = [
    ("1. Zbierz probki (n)", '1'),
    ("2. Stworz wykres", '2'),
    ("3. Zbierz i narysuj", '3'),
    ("4. Monitoruj dane", '4'),
    ("5. Ustaw parametry", '5'),  # Zmieniono nazwę
    ("0. Wyjscie", '0')
]

WINDOW_HEIGHT = len(MENU_OPTIONS) * (BUTTON_HEIGHT + MARGIN) + MARGIN
WINDOW_WIDTH = BUTTON_WIDTH + 2 * MARGIN
WINDOW_NAME = "Panel Sterowania"

# Globalne zmienne konfiguracyjne (pamięć między kliknięciami)
CURRENT_PORT = mcs.DEFAULT_PORT
CURRENT_BAUD = mcs.DEFAULT_BAUD

clicked_action = None


def get_settings_dialog():
    """Tworzy okienko do konfiguracji Portu, Baud i Temperatury"""
    result = {}

    root = tk.Tk()
    root.withdraw()  # Ukrywamy główne okno

    dialog = tk.Toplevel(root)
    dialog.title("Ustawienia")
    dialog.geometry("300x300")

    # Layout
    tk.Label(dialog, text="Port (np. COM5):").pack(pady=5)
    e_port = tk.Entry(dialog)
    e_port.insert(0, CURRENT_PORT)
    e_port.pack()

    tk.Label(dialog, text="Baud Rate:").pack(pady=5)
    e_baud = tk.Entry(dialog)
    e_baud.insert(0, str(CURRENT_BAUD))
    e_baud.pack()

    tk.Label(dialog, text="Temp. Zadana (np. 29.0):").pack(pady=5)
    e_temp = tk.Entry(dialog)
    e_temp.pack()
    e_temp.focus_set()

    def on_ok():
        p = e_port.get()
        b = e_baud.get()
        t = e_temp.get()

        if not p or not b or not t:
            messagebox.showwarning("Info", "Wypełnij wszystkie pola")
            return

        try:
            result['port'] = p
            result['baud'] = int(b)
            result['temp'] = float(t.replace(',', '.'))
            root.destroy()
        except ValueError:
            messagebox.showerror("Błąd", "Baud musi być int, Temp float")

    tk.Button(dialog, text="Wyślij", command=on_ok, height=2, bg="#ccc").pack(pady=20, fill='x', padx=20)

    # Czekamy na zamknięcie
    root.wait_window(dialog)
    return result if result else None


def get_samples_dialog():
    """Proste okienko pytające o liczbę próbek"""
    root = tk.Tk()
    root.withdraw()
    # askinteger zwraca int lub None (jak anulujesz)
    val = simpledialog.askinteger("Input", "Ile próbek zebrać? (0 = inf)", initialvalue=1000, parent=root)
    root.destroy()
    return val


def mouse_callback(event, x, y, flags, param):
    global clicked_action
    if event == cv2.EVENT_LBUTTONDOWN:
        for i, (text, action_id) in enumerate(MENU_OPTIONS):
            btn_y = MARGIN + i * (BUTTON_HEIGHT + MARGIN)
            if MARGIN <= x <= MARGIN + BUTTON_WIDTH and btn_y <= y <= btn_y + BUTTON_HEIGHT:
                clicked_action = action_id


def draw_menu():
    img = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
    for i, (text, action_id) in enumerate(MENU_OPTIONS):
        top_left = (MARGIN, MARGIN + i * (BUTTON_HEIGHT + MARGIN))
        bottom_right = (MARGIN + BUTTON_WIDTH, top_left[1] + BUTTON_HEIGHT)

        cv2.rectangle(img, top_left, bottom_right, (80, 80, 80), -1)
        cv2.rectangle(img, top_left, bottom_right, (200, 200, 200), 1)

        text_size = cv2.getTextSize(text, FONT, 0.6, 1)[0]
        text_x = top_left[0] + (BUTTON_WIDTH - text_size[0]) // 2
        text_y = top_left[1] + (BUTTON_HEIGHT + text_size[1]) // 2

        cv2.putText(img, text, (text_x, text_y), FONT, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def main():
    global clicked_action, CURRENT_PORT, CURRENT_BAUD

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    print("GUI Uruchomione...")

    while True:
        frame = draw_menu()
        cv2.imshow(WINDOW_NAME, frame)

        if clicked_action is not None:
            cv2.waitKey(100)  # Efekt kliknięcia

            # --- LOGIKA ---
            match clicked_action:
                case '1':
                    # Okienko zamiast input() w konsoli
                    n = get_samples_dialog()
                    if n is not None:
                        # Wywołujemy funkcję z backendu
                        mcs.safeData(PORT=CURRENT_PORT, BAUD=CURRENT_BAUD, expected_data=n)

                case '2':
                    mcs.createGraph()

                case '3':
                    mcs.safeData(PORT=CURRENT_PORT, BAUD=CURRENT_BAUD, expected_data=5000)
                    mcs.createGraph()

                case '4':
                    # Monitorowanie jest blokujące, więc GUI zamarznie do czasu przerwania (Ctrl+C w konsoli)
                    # Można to naprawić wątkami, ale na razie zostawiamy prosto
                    messagebox.showinfo("Info",
                                        "Monitorowanie uruchomione w konsoli.\nGUI zamarznie.\nUżyj Ctrl+C w konsoli aby przerwać.")
                    mcs.monitorData(PORT=CURRENT_PORT, BAUD=CURRENT_BAUD)

                case '5':
                    # Złożone okno ustawień
                    data = get_settings_dialog()
                    if data:
                        CURRENT_PORT = data['port']
                        CURRENT_BAUD = data['baud']
                        # Wywołanie backendu
                        mcs.set_target_temperature(data['temp'], PORT=CURRENT_PORT, BAUD=CURRENT_BAUD)

                case '0':
                    key = 27
                    break

            clicked_action = None

        key = cv2.waitKey(10)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()
    sys.exit()


if __name__ == "__main__":
    main()