# תפילה (tfilah.com): העלאה לאוויר

האתר הוא אתר סטטי, וקיר הנרות ומורה הדרך הם תוספות שמפעילים בנפרד.
הסידור, התהילים, החיפוש והשמורים עובדים מיד, בלי שום הגדרה.

## 1. העלאה ל-Cloudflare Pages (חינם)

1. נכנסים ל-dash.cloudflare.com ופותחים חשבון.
2. Workers & Pages ← Create ← Pages ← **Upload assets**.
3. שם הפרויקט: `tfilah`. גוררים את **כל התיקייה** (כולל `functions`).
   הערה: פונקציות (`functions/`) עובדות בהעלאה דרך Git או דרך `wrangler pages deploy`. אם גוררים בדפדפן והמורה לא עונה, מעלים כך:
   `npx wrangler pages deploy . --project-name tfilah`
4. אחרי ההעלאה: Custom domains ← Set up a custom domain ← `tfilah.com`.
5. ב-Spaceship: Domain ← Nameservers ← מחליפים לשני השרתים ש-Cloudflare נותן. תוך כמה שעות האתר עולה ב-tfilah.com.

## 2. קיר הנרות וחלוקת התהילים (Supabase, חינם)

1. supabase.com ← New project.
2. SQL Editor ← New query ← מדביקים את כל `supabase.sql` ← Run.
3. Project Settings ← API: מעתיקים את **Project URL** ואת המפתח **anon / publishable**.
4. ממלאים ב-`config.js` את `supabaseUrl` ואת `supabaseAnonKey`, ומעלים שוב.
   לעולם לא שמים כאן את מפתח ה-`service_role`.
5. להסתרת דף זיכרון לא ראוי: Table Editor ← memorials ← מסמנים `hidden = true`.

## 3. מורה הדרך AI (בתשלום לפי שימוש)

1. console.anthropic.com ← API Keys ← Create Key. מגדירים שם מגבלת הוצאה חודשית.
2. ב-Cloudflare: הפרויקט ← Settings ← Variables and Secrets ← מוסיפים Secret בשם `ANTHROPIC_API_KEY`.
3. ב-`config.js`: `aiEnabled: true`, ומעלים שוב.
4. מומלץ: Cloudflare ← Security ← WAF ← Rate limiting rule על `/api/ask` (למשל 10 בקשות לדקה לכל IP).

המודל מוגדר ב-`functions/api/ask.js` (ברירת מחדל Haiku, הזול והמהיר).

## 4. תרומות

ממלאים ב-`config.js` את `donateUrl` בקישור לדף התשלום. הכפתור באתר מוסיף לקישור `?amount=` עם הסכום שנבחר. אם דף התשלום לא תומך בזה, זה פשוט לא משפיע.

## 5. אפליקציה בטלפון

האתר מוכן להתקנה כאפליקציה: בטלפון נכנסים ל-tfilah.com ← שיתוף / תפריט ← "הוסף למסך הבית".
הסידור והתהילים עובדים גם בלי אינטרנט אחרי הכניסה הראשונה (למשל בבית כנסת בלי קליטה).
כשמעדכנים את האתר, משנים ב-`sw.js` את `VERSION` (למשל ל-`tfilah-v3`) כדי שכולם יקבלו את הגרסה החדשה.

תמונת השיתוף בוואטסאפ ובפייסבוק: `icons/og.png`.

## עדכון: תפילת רבים (רפואה, זיווג, הצלחה, כללי)

אם כבר הרצתם את `supabase.sql` בגרסה הקודמת, הריצו שוב את כל הקובץ: הוא מוסיף את סוג התפילה (`kind`).
אם מופיעה שגיאה על עמודה קיימת, הריצו קודם את שתי השורות שבסוף הקובץ (עם `alter table`).

## עדכון: סבבים בחלוקת התהילים
כשמסיימים את כל 150 הפרקים, מתחיל אוטומטית סבב חדש. אם כבר יש לכם מסד נתונים, הריצו ב-SQL Editor את שתי השורות שבסוף `supabase.sql` (בלי סימני ה-`--`).

## פיתוח (קוד)
- `src/app.html`: קוד המקור של האפליקציה.
- `python3 tools/build.py src/app.html index.html`: בונה את `index.html` לאתר.
- `python3 tools/prerender.py`: מייצר כ-960 דפים סטטיים לגוגל (`/tehillim/23/`, `/tefila/...`, `/sefer/...`) ואת `sitemap.xml`.
- אחרי כל שינוי: מריצים את שתי הפקודות, מעלים את `VERSION` ב-`sw.js`, ועושים deploy.

## קידום בגוגל
1. Google Search Console ← Add property ← `tfilah.com` ← מאמתים דרך DNS ב-Cloudflare.
2. Sitemaps ← `sitemap.xml` ← Submit.
3. אותו דבר ב-Bing Webmaster Tools (מייבא מ-Search Console בלחיצה).

## מיתוג
- שם המותג בממשק: „תפילה”. הדומיין `tfilah.com` הוא חתימה משנית.
- `brand/`: הלוגו כ-SVG וקטורי (בלי תמונה מוטמעת ובלי תלות בפונט): `mark.svg`, `mark-mono.svg`, `favicon.svg`, `icon-maskable.svg`, `logo.svg`, `logo-header.svg`.
- `python3 tools/build-logo.py <frank-ruhl-900.woff> <heebo-500.woff>` מייצר אותם מחדש. הלוגו שבכותרת האפליקציה מוטמע ב-`src/app.html`; אם משנים את הסמל, מעדכנים גם שם.
- צבעים: נייר `#F6F0E4`, דיו `#351A29`, אדום חותמת `#A3342B`. שכבת העיצוב נמצאת בסוף ה-CSS של `src/app.html` תחת ההערה `SEFER`.

## תהילים יחד (עדכון מסד הנתונים)
- מריצים את כל `supabase.sql` ב-SQL Editor. הקובץ בטוח להרצה חוזרת, גם על מסד קיים מהגרסה הקודמת.
- קריאה חדשה היא פרטית כברירת מחדל: רק מי שיש לו את הקישור רואה אותה. מי שפותח יכול לסמן שתופיע ברשימה הציבורית.
- הקצאת פרק וסימון „קראתי” נעשים בפונקציות בשרת, כך ששני קוראים לא מקבלים אותו פרק והספירה נשארת נכונה.
- פרק שנלקח ולא נקרא תוך 24 שעות חוזר להיות פנוי.

## בדיקות
- `python3 tools/seo-audit.py`: בודק את כל הדפים המחוללים ואת מפת האתר (canonical, H1, כותרות כפולות, קישורים פנימיים).
- `python3 tools/test-supabase.py`: בדיקות מקביליות של `supabase.sql` ושל `shim.js` מול Postgres מקומי.
