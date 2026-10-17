"""Bulle d'état toujours visible (veille / écoute / réflexion / parole) et bips sonores."""

import queue
import threading

ETATS = {
    "veille": ("#6b7280", "En veille"),
    "ecoute": ("#3b82f6", "Je t'écoute…"),
    "reflexion": ("#f59e0b", "Je réfléchis…"),
    "action": ("#a855f7", "J'agis…"),
    "parle": ("#10b981", "Jarvis parle"),
    "erreur": ("#ef4444", "Problème"),
}


class Interface:
    def __init__(self, bulle: bool, sons: bool, astuce_veille: str):
        self.bulle = bulle
        self.sons = sons
        self.astuce_veille = astuce_veille
        self._file = queue.Queue()

    # ------------------------------------------------------------ appelé par Jarvis

    def etat(self, nom: str, detail: str = "") -> None:
        if nom == "veille" and not detail:
            detail = self.astuce_veille
        self._file.put((nom, detail))

    def bip(self, montant: bool = True) -> None:
        """Bip court : montant = « je t'écoute », descendant = « j'ai fini d'écouter »."""
        if not self.sons:
            return
        try:
            import numpy as np
            import sounddevice as sd

            taux = 44100
            notes = (660, 990) if montant else (880, 550)
            sons = []
            for frequence in notes:
                t = np.linspace(0, 0.07, int(taux * 0.07), endpoint=False)
                enveloppe = np.minimum(1, np.minimum(t, 0.07 - t) * 200)  # évite les « clics »
                sons.append(0.25 * np.sin(2 * np.pi * frequence * t) * enveloppe)
            sd.play(np.concatenate(sons).astype(np.float32), taux)
            sd.wait()  # sinon le micro capterait le bip
        except Exception:
            pass

    # ------------------------------------------------------------------ boucle

    def lancer(self, programme) -> None:
        """Lance `programme` ; s'il y a une bulle, elle tourne dans le fil principal."""
        if not self.bulle:
            programme()
            return
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print("(bulle d'état indisponible : tkinter manquant)")
            programme()
            return
        fil = threading.Thread(target=self._programme_puis_fermer, args=(programme,), daemon=True)
        fil.start()
        self._fenetre()

    def _programme_puis_fermer(self, programme) -> None:
        try:
            programme()
        finally:
            self._file.put(("__fin__", ""))

    def _fenetre(self) -> None:
        import tkinter as tk

        racine = tk.Tk()
        racine.overrideredirect(True)  # pas de barre de titre
        racine.attributes("-topmost", True)
        racine.attributes("-alpha", 0.93)
        fond = "#111827"
        racine.configure(bg=fond)
        largeur, hauteur = 460, 64
        x = (racine.winfo_screenwidth() - largeur) // 2
        y = racine.winfo_screenheight() - hauteur - 80
        racine.geometry(f"{largeur}x{hauteur}+{x}+{y}")

        toile = tk.Canvas(racine, width=48, height=hauteur, bg=fond, highlightthickness=0)
        toile.pack(side="left")
        pastille = toile.create_oval(16, 20, 40, 44, fill=ETATS["veille"][0], outline="")
        textes = tk.Frame(racine, bg=fond)
        textes.pack(side="left", fill="both", expand=True, pady=8)
        titre = tk.Label(textes, text="Démarrage…", fg="white", bg=fond, anchor="w",
                         font=("Segoe UI", 12, "bold"))
        titre.pack(fill="x")
        detail = tk.Label(textes, text="", fg="#9ca3af", bg=fond, anchor="w",
                          font=("Segoe UI", 9))
        detail.pack(fill="x")

        # Déplacer la bulle à la souris ; clic droit pour quitter.
        def debut(e):
            racine._dx, racine._dy = e.x_root - racine.winfo_x(), e.y_root - racine.winfo_y()

        def bouger(e):
            racine.geometry(f"+{e.x_root - racine._dx}+{e.y_root - racine._dy}")

        menu = tk.Menu(racine, tearoff=0)
        menu.add_command(label="Quitter Jarvis", command=racine.destroy)
        for w in (racine, toile, textes, titre, detail):
            w.bind("<ButtonPress-1>", debut)
            w.bind("<B1-Motion>", bouger)
            w.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        etat_courant = {"nom": "veille", "tic": 0}

        def rafraichir():
            try:
                while True:
                    nom, texte = self._file.get_nowait()
                    if nom == "__fin__":
                        racine.destroy()
                        return
                    couleur, libelle = ETATS.get(nom, ETATS["veille"])
                    etat_courant["nom"] = nom
                    toile.itemconfig(pastille, fill=couleur)
                    titre.config(text=libelle)
                    detail.config(text=_raccourcir(texte, 70))
            except queue.Empty:
                pass
            # La pastille « respire » pendant l'écoute pour qu'on voie bien que le micro est ouvert.
            etat_courant["tic"] += 1
            if etat_courant["nom"] == "ecoute":
                r = 14 if (etat_courant["tic"] // 4) % 2 else 10
            else:
                r = 12
            toile.coords(pastille, 28 - r, 32 - r, 28 + r, 32 + r)
            racine.after(100, rafraichir)

        rafraichir()
        try:
            racine.mainloop()
        except KeyboardInterrupt:
            pass


def _raccourcir(texte: str, n: int) -> str:
    texte = " ".join(texte.split())
    return texte if len(texte) <= n else texte[: n - 1] + "…"
