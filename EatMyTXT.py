import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    raise SystemExit(
        "Le module 'tkinterdnd2' est requis.\n"
        "Installe-le avec : pip install tkinterdnd2"
    )

# --- CONFIGURATION ---

# 1. Extensions de fichiers à INCLURE (Code source utile)
INCLUDED_EXTENSIONS = [
    ".dart", ".js", ".ts", ".jsx", ".tsx", ".template",
    ".json", ".yaml", ".yml",".asm",".bat"
    ".html", ".htm", ".css",
    ".md", ".txt",
    ".py", ".java", ".kt", ".c", ".cpp", ".h", ".hpp",
    ".sh", ".bat", ".dockerfile", "Dockerfile", # Ajout explicite docker
]

# 2. Dossiers cachés à INCLURE (Exceptions)
INCLUDED_HIDDEN_DIRS = {
    ".github",  # Pour les workflows
}

# 3. Dossiers à EXCLURE (Ne pas scanner)
EXCLUDED_DIRS = {
    "build",
    ".dart_tool",
    ".git",
    ".idea",
    ".vscode",
    "android",
    "ios",
    "node_modules",
    ".gradle",
    ".gitlab",
    ".vs",
    ".venv",
    "venv",
    "__pycache__",
}

# 4. Fichiers spécifiques à EXCLURE (Secrets & Fichiers lourds)
EXCLUDED_FILENAMES = {
    # --- Fichiers d'environnement standards ---
    ".env",
    ".env.local",
    ".env.development",
    ".env.test",
    ".env.production",
    
    # --- Fichiers d'environnement Docker & Overrides ---
    ".env.docker",
    "docker.env",
    "docker-compose.override.yml", # Contient souvent des configs locales secrètes
    "compose.env",
    "env_file", # Nom générique souvent utilisé dans docker-compose

    # --- Fichiers de dépendances lourds (bruit pour l'IA) ---
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "Cargo.lock",
    
    # --- Fichiers système ---
    ".DS_Store",
    "Thumbs.db",
}

SEPARATOR = "-" * 80


def normalize_path_slashes(path: str) -> str:
    """Convertit toutes les barres en slashes unix."""
    return path.replace("\\", "/")


def is_code_file(filename: str) -> bool:
    """Retourne True si le fichier a une extension valide ou est un Dockerfile."""
    # Gestion spécifique pour les fichiers sans extension type 'Dockerfile'
    if filename.lower() == "dockerfile":
        return True
        
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in INCLUDED_EXTENSIONS)


def clean_text(content: str) -> str:
    """Nettoie les fins de ligne et caractères invisibles."""
    cleaned = (
        content.replace("\r\n", "\n")
               .replace("\r", "\n")
               .replace("\u2028", "\n")
               .replace("\u2029", "\n")
    )
    return cleaned


def flatten_folder_to_single_txt(folder: str) -> str:
    """Concatène le code dans un fichier .txt nommé comme le dossier parent."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    folder_name = os.path.basename(os.path.normpath(folder))
    output_filename = f"{folder_name}.txt"
    output_path = os.path.join(script_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as out:

        for root, dirs, files in os.walk(folder):
            
            # 1. Filtrage des DOSSIERS
            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDED_DIRS
                and (not d.startswith(".") or d in INCLUDED_HIDDEN_DIRS)
            ]

            for filename in files:
                
                # 2. Filtrage des FICHIERS INTERDITS (Blacklist)
                if filename in EXCLUDED_FILENAMES:
                    continue

                # 3. Filtrage par EXTENSION (Whitelist)
                if not is_code_file(filename):
                    continue

                full_path = os.path.join(root, filename)
                full_path_clean = normalize_path_slashes(full_path)

                # Écriture
                out.write(SEPARATOR + "\n")
                out.write(f"FILE: {full_path_clean}\n")
                out.write(SEPARATOR + "\n\n")

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(full_path, "r", encoding="latin-1", errors="ignore") as f:
                        content = f.read()

                cleaned = clean_text(content)
                out.write(cleaned)
                out.write("\n\n")

    return output_path


class FlattenApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Code Flattener")
        self.geometry("480x260")
        self.resizable(False, False)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text="Glisse-dépose un dossier de code\nou clique sur le bouton ci-dessous",
            justify="center",
            font=("Segoe UI", 11, "bold"),
        )
        title_label.pack(pady=(0, 10))

        self.drop_label = tk.Label(
            main_frame,
            text="Dépose le dossier ici",
            relief="ridge",
            borderwidth=2,
            width=40,
            height=4,
            bg="#f0f0f0",
            fg="#333333",
        )
        self.drop_label.pack(pady=5)

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.on_drop)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        browse_btn = ttk.Button(
            btn_frame,
            text="Choisir un dossier...",
            command=self.choose_folder,
        )
        browse_btn.pack(side="left", padx=5)

        quit_btn = ttk.Button(
            btn_frame,
            text="Quitter",
            command=self.destroy,
        )
        quit_btn.pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="En attente d’un dossier...")
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            foreground="#555555",
            wraplength=430,
            justify="center",
        )
        status_label.pack(pady=(10, 0))

    def normalize_path(self, raw: str) -> str:
        path = raw.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        return path

    def on_drop(self, event):
        raw_path = event.data
        folder = self.normalize_path(raw_path)

        if not os.path.isdir(folder):
            messagebox.showerror("Erreur", "Ce n’est pas un dossier valide.")
            return

        self.process_folder(folder)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choisir un dossier de projet")
        if folder:
            self.process_folder(folder)

    def process_folder(self, folder: str):
        self.status_var.set(f"Traitement en cours...\n{folder}")
        self.update_idletasks()

        try:
            output = flatten_folder_to_single_txt(folder)
        except Exception as e:
            messagebox.showerror("Erreur", f"{type(e).__name__}: {e}")
            self.status_var.set("Erreur.")
            return

        filename = os.path.basename(output)
        self.status_var.set(f"Terminé.\nFichier généré : {filename}")
        messagebox.showinfo("Terminé", f"Fichier généré :\n\n{output}")


if __name__ == "__main__":
    app = FlattenApp()
    app.mainloop()