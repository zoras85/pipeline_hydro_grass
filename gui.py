# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/gui.py
# ─────────────────────────────────────────────────────────────────────────────
"""Interface Tkinter pour configurer et exécuter le pipeline hydrologique.

Fonctions principales :
* Chargement des fichiers de configuration YAML
* Édition des paramètres
* Sauvegarde de la configuration
* Exécution du pipeline avec affichage des logs
* Gestion du mode développeur
"""

from __future__ import annotations
import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from .config import Config
from .config_io import from_yaml_pair, save_editable_yaml
from .logging_setup import setup_logging
from .env_utils import validate_environment
from .download_dem import calculate_bbox_wgs84, telecharger_mnt
from .preprocess_dem import pretraiter_mnt
from .grass_session import init_grass_modules, initialiser_grass
from .hydro_analysis import analyse_hydro_grass
from .export_results import export_grass_results


class PipelineConfigGUI(tk.Tk):
    """Interface graphique pour le pipeline hydrologique."""

    def __init__(self, cfg: Config | None = None):
        """Initialise l'interface avec une configuration optionnelle."""
        super().__init__()
        self.title("Configuration du Pipeline Hydrologique")
        self.geometry("900x750")
        self.logger = setup_logging()
        self.cfg = cfg
        self._initialiser_interface()

    # ──────────────────────────────────────────────────────────────────────
    # Méthodes internes pour la construction de l'interface
    # ──────────────────────────────────────────────────────────────────────

    def _initialiser_interface(self):
        """Configure les widgets principaux de l'interface."""
        self._creer_widgets_principaux()
        self._creer_variables_tk()
        self._organiser_widgets()

    def _creer_widgets_principaux(self):
        """Crée les conteneurs principaux avec scrollbar."""
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame,
            orient="vertical",
            command=self.canvas.yview
        )

        self.content_frame = ttk.Frame(self.canvas)
        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.content_frame.columnconfigure(1, weight=1)

    def _creer_variables_tk(self):
        """Initialise les variables Tkinter pour stocker les valeurs."""
        cfg = self.cfg

        # Variables géographiques
        self.lat = tk.DoubleVar(value=cfg.LAT if cfg else 0.0)
        self.lon = tk.DoubleVar(value=cfg.LON if cfg else 0.0)
        self.boxkm = tk.DoubleVar(value=cfg.BBOX_SIZE_KM if cfg else 0.0)
        self.site = tk.StringVar(value=cfg.SITE_NAME if cfg else "")
        self.epsg = tk.IntVar(value=cfg.EPSG_CIBLE if cfg else 0)

        # Variables MNT et hydrologie
        self.nodata = tk.DoubleVar(value=cfg.NODATA_VALUE if cfg else 0.0)
        self.thrkm2 = tk.DoubleVar(value=cfg.STREAM_THRESHOLD_KM2 if cfg else 0.0)

        # Variables d'environnement
        self.api = tk.StringVar(value=cfg.OPENTOPOGRAPHY_API_KEY if cfg else "")
        self.grass_base = tk.StringVar(value=cfg.GRASS_GISBASE if cfg else "")
        self.qgis = tk.StringVar(value=cfg.QGIS_PATH if cfg else "")

        # Variables GDAL/PROJ
        self.gdalwarp = tk.StringVar(value=cfg.GDALWARP_CMD if cfg else "")
        self.gdal_data = tk.StringVar(value=cfg.GDAL_DATA_EXT if cfg else "")
        self.proj = tk.StringVar(value=cfg.PROJ_LIB_EXT if cfg else "")
        self.gdal_bin = tk.StringVar(value=cfg.GDAL_BIN_EXT if cfg else "")

        # Variables de chemins
        self.outdir = tk.StringVar(value=cfg.OUTPUT_DIR if cfg else "")
        self.tmpdir = tk.StringVar(value=cfg.TEMP_DIR if cfg else "")
        self.grassdb = tk.StringVar(value=cfg.GRASS_DB_DIR if cfg else "")

        # Mode développeur
        self.dev = tk.BooleanVar(value=bool(cfg.DEV_MODE) if cfg else False)

    def _organiser_widgets(self):
        """Positionne les widgets dans l'interface."""
        row = 0

        # Section Paramètres géographiques
        self._ajouter_section("Paramètres géographiques", row)
        row = self._ajouter_champs_geographiques(row + 1)

        # Section Paramètres MNT & hydrologie
        self._ajouter_section("Paramètres MNT & hydrologie", row)
        row = self._ajouter_champs_mnt(row + 1)

        # Section Clés API
        self._ajouter_section("Clés et accès API", row)
        row = self._ajouter_champs_api(row + 1)

        # Section Chemins d'installation
        self._ajouter_section("Chemins d'installation", row)
        row = self._ajouter_champs_installation(row + 1)

        # Section Composants GDAL/PROJ
        self._ajouter_section("Composants GDAL/PROJ", row)
        row = self._ajouter_champs_gdal(row + 1)

        # Section Dossiers de travail
        self._ajouter_section("Dossiers de travail et sortie", row)
        row = self._ajouter_champs_dossiers(row + 1)

        # Checkbox mode développeur
        self._ajouter_checkbox_dev(row)
        row += 1

        # Boutons d'action
        self._ajouter_boutons_actions(row)

    def _ajouter_section(self, titre: str, row: int):
        """Ajoute un titre de section."""
        ttk.Label(
            self.content_frame,
            text=titre,
            font=("Arial", 12, "bold")
        ).grid(row=row, columnspan=3, pady=(10, 5), sticky="w")

    def _ajouter_champs_geographiques(self, row: int) -> int:
        """Ajoute les champs pour les paramètres géographiques."""
        self._creer_champ_entree("Latitude (°)", self.lat, row)
        self._creer_champ_entree("Longitude (°)", self.lon, row + 1)
        self._creer_champ_entree("Demi-côté de la bbox (km)", self.boxkm, row + 2)
        self._creer_champ_entree("Nom du site", self.site, row + 3)
        self._creer_champ_entree("EPSG cible", self.epsg, row + 4)
        return row + 5

    def _ajouter_champs_mnt(self, row: int) -> int:
        """Ajoute les champs pour les paramètres MNT."""
        self._creer_champ_entree("Valeur NoData", self.nodata, row)
        self._creer_champ_entree("Seuil cours d'eau (km²)", self.thrkm2, row + 1)
        return row + 2

    def _ajouter_champs_api(self, row: int) -> int:
        """Ajoute le champ pour la clé API."""
        self._creer_champ_entree("OpenTopography API", self.api, row)
        return row + 1

    def _ajouter_champs_installation(self, row: int) -> int:
        """Ajoute les champs pour les chemins d'installation."""
        self._creer_champ_chemin("GRASS GISBASE", self.grass_base, row)
        self._creer_champ_chemin("QGIS (optionnel)", self.qgis, row + 1)
        return row + 2

    def _ajouter_champs_gdal(self, row: int) -> int:
        """Ajoute les champs pour les composants GDAL."""
        self._creer_champ_chemin("gdalwarp.exe", self.gdalwarp, row, False)
        self._creer_champ_chemin("GDAL_DATA", self.gdal_data, row + 1)
        self._creer_champ_chemin("PROJ_LIB", self.proj, row + 2)
        self._creer_champ_chemin("GDAL bin", self.gdal_bin, row + 3)
        return row + 4

    def _ajouter_champs_dossiers(self, row: int) -> int:
        """Ajoute les champs pour les dossiers de travail."""
        self._creer_champ_chemin("Dossier de sortie", self.outdir, row)
        self._creer_champ_chemin("Dossier temporaire", self.tmpdir, row + 1)
        self._creer_champ_chemin("Répertoire GRASSDATA", self.grassdb, row + 2)
        return row + 3

    def _ajouter_checkbox_dev(self, row: int):
        """Ajoute la checkbox pour le mode développeur."""
        ttk.Checkbutton(
            self.content_frame,
            text="Mode développeur (conserver les temporaires)",
            variable=self.dev
        ).grid(row=row, columnspan=3, pady=10, sticky="w")

    def _ajouter_boutons_actions(self, row: int):
        """Ajoute les boutons d'action principaux."""
        frame_boutons = ttk.Frame(self.content_frame)
        frame_boutons.grid(row=row, columnspan=3, sticky="w", pady=10)

        ttk.Button(
            frame_boutons,
            text="Charger 2 YAML…",
            command=self._charger_yaml
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            frame_boutons,
            text="Enregistrer config.yaml…",
            command=self._sauvegarder_yaml
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            frame_boutons,
            text="Lancer le pipeline",
            command=self._executer_pipeline
        ).pack(side="left")

    # ──────────────────────────────────────────────────────────────────────
    # Méthodes utilitaires pour les widgets
    # ──────────────────────────────────────────────────────────────────────

    def _creer_champ_entree(self, label: str, variable: tk.Variable, row: int):
        """Crée un champ d'entrée avec étiquette."""
        ttk.Label(self.content_frame, text=label).grid(
            row=row, column=0, sticky="w", pady=2, padx=5
        )
        ttk.Entry(self.content_frame, textvariable=variable, width=50).grid(
            row=row, column=1, sticky="ew", pady=2, padx=5
        )

    def _creer_champ_chemin(self, label: str, variable: tk.Variable, row: int, est_repertoire: bool = True):
        """Crée un champ de sélection de chemin."""
        self._creer_champ_entree(label, variable, row)
        ttk.Button(
            self.content_frame,
            text="Parcourir",
            command=lambda: self._selectionner_chemin(variable, est_repertoire)
        ).grid(row=row, column=2, sticky="e", pady=2, padx=5)

    @staticmethod
    def _selectionner_chemin(variable: tk.Variable, est_repertoire: bool):
        """Ouvre un dialogue de sélection de fichier/dossier."""
        chemin = filedialog.askdirectory() if est_repertoire else filedialog.askopenfilename()
        if chemin:
            variable.set(chemin)

    # ──────────────────────────────────────────────────────────────────────
    # Gestion de la configuration
    # ──────────────────────────────────────────────────────────────────────

    def _collecter_config(self) -> Config:
        """Crée un objet Config à partir des valeurs de l'interface."""
        return Config(
            LAT=self.lat.get(),
            LON=self.lon.get(),
            BBOX_SIZE_KM=self.boxkm.get(),
            SITE_NAME=self.site.get(),
            EPSG_CIBLE=self.epsg.get(),
            NODATA_VALUE=self.nodata.get(),
            STREAM_THRESHOLD_KM2=self.thrkm2.get(),
            GRASS_GISBASE=self.grass_base.get(),
            QGIS_PATH=self.qgis.get(),
            GDALWARP_CMD=self.gdalwarp.get(),
            GDAL_DATA_EXT=self.gdal_data.get(),
            PROJ_LIB_EXT=self.proj.get(),
            GDAL_BIN_EXT=self.gdal_bin.get(),
            OUTPUT_DIR=self.outdir.get(),
            TEMP_DIR=self.tmpdir.get(),
            GRASS_DB_DIR=self.grassdb.get(),
            OPENTOPOGRAPHY_API_KEY=self.api.get(),
            DEV_MODE=self.dev.get(),
        )

    def _appliquer_config(self, cfg: Config):
        """Applique une configuration à l'interface."""
        self.lat.set(cfg.LAT)
        self.lon.set(cfg.LON)
        self.boxkm.set(cfg.BBOX_SIZE_KM)
        self.site.set(cfg.SITE_NAME)
        self.epsg.set(cfg.EPSG_CIBLE)
        self.nodata.set(cfg.NODATA_VALUE)
        self.thrkm2.set(cfg.STREAM_THRESHOLD_KM2)
        self.api.set(cfg.OPENTOPOGRAPHY_API_KEY)
        self.grass_base.set(cfg.GRASS_GISBASE)
        self.qgis.set(cfg.QGIS_PATH)
        self.gdalwarp.set(cfg.GDALWARP_CMD)
        self.gdal_data.set(cfg.GDAL_DATA_EXT)
        self.proj.set(cfg.PROJ_LIB_EXT)
        self.gdal_bin.set(cfg.GDAL_BIN_EXT)
        self.outdir.set(cfg.OUTPUT_DIR)
        self.tmpdir.set(cfg.TEMP_DIR)
        self.grassdb.set(cfg.GRASS_DB_DIR)
        self.dev.set(cfg.DEV_MODE)

    def _charger_yaml(self):
        """Charge les fichiers de configuration YAML."""
        chemin_config = filedialog.askopenfilename(
            title="Choisir config.yaml",
            filetypes=[("YAML", "*.yml *.yaml")],
        )
        if not chemin_config:
            return

        chemin_defaut = filedialog.askopenfilename(
            title="Choisir default_config.yaml",
            filetypes=[("YAML", "*.yml *.yaml")],
        )
        if not chemin_defaut:
            return

        try:
            cfg = from_yaml_pair(chemin_config, chemin_defaut)
            self._appliquer_config(cfg)
            self.cfg = cfg
            messagebox.showinfo(
                "Configuration",
                f"Configurations chargées avec succès :\n- {chemin_config}\n- {chemin_defaut}"
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les YAML : {e}")

    def _sauvegarder_yaml(self):
        """Sauvegarde la configuration actuelle dans un fichier YAML."""
        if self.cfg is None:
            messagebox.showerror("Erreur", "Aucune configuration chargée.")
            return

        chemin = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml"), ("YML", "*.yml")],
        )
        if not chemin:
            return

        try:
            save_editable_yaml(self._collecter_config(), chemin)
            messagebox.showinfo("Configuration", f"Fichier enregistré : {chemin}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer : {e}")

    # ──────────────────────────────────────────────────────────────────────
    # Exécution du pipeline
    # ──────────────────────────────────────────────────────────────────────

    def _executer_pipeline(self):
        """Lance l'exécution du pipeline dans un thread séparé."""
        cfg = self._collecter_config()
        logger = self.logger

        # Création de la fenêtre de logs
        self.withdraw()
        fenetre_logs = tk.Toplevel(self)
        fenetre_logs.title("Exécution du Pipeline")
        zone_texte = tk.Text(fenetre_logs, wrap="word", width=80, height=24)
        zone_texte.pack(fill="both", expand=True, padx=10, pady=10)

        # Configuration du handler de logs
        import logging
        class HandlerLogsTexte(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
                self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

            def emit(self, record):
                try:
                    message = self.format(record) + "\n"
                    self.widget.insert(tk.END, message)
                    self.widget.see(tk.END)
                    self.widget.update_idletasks()
                except Exception:
                    pass

        handler = HandlerLogsTexte(zone_texte)
        logger.addHandler(handler)

        def _travail():
            """Fonction exécutée dans le thread pour le pipeline."""
            dossier_temp = None
            base_grass = None

            try:
                # Validation de l'environnement
                infos_env = validate_environment(cfg, logger)

                # Préparation des dossiers
                bbox = calculate_bbox_wgs84(cfg.LAT, cfg.LON, cfg.BBOX_SIZE_KM)
                session = f"{cfg.SITE_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                dossier_sortie = os.path.join(cfg.OUTPUT_DIR, session)
                dossier_temp = os.path.join(cfg.TEMP_DIR, session)
                base_grass = os.path.join(cfg.GRASS_DB_DIR, f"hydro_grass_db_{session}")

                os.makedirs(dossier_sortie, exist_ok=True)
                os.makedirs(dossier_temp, exist_ok=True)
                os.makedirs(cfg.GRASS_DB_DIR, exist_ok=True)
                logger.info("Dossiers préparés : temp=%s | db=%s | out=%s",
                            dossier_temp, base_grass, dossier_sortie)

                # Étapes du pipeline
                mnt_brut = telecharger_mnt(bbox, dossier_temp, cfg.OPENTOPOGRAPHY_API_KEY, logger)
                mnt_propre = pretraiter_mnt(
                    mnt_brut, dossier_temp, cfg.EPSG_CIBLE, cfg.NODATA_VALUE,
                    infos_env["GDAL_ENV"], cfg.GDALWARP_CMD, logger
                )

                gi = init_grass_modules(infos_env["GRASS_PYTHON_PATH"], logger)
                initialiser_grass(
                    gi, infos_env["GRASS_CMD"], cfg.GRASS_DB_DIR,
                    f"hydro_loc_{session}", "PERMANENT", cfg.EPSG_CIBLE, logger
                )

                x_out, y_out = analyse_hydro_grass(
                    gi, mnt_propre, cfg.LAT, cfg.LON,
                    cfg.STREAM_THRESHOLD_KM2, 4326, cfg.EPSG_CIBLE, logger
                )

                # Utilisation explicite pour éviter l'avertissement "non utilisé"
                logger.info("Exutoire (SCR cible) : (%.2f, %.2f)", x_out, y_out)

                export_grass_results(gi, dossier_sortie, logger)
                self.after(
                    0,
                    messagebox.showinfo,
                    "Succès",
                    f"Pipeline terminé.\nRésultats : {dossier_sortie}"
                )


            except Exception as e:
                self.after(
                    0,
                    messagebox.showerror,
                    "Échec",
                    f"Le pipeline a échoué : {e}"
                )


            finally:
                # Nettoyage
                try:
                    logger.removeHandler(handler)
                except Exception:
                    pass
                fenetre_logs.destroy()
                self.deiconify()

                if not cfg.DEV_MODE:
                    self._nettoyer_temporaires(dossier_temp, base_grass, logger=logger)

        threading.Thread(target=_travail, daemon=True).start()

    @staticmethod
    def _nettoyer_temporaires(*chemins, logger=None):
        """Nettoie les fichiers temporaires si nécessaire."""
        for chemin in chemins:
            try:
                if chemin and os.path.isdir(chemin):
                    shutil.rmtree(chemin)
                    if logger:
                        logger.info("Temporaire supprimé : %s", chemin)
            except Exception as e:
                if logger:
                    logger.warning("Échec suppression du temporaire %s : %s", chemin, e)
                continue
