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

- Frontend : http://localhost:4173
- Backend : http://localhost:8000/api/search?q=elden+ring
- Healthcheck : http://localhost:8000/api/health

## Notes

- La clé Algolia d'Instant Gaming est une clé "search-only" publique exposée côté client sur leur site — pas de credentials propriétaires impliqués, mais ce n'est pas une API contractuelle documentée : elle peut changer sans préavis.
- G2A a été exclu (protection Akamai Bot Manager + Forter, non exploitable simplement).
