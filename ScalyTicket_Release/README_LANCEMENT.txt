================================================================================
          SCALY-TICKET - LA FERME DES PEUPLIERS
================================================================================

1. DÉMARRAGE RAPIDE
-------------------
- Double-cliquez sur "ScalyTicket.exe".
- Le serveur local démarre et ouvre automatiquement votre navigateur sur :
  http://127.0.0.1:3000

2. CONTENU DU DOSSIER
---------------------
- ScalyTicket.exe : L'application autonome (moteur d'impression, API, interface Web).
- data/scaly_ticket.db : Base de données SQLite persistante contenant toutes vos imprimantes (IP, calibration, offsets) et vos recettes/parfums enregistrés.
- secret.json : Configuration de la connexion à l'ERP Microsoft Business Central.
- .env : Paramètres du serveur (port d'écoute).
- commandeTest/ : Échantillons de fichiers de commandes (.txt) pour tests hors-ligne.

3. CONFIGURATION BUSINESS CENTRAL (secret.json)
-----------------------------------------------
Pour basculer entre l'environnement de Test (Dev) et l'environnement réel (Production),
ouvrez le fichier "secret.json" dans le Bloc-notes et modifiez la ligne :

  "BC_ENVIRONMENT": "Production"   <-- (ou "Dev" pour la sandbox de test)

================================================================================
