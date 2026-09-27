const REPO = "erdalyaslica/maltepe-yemek-mail";
async function send(env, text) {
  const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({chat_id: env.TG_ALLOWED_CHAT_ID, text})
  });
  if (!r.ok || !(await r.json()).ok) throw new Error("Telegram gönderimi başarısız");
}
export function command(text) {
  return String(text || "").trim().replace(/^\/\s+/, "/").split(/\s+/)[0].split("@")[0].toLocaleLowerCase("tr");
}
export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== "/telegram" || request.method !== "POST")
      return new Response("Not found", {status:404});
    if (!env.WEBHOOK_SECRET || request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET)
      return new Response("Forbidden", {status:403});
    let update;
    try { update = await request.json(); } catch { return new Response("Bad request", {status:400}); }
    const m = update.message;
    if (!m || String(m.chat?.id) !== String(env.TG_ALLOWED_CHAT_ID) || !m.text)
      return new Response("OK");
    const c = command(m.text);
    try {
      if (c === "/test") {
        await send(env, "✅ Yemek botunun Telegram bağlantısı çalışıyor.");
      } else if (["/bugün","/bugun","/yarın","/yarin","/hafta"].includes(c)) {
        const canonical = {"/bugün":"bugun","/bugun":"bugun","/yarın":"yarin","/yarin":"yarin","/hafta":"hafta"}[c];
        const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/telegram-webhook.yml/dispatches`, {
          method:"POST",
          headers:{"Authorization":`Bearer ${env.GH_TOKEN}`,"Accept":"application/vnd.github+json","User-Agent":"maltepe-yemek-worker","Content-Type":"application/json"},
          body:JSON.stringify({ref:"main",inputs:{command:canonical,requested_at:String(m.date || Math.floor(Date.now()/1000))}})
        });
        if (!r.ok) throw new Error("GitHub görevi başlatılamadı");
        await send(env, "⏳ Menü isteğin alındı. GitHub'da hazırlanıyor; sonuç burada bildirilecek.");
      } else {
        await send(env, "🍽️ Maltepe Yemek Botu\n\n/bugun veya /bugün — Bugünün menüsü\n/yarin veya /yarın — Yarının menüsü\n/hafta — Haftanın menüsü (hafta sonunda gelecek hafta)\n/test — Bağlantı testi\n/yardim — Komutlar");
      }
    } catch {
      console.error("Yemek komutu işlenemedi");
      try { await send(env,"⚠️ İstek tamamlanamadı. GitHub ve Cloudflare bağlantı ayarlarını kontrol edin."); } catch {}
    }
    return new Response("OK");
  }
};
