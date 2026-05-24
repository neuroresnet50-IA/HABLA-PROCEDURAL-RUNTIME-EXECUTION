import tkinter as tk
from tkinter import messagebox

class JuegoAlgebraLineal:
    def __init__(self, root):
        self.root = root
        self.root.title("Reto de Álgebra Lineal")
        self.root.geometry("500x400")
        self.root.configure(bg="#f0f0f0")

        # Base de datos de preguntas
        self.preguntas = [
            {
                "enunciado": "¿Qué caracteriza a un vector unitario?",
                "opciones": ["Su magnitud es exactamente 1", "Su dirección es siempre horizontal", "No tiene sentido", "Es el vector nulo"],
                "correcta": 0
            },
            {
                "enunciado": "En el espacio tridimensional (R³), ¿cuántas coordenadas definen la posición de un punto?",
                "opciones": ["2 coordenadas", "3 coordenadas", "4 coordenadas", "Infinitas"],
                "correcta": 1
            },
            {
                "enunciado": "Si r(t) es una función vectorial de posición, ¿qué representa físicamente su derivada r'(t)?",
                "opciones": ["La curvatura", "La aceleración", "El vector tangente (velocidad)", "El plano normal"],
                "correcta": 2
            },
            {
                "enunciado": "¿Cuál es el resultado del producto punto de dos vectores perpendiculares?",
                "opciones": ["Uno (1)", "El vector nulo", "Cero (0)", "Un vector ortogonal"],
                "correcta": 2
            },
            {
                "enunciado": "¿Qué operación entre dos vectores en R³ da como resultado un tercer vector perpendicular a ambos?",
                "opciones": ["Producto punto", "Suma de vectores", "Producto escalar", "Producto cruz (o vectorial)"],
                "correcta": 3
            }
        ]

        self.indice = 0
        self.puntos = 0

        # Elementos de la interfaz
        self.lbl_pregunta = tk.Label(root, text="", font=("Arial", 12, "bold"), wraplength=400, bg="#f0f0f0", pady=20)
        self.lbl_pregunta.pack()

        self.botones = []
        for i in range(4):
            btn = tk.Button(root, text="", font=("Arial", 10), width=40, command=lambda i=i: self.validar(i))
            btn.pack(pady=10)
            self.botones.append(btn)

        self.mostrar_pregunta()

    def mostrar_pregunta(self):
        if self.indice < len(self.preguntas):
            p = self.preguntas[self.indice]
            self.lbl_pregunta.config(text=p["enunciado"])
            for i in range(4):
                self.botones[i].config(text=p["opciones"][i])
        else:
            messagebox.showinfo("Fin", f"Juego terminado. Puntaje: {self.puntos}/5")
            self.root.quit()

    def validar(self, seleccion):
        if seleccion == self.preguntas[self.indice]["correcta"]:
            self.puntos += 1
            messagebox.showinfo("¡Bien!", "Respuesta correcta.")
        else:
            messagebox.showerror("Error", "Respuesta incorrecta.")
        
        self.indice += 1
        self.mostrar_pregunta()

if __name__ == "__main__":
    root = tk.Tk()
    app = JuegoAlgebraLineal(root)
    root.mainloop()
