import { createFileRoute } from "@tanstack/react-router";
import { Activity, ArrowDownToLine, Cloud, FolderSync, KeyRound, Link2, LockKeyhole, RadioTower, ShieldCheck, Smartphone, Unplug } from "lucide-react";

export const Route = createFileRoute("/portal")({
  head: () => ({
    meta: [
      { title: "TeleDrive Portal — لوحة التحكم" },
      { name: "description", content: "بوابة TeleDrive الموحدة لإدارة اتصالات Google Drive وTelegram ومحرك النقل." },
    ],
  }),
  component: PortalPage,
});

const connections = [
  { name: "تسجيل الدخول", detail: "هوية المستخدم وحماية حسابه", icon: LockKeyhole },
  { name: "Google Drive", detail: "تفويض منفصل للوصول إلى الملفات", icon: Cloud },
  { name: "Telegram", detail: "ربط حساب المستخدم أو إعدادات البوت حسب الوظيفة", icon: Smartphone },
  { name: "محرك TeleDrive", detail: "عامل Colab الحالي — دون تغيير طريقة تشغيله", icon: RadioTower },
];

function Status({ children }: { children: string }) {
  return <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground"><span className="h-2 w-2 rounded-full bg-muted-foreground/60" />{children}</span>;
}

function PortalPage() {
  return (
    <main dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground" style={{ fontFamily: "system-ui, -apple-system, 'Segoe UI', Tahoma, sans-serif" }}>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground"><FolderSync size={25} /></div>
            <div><p className="text-sm text-muted-foreground">بوابة التحكم الموحدة</p><h1 className="text-2xl font-bold tracking-tight">TeleDrive</h1></div>
          </div>
          <Status>لم يتم تسجيل الدخول</Status>
        </header>

        <section className="grid gap-6 py-8 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="rounded-3xl border border-border bg-card p-6 sm:p-8">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1 text-xs font-medium"><ShieldCheck size={15} /> خصوصية المستخدم أولاً</div>
            <h2 className="max-w-2xl text-3xl font-bold leading-tight sm:text-4xl">كل اتصالاتك ومهامك من مكان واحد.</h2>
            <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">اربط حساباتك، جهّز محرك النقل، وتابع الطابور من لوحة واحدة. ستظهر حالة الاتصال الفعلية فقط؛ لن نعرض تقدّمًا أو مهامًا تجريبية على أنها حقيقية.</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button type="button" disabled className="inline-flex cursor-not-allowed items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground opacity-60"><KeyRound size={17} /> تسجيل الدخول عبر Google <span className="text-xs">(يتطلب إعداد OAuth)</span></button>
              <a href="#connections" className="inline-flex items-center gap-2 rounded-xl border border-border px-5 py-3 text-sm font-semibold hover:bg-muted"><Link2 size={17} /> إعداد الاتصالات</a>
            </div>
          </div>
          <div className="rounded-3xl border border-border bg-card p-6">
            <div className="flex items-center justify-between"><h2 className="font-semibold">حالة الخدمة</h2><Activity size={18} className="text-muted-foreground" /></div>
            <div className="mt-5 space-y-4">
              {[["بوابة الويب","متاحة للعرض"],["Google Drive","غير متصل"],["Telegram","غير متصل"],["محرك النقل","لم يتم التحقق"]].map(([label,value]) => <div key={label} className="flex items-center justify-between gap-3 border-b border-border pb-3 last:border-0"><span className="text-sm text-muted-foreground">{label}</span><Status>{value}</Status></div>)}
            </div>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">هذه حالة التهيئة الحالية وليست فحصًا حيًا للمحرك. ستتحول الحالة إلى حية بعد إضافة المصادقة وخدمة heartbeat الآمنة.</p>
          </div>
        </section>

        <section id="connections" className="py-3">
          <div className="mb-5"><h2 className="text-xl font-bold">الاتصالات والإعداد</h2><p className="mt-1 text-sm text-muted-foreground">خطوات منفصلة وواضحة، مع حفظ بيانات الاعتماد في الخادم فقط.</p></div>
          <div className="grid gap-4 md:grid-cols-2">
            {connections.map(({ name, detail, icon: Icon }, index) => <article key={name} className="rounded-2xl border border-border bg-card p-5">
              <div className="flex items-start gap-4"><div className="rounded-xl bg-muted p-3"><Icon size={21} /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">{index + 1}. {name}</h3><Status>{index === 0 ? "غير مهيأ" : "غير متصل"}</Status></div><p className="mt-2 text-sm leading-6 text-muted-foreground">{detail}</p></div></div>
            </article>)}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-border bg-muted/30 p-5 sm:p-6">
          <div className="flex items-start gap-3"><Unplug size={20} className="mt-1 text-muted-foreground" /><div><h2 className="font-semibold">المحرك الحالي على Colab محفوظ</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">هذه البوابة لا تستبدل Notebook الحالي ولا تغيّر تشغيله. في مرحلة الربط سيبدأ العامل اتصالًا صادرًا ومصادقًا إلى البوابة؛ وإذا انتهت جلسة Colab ستعرض البوابة أنه غير متصل بدل إظهار نجاح غير مؤكد.</p></div></div>
        </section>

        <section className="mt-6 rounded-2xl border border-border p-5 sm:p-6">
          <div className="flex items-center gap-2"><ArrowDownToLine size={19} /><h2 className="font-semibold">لوحة المهام</h2></div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">لن تظهر أوامر بدء التنزيل أو الطابور أو السرعة إلا بعد ربط API موثّق بالمحرك الحقيقي. لا توجد مهام تجريبية في هذه الصفحة.</p>
        </section>
        <footer className="py-8 text-center text-xs text-muted-foreground">TeleDrive Portal · مرحلة تأسيس الواجهة · لا تُدخل كلمات مرور أو رموز جلسات في هذه الصفحة.</footer>
      </div>
    </main>
  );
}
