# Frontend Skill — cfb-agent

## Stack
React + Vite + Tailwind CSS + shadcn/ui
Deployed on Vercel. Root: `/frontend`. Build: `npm run build`. Output: `dist`.
API base URL via env var: `VITE_API_URL` (set in Vercel dashboard).

## API Client
All API calls go through `frontend/src/lib/client.js`.
Never call fetch() directly in components — always use the client.
```javascript
import api from '../lib/client'
// default import — not named import
```

## Component Conventions
- shadcn/ui components from `@/components/ui/`
- Tailwind utility classes only — no custom CSS files
- All pages in `frontend/src/pages/`
- Shared components in `frontend/src/components/`

## Pages
| Page | Path | Description |
|---|---|---|
| Games | /games | FBS games, model vs Vegas, value flags |
| Picks | /picks | Approved public picks |
| History | /picks/history | Full pick history with ATS tracking |
| Rankings | /rankings | Preseason composite for 137 FBS teams |
| CLV Dashboard | /clv | Closing line value summary + pick table |

## Display Rules
- Spread values: always `toFixed(1)` — never raw floats
- Win probability: `(value * 100).toFixed(1) + '%'`
- Edge: magnitude only, no + sign
- Pick spread: from pick team perspective
- Value pick badge: 🔥 on approved picks in Games page

## Known Gotchas
- Use default import for api client: `import api from '../lib/client'` not `import { api }`
- No duplicate `export default` in client.js
- Vite requires all env vars to be prefixed with `VITE_`
- shadcn/ui components must be installed individually — they are not tree-shaken from a bundle
