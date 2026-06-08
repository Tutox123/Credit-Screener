# Credit RV Screener

Dashboard professionnel de screening de relative value sur l'univers crédit européen.
Construit en **Python / Streamlit / Plotly**. Identifie les meilleures opportunités ajustées du risque.

---

## Démarrage Rapide (Local)

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. (Optionnel) Régénérer le dataset
python generate_inputs.py

# 3. (Optionnel) Calculer les scores en batch
python scoring_engine.py

# 4. Lancer le dashboard
streamlit run dashboard.py
```

Le dashboard s'ouvre automatiquement sur `http://localhost:8501`.

---

## Déploiement sur Streamlit Cloud (URL publique, gratuit)

Streamlit Cloud permet d'héberger le dashboard avec un lien partageable, parfait pour l'envoyer à un recruteur. **Compte gratuit jusqu'à 3 apps publiques.**

### Étape 1 — Mettre le projet sur GitHub

```bash
# Dans le dossier credit_rv_screener
cd credit_rv_screener
git init
git add .
git commit -m "Initial commit"

# Créer un nouveau repo sur github.com (par exemple "credit-rv-screener")
# Puis le lier :
git branch -M main
git remote add origin https://github.com/<ton-username>/credit-rv-screener.git
git push -u origin main
```

> 💡 **Important** : le repo peut être public (gratuit) ou privé (Streamlit Cloud supporte les deux avec un compte gratuit).

### Étape 2 — Déployer sur Streamlit Cloud

1. Aller sur **https://share.streamlit.io** (ou https://streamlit.io/cloud)
2. Se connecter avec ton compte GitHub
3. Cliquer **"New app"**
4. Sélectionner :
   - **Repository** : `<ton-username>/credit-rv-screener`
   - **Branch** : `main`
   - **Main file path** : `dashboard.py`
5. Cliquer **Deploy**

Streamlit Cloud installe automatiquement les dépendances de `requirements.txt`. Le déploiement prend 2-3 minutes la première fois.

Tu obtiens une URL du type : `https://credit-rv-screener-<random>.streamlit.app`

### Étape 3 — Mises à jour

Tout push sur la branche `main` redéploie automatiquement l'app. Pour modifier la méthodologie :

```bash
# Modifier weights.yaml ou n'importe quel fichier
git add .
git commit -m "Update weights"
git push
# → l'app se met à jour toute seule en ~1 minute
```

### Astuces Pro

- **Personnaliser l'URL** : Settings → General → "Custom subdomain" (gratuit) → ex. `credit-rv-ilias.streamlit.app`
- **Mettre l'app en veille** : Streamlit Cloud met les apps non utilisées en veille (redémarrage en ~30s au premier visiteur) — pas grave pour un partage one-shot
- **Logs** : visible dans le panel Streamlit Cloud, utile en cas de bug

---

## Structure du Projet

```
credit_rv_screener/
├── generate_inputs.py     # Génère l'inputs.csv (univers réaliste de 79 obligations)
├── inputs.csv             # Données obligataires brutes
├── weights.yaml           # Toutes les pondérations centralisées
├── scoring_engine.py      # Applique la méthodologie -> scores.csv
├── dashboard.py           # Interface Streamlit
├── methodology.md         # Note méthodologique complète (avec auto-critique)
├── requirements.txt       # Dépendances Python
└── README.md
```

---

## Fonctionnement

1. **`inputs.csv`** contient les données obligataires brutes — le type de feed qu'un analyste credit research reçoit quotidiennement de Bloomberg / ICE / Markit (ISIN, spreads, ratings, fondamentaux, métriques de liquidité).
2. **`weights.yaml`** centralise la méthodologie — chaque pondération, chaque table de référence. À ajuster pour recalibrer sans toucher au code.
3. **`scoring_engine.py`** applique la méthodologie de manière déterministe — mêmes inputs + mêmes poids = mêmes outputs, toujours.
4. **`dashboard.py`** est l'UI Streamlit — bubble chart interactif, heatmap sectorielle, top picks, détail émetteur. **Les pondérations peuvent être modifiées en direct via la sidebar**, avec recalcul automatique.

---

## Encodage Visuel

| Canal    | Dimension              | Mapping                                                   |
|----------|------------------------|-----------------------------------------------------------|
| Axe X    | Score de Risque        | 0 = sûr → 100 = risqué                                    |
| Axe Y    | Score de Reward        | 0 = peu attractif → 100 = attractif                       |
| Taille   | Score de Liquidité     | petite = illiquide → grande = liquide                     |
| Forme    | Séniorité              | ■ SS · ● SU · ◆ T2 · ▲ AT1 · ⬟ Subordonné Assurance       |
| Couleur  | Émetteur               | Une couleur par émetteur (légende à droite)               |

Les meilleures opportunités RV se trouvent dans le **quadrant haut-gauche**.

---
