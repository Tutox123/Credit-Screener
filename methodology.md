# Credit RV Screener — Note Méthodologique

**Version** : 1.0
**Date** : 8 juin 2026
**Univers** : 79 émissions obligataires · 36 émetteurs · 4 secteurs (Banks, Insurance, Corporate IG, High Yield)

---

## 1. Synthèse

Le Credit RV Screener est un cadre quantitatif conçu pour identifier des **opportunités de relative value** sur l'univers crédit européen. Il combine une **analyse bottom-up au niveau de l'émetteur** avec un **overlay top-down sectoriel et macro**, condensant chaque émission en trois scores principaux :

- **Score de Risque** (0–100, plus élevé = plus risqué)
- **Score de Reward** (0–100, plus élevé = plus attractif)
- **Score de Liquidité** (0–100, plus élevé = plus liquide)

L'output final est un **Score RV = Reward / Risque** qui classe l'univers et fait ressortir les émissions offrant le meilleur rendement ajusté du risque.

Le framework est conçu pour la **reproductibilité** : chaque pondération est centralisée dans `weights.yaml`, chaque score découle d'inputs auditables, et l'ensemble du pipeline peut être relancé de bout en bout après toute modification.

---

## 2. Encodage Visuel (Dashboard)

Le screener principal encode l'information selon cinq dimensions visuelles sur un seul bubble chart :

| Visuel  | Dimension              | Lecture                                                    |
|---------|------------------------|------------------------------------------------------------|
| Axe X   | **Score de Risque**    | Aller à gauche = plus sûr                                  |
| Axe Y   | **Score de Reward**    | Aller en haut = plus attractif                             |
| Taille  | **Score de Liquidité** | Plus grand = plus liquide                                  |
| Forme   | **Séniorité**          | ■ SS · ● SU · ◆ T2 · ▲ AT1 · ⬟ Subordonné Assurance        |
| Couleur | **Émetteur**           | Une couleur par émetteur (partagée par toutes ses émissions) |

Les **meilleures opportunités** se situent dans le **quadrant haut-gauche** : reward élevé pour un risque faible, idéalement avec une grande bulle (liquide).

---

## 3. Score de Risque — Décomposition

### Bloc A — Risque Idiosyncratique (65%)
Capture le risque propre à l'émetteur.

| Composante       | Poids  | Input                                                                 |
|------------------|--------|-----------------------------------------------------------------------|
| Rating Obligation| 28%    | Rating S&P au niveau obligataire, table de conversion (AAA=2, BBB=42, CCC=96) |
| Subordination    | 20%    | Position dans la capital structure (SS=0, SU=18, T2=55, Sub Ins=60, AT1=90) |
| Levier           | 12%    | Sector-aware : ND/EBITDA (corp), CET1 (banks), Solvency II (assurance) |
| Duration         | 5%     | Duration modifiée, normalisée min-max                                 |

### Bloc B — Risque Sectoriel (18%)
Caractéristiques structurelles du secteur.

| Composante            | Poids  | Méthodologie                                                  |
|-----------------------|--------|---------------------------------------------------------------|
| Cyclicité             | 7%     | Défensif vs cyclique (base sectorielle + ajustement sous-secteur) |
| Historique de Défaut  | 6%     | Taux de défaut historique par secteur (Moody's)               |
| Volatilité des Spreads| 5%     | Vol historique 5Y des spreads sectoriels                      |

### Bloc C — Risque Macro / Exogène (17%)
Facteurs externes à l'émetteur.

| Composante            | Poids  | Input                                                         |
|-----------------------|--------|---------------------------------------------------------------|
| Géopolitique          | 6%     | Score-pays (sanctions, conflits, risque politique)            |
| Sensibilité aux Taux  | 5%     | Sensibilité driven-by-duration à un choc +100bp               |
| Exposition FX         | 3%     | Mismatch de devise (dette non-EUR → score plus élevé)         |
| Pression Réglementaire| 3%     | Intensité réglementaire par secteur                           |

---

## 4. Score de Reward — Décomposition

### Bloc A — Attractivité du Spread (62%)

| Composante                  | Poids  | Méthodologie                                       |
|-----------------------------|--------|----------------------------------------------------|
| Z-Spread vs Univers         | 30%    | Rang percentile sur l'univers complet              |
| Pickup vs Médiane Sectorielle| 20%   | Pickup vs médiane secteur, normalisée min-max      |
| Pickup vs Médiane Rating    | 12%    | Pickup vs pairs de même rating (cheap intra-rating ?) |

### Bloc B — Carry & Roll (18%)

| Composante         | Poids  | Méthodologie                                                                |
|--------------------|--------|-----------------------------------------------------------------------------|
| Yield Courant      | 11%    | Coupon / Prix Mid                                                           |
| Roll-Down 1Y       | 7%     | Approximé via pente de courbe issuer × duration                             |

### Bloc C — Croissance Sectorielle & Momentum (20%)

| Composante                | Poids  | Input                                                            |
|---------------------------|--------|------------------------------------------------------------------|
| Perspective de Croissance | 10%    | Qualitative (Forte=85, Modérée=55, Stable=40, Mitigée=25, Faible=10) |
| Momentum Révisions ROE    | 7%     | Percentile ROE intra-secteur (proxy de direction des révisions)  |
| Momentum Spread 3M        | 3%     | Trajectoire 3M du spread sectoriel                               |

---

## 5. Score de Liquidité

| Composante              | Poids  | Input                                              |
|-------------------------|--------|----------------------------------------------------|
| Encours                 | 30%    | Notionnel, normalisé min-max                       |
| Bid-Ask                 | 30%    | Bid-ask inversé (en cents)                         |
| Jours Tradés / Mois     | 20%    | Nombre de jours d'activité (sur ~22)               |
| Volume Quotidien Moyen  | 20%    | Notionnel moyen tradé par jour                     |

---

## 6. Agrégation Finale

```
SCORE DE RISQUE  = 0.65 × Idiosyncratique + 0.18 × Sectoriel + 0.17 × Macro
SCORE DE REWARD  = 0.62 × Attractivité Spread + 0.18 × Carry/Roll + 0.20 × Croissance Sectorielle
SCORE RV         = Score de Reward / Score de Risque
```

Le Score RV fonctionne comme un **proxy de rendement ajusté du risque**. Les obligations avec RV > 1.0 délivrent plus de reward par unité de risque ; celles avec RV < 1.0 sont écartées comme surévaluées par rapport à leurs fondamentaux.

---

## 7. Sources de Données

| Champ                                | Source                                                  |
|--------------------------------------|---------------------------------------------------------|
| Ratings (S&P/Moody's/Fitch)          | Agences de rating, Bloomberg `RTGS<GO>`                 |
| Spreads (Z, OAS, ASW, G)             | Bloomberg `YAS<GO>`, ICE BAML, Markit iBoxx             |
| Fondamentaux Banks (CET1)            | Publications trimestrielles, ECB SREP, EBA Risk Dashboard |
| Fondamentaux Assurance (Solvency II) | Rapports SFCR, statistiques EIOPA trimestrielles        |
| Fondamentaux Corporate (ND/EBITDA)   | Comptes émetteur, S&P Capital IQ, Bloomberg `FA<GO>`    |
| Taux de défaut par secteur           | Moody's Annual Default Study                            |
| Volatilité des spreads               | Bloomberg historique (rolling 5Y)                       |
| Risque géopolitique                  | IMF WEO, World Bank, BlackRock GRI                      |
| Métriques de liquidité               | TRACE (US), MiFID II APAs (EU), Bloomberg BVAL          |

---

## 8. Reproductibilité & Automatisation

Le framework est construit en pipeline 3 couches :

```
inputs.csv  ──┐
              ├──> scoring_engine.py ──> scores.csv ──> dashboard.py
weights.yaml ─┘
```

- **`inputs.csv`** — données brutes au niveau obligataire, rafraîchissables hebdo/mensuel depuis n'importe quel feed market data
- **`weights.yaml`** — toutes les pondérations centralisées ; modifier ce fichier puis relancer pour recalibrer
- **`scoring_engine.py`** — couche de calcul déterministe
- **`dashboard.py`** — couche de visualisation Streamlit

Un rerun complet avec données rafraîchies prend **moins de 5 secondes**. Les mêmes inputs produisent toujours les mêmes outputs (zéro stochasticité, hors momentum spread placeholder qui utilise une seed fixe).

> **Nouveauté v1.0** : les pondérations sont aussi modifiables **en direct via la sidebar du dashboard**, avec recalcul automatique. Idéal pour tester des sensibilités sans relancer le pipeline.

---

## 9. Évaluation Critique de la Méthodologie

Cette section est volontairement honnête — tout modèle a ses limites et une équipe de credit research doit en avoir conscience.

### 9.1 Limites de Construction du Scoring

- **Pondérations arbitraires.** Les poids reflètent un jugement d'analyste, pas une optimisation statistique. Une approche plus rigoureuse calibrerait les poids via régression historique — quels facteurs ont prédit les défauts, widenings, ou upgrades passés ? — sur un dataset propriétaire non disponible ici.
- **Hypothèse de linéarité.** Le scoring agrège les facteurs linéairement, alors que le risque crédit est non-linéaire. Les effets de seuil aux frontières de rating (BBB → BB, le passage IG/HY) ou aux cliffs de ratios de capital (une banque passant de 12% CET1 à 10.5% déclenche les restrictions MDA, pas "1.5% de risque") sont lissés par le blend linéaire.
- **Normalisation percentile = relative.** Le scoring compare les émissions entre elles à l'instant t. Si tout l'univers se dégrade simultanément, le scoring ne le détecte pas — il identifie seulement la cherté relative. Un benchmark externe (iTraxx Main, Xover) corrigerait ce biais.

### 9.2 Limites des Données

- **Spreads = snapshot.** Un Z-spread à un instant t ne dit rien de la réalisabilité de ce spread. Une obligation cheap peut simplement être illiquide ou orpheline — et le spread est le prix du gel de capital, pas une option gratuite.
- **Pas d'ajustement de convexité.** Deux obligations au même Z-spread mais convexités différentes (callable vs bullet, perpétuelles) ne sont pas équivalentes. Le scoring les traite identiquement.
- **Fondamentaux en retard sur le marché.** Les ratios CET1, levier, et Solvency II sont publiés trimestriellement. Le marché crédit reprice à la seconde. Tout scoring basé sur les fondamentaux est structurellement backward-looking.

### 9.3 Limites de la Couche Sectorielle / Macro

- **Subjectivité de la perspective de croissance.** Qualifier un secteur de "porteur" (IA, défense) est un call de consensus potentiellement déjà pricé. Le marché crédit price le *risque*, pas la *croissance equity* — un secteur en hyper-croissance avec un capex délirant peut être plus risqué.
- **Risque macro statique.** Un seul nombre pour "exposition géopolitique au pays X" ne peut remplacer une analyse granulaire revenue-by-country. Une corporate avec 30% Chine en 2019 n'a pas le même profil de risque qu'en 2025.
- **La croissance sectorielle contribue au reward, pas à une décote de risque.** C'est discutable : certains argueraient que les secteurs en croissance méritent un *premium de risque* (plus d'incertitude, plus de risque de disruption), pas un *premium de reward*.

### 9.4 Pièges Comportementaux / d'Usage

- **Fausse précision.** Reporter les scores avec deux décimales crée une illusion d'exactitude. Le modèle doit être utilisé comme un outil de **screening**, jamais comme signal de trading standalone.
- **Pas de signal de timing.** Le Score RV dit ce qui est cheap. Il ne dit pas *quand* acheter. Une obligation qui screene cheap aujourd'hui peut le rester six mois.
- **Risque de biais de survie.** Les émetteurs en défaut sortent de l'univers au fil du temps, biaisant toute calibration historique vers le haut.

### 9.5 Roadmap d'Amélioration

1. **Distance-to-default Merton-style** pour les corporates (utilise vol equity et levier)
2. **Modèle factoriel** — régresser les spreads contre (rating, secteur, duration, taille), extraire les résidus comme "vrai" signal de relative value (model-implied vs observed)
3. **Affinement de l'overlay liquidité** via données de transaction TRACE/MiFID II plutôt que bid-ask statique
4. **Overlay ESG** — les primes/décotes de durabilité sont désormais pricées sur l'IG euro
5. **Backtest historique** du Score RV sur 5 ans pour mesurer la performance forward 6M des cohortes high-RV vs low-RV
6. **Overlay de stress** — à quoi ressemble le spread de chaque obligation dans un choc taux -2σ ou une récession sectorielle ?

---

## 10. Guide Utilisateur — Rafraîchissement du Process

### Mode batch (fichiers de configuration)
1. **Mettre à jour `inputs.csv`** avec les dernières données obligataires
2. **Éventuellement ajuster `weights.yaml`** pour tester des méthodologies alternatives
3. Lancer `python scoring_engine.py` — génère un `scores.csv` à jour
4. Lancer `streamlit run dashboard.py` — visualisation auto-rafraîchie

### Mode interactif (sidebar du dashboard)
1. Lancer `streamlit run dashboard.py`
2. Modifier directement les pondérations dans la section **Pondérations** de la sidebar
3. Les scores et le bubble chart se recalculent automatiquement
4. Cliquer **Reset aux pondérations par défaut** pour revenir à la calibration de base

Le process est conçu pour être re-runnable **chaque semaine voire chaque jour** avec un effort minimal, supportant à la fois le monitoring de l'univers existant et le scoring rapide de nouvelles émissions primaires (DCM / Private Debt screening).

---

*Méthodologie v1.0 — juin 2026.*
