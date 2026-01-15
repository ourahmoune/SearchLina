# 🏠 CROUS Paris Monitor - Surveillance Automatique

Bot qui surveille automatiquement les nouvelles offres de logement CROUS à Paris et t'envoie un email dès qu'une nouvelle offre apparaît.

## 🚀 Déploiement sur GitHub (Guide complet)

### Étape 1 : Configuration de Gmail

Suis le guide dans `GMAIL_SETUP.md` pour :
1. Activer la validation en deux étapes
2. Générer un mot de passe d'application
3. Noter ton email et le mot de passe d'application

### Étape 2 : Créer le dépôt GitHub

1. Va sur https://github.com/new
2. Nomme ton dépôt : `crous-monitor` (ou un autre nom)
3. Choisis **Public** ou **Private**
4. **NE COCHE PAS** "Initialize this repository with a README"
5. Clique sur "Create repository"

### Étape 3 : Pousser le code vers GitHub

Ouvre un terminal et exécute ces commandes :

```bash
# Clone ou va dans le dossier de ton projet
cd chemin/vers/ton/projet

# Initialise git
git init

# Ajoute tous les fichiers
git add .

# Crée le premier commit
git commit -m "🎉 Initial commit - CROUS Monitor"

# Ajoute le dépôt distant (remplace USERNAME et REPO)
git remote add origin https://github.com/USERNAME/REPO.git

# Pousse le code
git branch -M main
git push -u origin main
```

### Étape 4 : Configurer les secrets GitHub

1. Va sur ton dépôt GitHub
2. Clique sur **Settings** (en haut)
3. Dans le menu de gauche, clique sur **Secrets and variables** → **Actions**
4. Clique sur **New repository secret**
5. Crée deux secrets :

   **Secret 1 :**
   - Name: `EMAIL`
   - Value: `tonemail@gmail.com`
   
   **Secret 2 :**
   - Name: `MOT_DE_PASSE_APP`
   - Value: `xxxx xxxx xxxx xxxx` (le mot de passe d'application Gmail)

6. Clique sur "Add secret" pour chaque secret

### Étape 5 : Donner les permissions au workflow

1. Toujours dans **Settings**
2. Va dans **Actions** → **General** (dans le menu de gauche)
3. Descends jusqu'à **Workflow permissions**
4. Sélectionne **Read and write permissions**
5. Clique sur **Save**

### Étape 6 : Activer le workflow

1. Va dans l'onglet **Actions** de ton dépôt
2. Tu verras le workflow "🏠 CROUS Paris Monitor"
3. Clique sur **Enable workflow** si demandé
4. Clique sur le workflow puis sur **Run workflow** → **Run workflow** pour le tester manuellement

## ⚙️ Configuration

Le bot vérifie automatiquement les offres **toutes les 30 minutes**.

Pour changer la fréquence, modifie cette ligne dans `.github/workflows/crous_monitor.yml` :

```yaml
- cron: '*/30 * * * *'  # Toutes les 30 minutes
```

Exemples de fréquences :
- `*/15 * * * *` - Toutes les 15 minutes
- `*/60 * * * *` - Toutes les heures
- `0 */2 * * *` - Toutes les 2 heures
- `0 8-20/2 * * *` - Toutes les 2h entre 8h et 20h

## 📊 Vérifier que ça marche

1. Va dans **Actions** sur GitHub
2. Tu verras l'historique des exécutions
3. Clique sur une exécution pour voir les logs
4. Tu verras des messages comme :
   - `🔍 Vérification 15/01/2025 10:30:00`
   - `📭 Aucun logement disponible à Paris (normal)`
   - `✅ Toujours pas d'offres (surveillance active)`

## 🎯 Quand une nouvelle offre apparaît

Tu recevras un email avec :
- 🏠 Titre du logement
- 📍 Adresse
- 💰 Prix
- 🔗 Lien direct pour postuler
- 📝 Détails supplémentaires

## 🔧 Dépannage

### Le workflow ne se lance pas
- Vérifie que tu as activé les workflows dans Actions
- Vérifie que tu as donné les permissions "Read and write"

### Pas d'email reçu
- Vérifie que les secrets `EMAIL` et `MOT_DE_PASSE_APP` sont bien configurés
- Vérifie dans les spams
- Lance le workflow manuellement pour voir les logs d'erreur

### Erreur "playwright"
- C'est normal au premier lancement, le workflow installe automatiquement

## 📝 Fichiers du projet

- `crous_monitor.py` - Script principal
- `.github/workflows/crous_monitor.yml` - Configuration GitHub Actions
- `seen.json` - Historique des offres (créé automatiquement)
- `requirements.txt` - Dépendances Python
- `GMAIL_SETUP.md` - Guide de configuration Gmail

## ⚠️ Important

- Les workflows gratuits sur GitHub ont une limite d'utilisation mensuelle
- Le fichier `seen.json` est mis à jour automatiquement par le bot
- Ne partage JAMAIS tes secrets (email, mot de passe d'application)

## 🎉 C'est tout !

Ton bot surveille maintenant automatiquement les offres CROUS Paris 24h/24 ! 🚀
