# GameDeal Aggregator

Agrégateur de prix de jeux vidéo, sources actuelles : [IsThereAnyDeal](https://isthereanydeal.com) (API officielle) et Instant Gaming (index Algolia public du site).

## Stack

- **Backend** : FastAPI (Python) — `backend/`
- **Frontend** : React + Vite — `frontend/`
- **Cache** : Redis (résultats de recherche, TTL 15 min)

## Lancer en local

```bash
cp backend/.env.example backend/.env
# renseigner ITAD_API_KEY dans backend/.env (clé gratuite sur https://isthereanydeal.com/apps/my/)

docker compose up --build
```

- Frontend direct (debug) : http://localhost:4273
- Backend direct (debug) : http://localhost:8100/api/health
- **App via reverse proxy Caddy (recommandé)** :
  - HTTP : http://\<IP\>:8090
  - HTTPS (certificat auto-signé) : https://\<IP\>:8443 — nécessaire pour le partage natif (Web Share API), qui exige un contexte sécurisé. Accepter l'avertissement de certificat au premier accès.

## Notes

- Le frontend est buildé avec une base d'API relative (`VITE_API_BASE=""`), donc il doit passer par Caddy (ports 8090/8443) pour fonctionner correctement — l'accès direct au port 4273 seul ne proxifie pas `/api/*`.
- Voir `Caddyfile` pour la config source et `caddy.json` pour la config réellement utilisée (contient un réglage `default_sni` non exprimable en syntaxe Caddyfile, nécessaire car les clients TLS n'envoient pas de SNI pour une IP littérale).

- La clé Algolia d'Instant Gaming est une clé "search-only" publique exposée côté client sur leur site — pas de credentials propriétaires impliqués, mais ce n'est pas une API contractuelle documentée : elle peut changer sans préavis.
- G2A a été exclu (protection Akamai Bot Manager + Forter, non exploitable simplement).
