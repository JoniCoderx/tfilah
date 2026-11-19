// הגדרות האתר tfilah.com
// זה הקובץ היחיד שצריך לערוך. ראו README.md.
window.TFILAH_CONFIG = {
  // Supabase: בשביל קיר הנרות וחלוקת התהילים. משאירים ריק כדי לכבות.
  supabaseUrl: "",       // לדוגמה: "https://abcd1234.supabase.co"
  supabaseAnonKey: "",   // המפתח הציבורי (anon / publishable), לא ה-service_role!

  // קישור לעמוד התרומה (Grow / PayPal / PayBox וכו'). משאירים ריק כדי להציג "בקרוב".
  donateUrl: "",

  // מורה הדרך AI: true רק אחרי שהגדרתם ANTHROPIC_API_KEY ב-Cloudflare.
  aiEnabled: false
};
