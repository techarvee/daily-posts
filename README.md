# daily-posts

Roz 5 carousel posts, apne aap **Instagram (@ravidigitalproduct)** aur **Facebook page (Ravi Verma)** par.

## Kaise chalta hai
- `content/*.json`: posts ka text (title, 4 tip slides, caption). Har file = 35 posts = 1 hafta.
- `scripts/render.py`: har post ke 6 slides (1080×1350 JPEG) `posts/<id>/` mein banata hai.
- `scripts/publish.py`: agla post Instagram carousel + Facebook multi-photo post ke roop mein publish karta hai.
- `.github/workflows/daily-posts.yml`: roz 5 baar chalta hai (IST 08:53, 11:53, 14:53, 17:53, 20:53).
- `state.json`: kaunse posts publish ho chuke hain.

## Ek baar ka setup (Meta token)
1. Instagram account ko **Professional (Business/Creator)** banao aur Facebook page "Ravi Verma" se link karo.
2. developers.facebook.com par ek app banao (type: Business).
3. **Graph API Explorer** mein ye permissions lo: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`.
4. User token ko long-lived banao, phir `me/accounts` se page ka **access token** aur **page id** lo (page token long-lived user token se lene par expire nahi hota).
5. `{page-id}?fields=instagram_business_account` se **IG user id** lo.
6. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:
   - `META_ACCESS_TOKEN` = page access token
   - `FB_PAGE_ID` = page id
   - `IG_USER_ID` = instagram business account id

## Test
**Actions → Daily posts → Run workflow** → "dry_run" tick karke chalao. Logs mein agla post aur image links dikhenge.

## Naye posts add karna
`content/week02.json` same format mein banao aur push karo. Images workflow khud bana dega.
