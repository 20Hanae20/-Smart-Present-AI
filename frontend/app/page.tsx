import Link from 'next/link';
import { ArrowRight, Bell, ChartBar, Shield, Users } from 'lucide-react';

export const dynamic = 'force-dynamic';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-12 px-6 py-16">
      <header className="flex items-center justify-between">
        <div className="text-2xl font-semibold">
          Smart Presence <span className="text-primary-400">AI</span>
        </div>
        <Link href="/auth/login" className="btn-primary text-sm">
          Connexion
        </Link>
      </header>

      <section className="grid gap-10 md:grid-cols-2 md:items-center">
        <div className="space-y-6">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-200/90">
            AI-Powered
          </p>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            Système intelligent de gestion de présence.
          </h1>
          <p className="text-lg text-white/70">
            Choisissez mot de passe ou reconnaissance faciale à la connexion. Des tableaux de bord
            multi-rôles, des analyses en temps réel, des notifications intelligentes et des rapports
            avancés prêts à l'emploi.
          </p>
          <div className="flex flex-wrap gap-3 text-sm text-white/80">
            <Feature label="Reconnaissance faciale" Icon={Shield} />
            <Feature label="Analytique temps réel" Icon={ChartBar} />
            <Feature label="Multi-rôles" Icon={Users} />
            <Feature label="Notifications smart" Icon={Bell} />
            <Feature label="Rapports PDF/Excel" Icon={ArrowRight} />
          </div>
          <div className="flex gap-3">
            <Link href="/auth/login" className="btn-primary">
              Commencer
            </Link>
            <a href="#features" className="inline-flex items-center gap-2 text-sm text-amber-300">
              Voir les fonctionnalités <ArrowRight size={16} />
            </a>
          </div>
        </div>
        <div className="card border-primary-500/20 bg-gradient-to-br from-white/5 to-primary-500/10">
          <div className="space-y-4">
            <p className="text-sm text-white/70">Aperçu rapide</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <MiniStat label="Présents" value="94%" tone="text-emerald-300" />
              <MiniStat label="Retards" value="4%" tone="text-amber-300" />
              <MiniStat label="Absences" value="2%" tone="text-rose-300" />
              <MiniStat label="Alertes" value="3" tone="text-sky-300" />
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-white/70">
              <p className="font-semibold text-white">Flux d'authentification</p>
              <p>1) Email, 2) Choix mot de passe ou visage, 3) Validation &lt; 2s.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="grid gap-6 md:grid-cols-3">
        <Card
          title="Connexion hybride"
          description="Mot de passe ou visage (3 photos à l\'enrôlement), sécurité simple et rapide."
        />
        <Card
          title="Dashboards rôle"
          description="Admins, formateurs, étudiants : chaque profil a ses vues, ses actions."
        />
        <Card
          title="Présences & rapports"
          description="Pointage, justifications, pourcentage, exports PDF/Excel/CSV en un clic."
        />
      </section>
    </main>
  );
}

function Feature({ label, Icon }: { label: string; Icon: React.ComponentType<any> }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
      <Icon size={16} /> {label}
    </span>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-white/5 bg-white/5 p-3">
      <p className="text-white/60">{label}</p>
      <p className={`text-xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function Card({ title, description }: { title: string; description: string }) {
  return (
    <div className="card h-full">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm text-white/70">{description}</p>
    </div>
  );
}
