# pipeline_hydro_grass

## Description

Ce script Python automatise la génération du réseau hydrographique et du bassin versant principal à partir d'un point WGS84. Il s'appuie sur le Modèle Numérique de Terrain (MNT) ALOS AW3D30, et intègre GRASS GIS 8.4 (via OSGeo4W) ainsi que les outils GDAL/QGIS pour le traitement géospatial.

Les paramètres de configuration (coordonnées, chemins, etc.) sont facilement gérables via une interface graphique Tkinter.

## Fonctionnalités

* **Téléchargement de MNT :** Acquisition automatique des données ALOS AW3D30 via OpenTopography.
* **Prétraitement Géospatial :** Reprojection et nettoyage du MNT.
* **Analyse Hydrologique Avancée :**
    * Remplissage des puits du MNT.
    * Calcul de l'accumulation de flux et extraction du réseau hydrographique.
    * Détermination de l'exutoire le plus proche et délimitation du bassin versant principal.
    * Préparation du point exutoire pour SWAT+.
* **Export Complet :** Export des couches vectorielles (rivières, exutoire, bassin versant) dans un GeoPackage (.gpkg) et du MNT masqué en GeoTIFF (.tif).
* **Interface Utilisateur Intuitive :** Configuration simplifiée via une GUI Tkinter.

## Pré-requis

* **Python 3** (avec `pip` pour les dépendances)
* **GRASS GIS 8.4** (installation OSGeo4W recommandée sur Windows)
* **QGIS** (pour les outils GDAL/PROJ)
* Une **clé API OpenTopography** (disponible sur [opentopography.org](https://opentopography.org/developers))

## Installation

1.  Clonez le dépôt :
    ```bash
    git clone [https://github.com/votre_utilisateur/pipeline_hydro_grass.git](https://github.com/votre_utilisateur/pipeline_hydro_grass.git)
    cd pipeline_hydro_grass
    ```
2.  Installez les dépendances Python :
    ```bash
    pip install numpy rasterio requests pyproj
    ```
3.  **Configuration des Chemins :** Assurez-vous que les chemins vers GRASS GIS et QGIS (et les outils GDAL/PROJ) sont correctement définis dans l'interface graphique du script lors de la première exécution, ou ajustez les valeurs par défaut dans le code source si nécessaire.

## Utilisation

1.  Lancez le script :
    ```bash
    python Hydro_GRASS.py
    ```
2.  Dans l'interface graphique, configurez les paramètres requis (coordonnées, chemins, clé API, etc.).
3.  Cliquez sur "Lancer le Pipeline Hydrologique" pour démarrer le processus. Les logs d'exécution s'afficheront en temps réel.

## Résultats

Les résultats seront enregistrés dans le répertoire de sortie que vous avez spécifié :

* `hydro_results.gpkg` : Contient les couches `rivieres`, `exutoire` et `main_basin`.
* `MNT_decoupe_bassin_versant.tif` : Le MNT masqué au bassin versant principal.

## Auteur

* Zo RASOANAIVO

## Dernière Modification

* 12 Juillet 2025

## Licence

Ce projet est sous licence MIT.
