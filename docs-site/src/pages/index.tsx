import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

const LAN = 'http://10.0.0.251';
const TS = 'http://100.107.14.51';

type Card = {
  title: string;
  desc: string;
  href?: string; // absolute URL or internal doc path
  port?: number; // LAN/Tailscale service — renders paired links
  path?: string; // path suffix for port-based links, e.g. '/dashboard'
  badge?: 'LAN' | 'DEV' | 'STOPPED';
};

const projects: Card[] = [
  {title: 'Infrastructure', desc: 'Doppler, secrets, shared platform services', href: '/infrastructure/getting-started'},
  {title: 'AI Factory', desc: 'LangGraph agents, orchestrators, registry', href: '/dhg-ai-factory/getting-started'},
  {title: 'Memreg', desc: 'KB + memory capture pipeline and daemon', href: '/dhg-memreg/getting-started'},
  {title: 'Memory Pipeline', desc: 'Session hooks, capture scripts, registry endpoints', href: '/memory-pipeline/getting-started'},
  {title: 'Open WebUI', desc: 'Self-hosted chat: models, tools, knowledge bases', href: '/open-webui/getting-started'},
  {title: 'Portage', desc: 'AI-powered inventory & multi-marketplace seller', href: '/portage/getting-started'},
];

const apps: Card[] = [
  {title: 'DHG Frontend', desc: 'Next.js chat + human review inbox', href: 'https://app.digitalharmonyai.com'},
  {title: 'Open WebUI', desc: 'Chat with local + cloud models', href: 'https://chat.digitalharmonyai.com'},
  {title: 'Portage', desc: 'Inventory & marketplace seller platform', href: 'https://portage.digitalharmonyai.com'},
  {title: 'DHG Promptmaster', desc: 'Prompt library & management', port: 8020, badge: 'LAN'},
  {title: 'LM Studio (Mac)', desc: 'Local model server on fafaudiodesk — enable server in LM Studio Developer tab', href: 'http://100.124.179.71:1234', badge: 'LAN'},
  {title: 'Registry API', desc: 'Swagger for the DHG registry', href: 'https://registry.digitalharmonyai.com/docs'},
  {title: 'VS Engine API', desc: 'Verbalized Sampling engine', href: 'https://vs.digitalharmonyai.com/docs'},
  {title: 'Portage API', desc: 'Swagger for the Portage backend', href: 'https://portage-api.digitalharmonyai.com/docs'},
];

const observability: Card[] = [
  {title: 'Grafana', desc: 'Dashboards: golden signals, Docker, Mission Control, Memreg', href: 'https://grafana.digitalharmonyai.com', port: 3001},
  {title: 'Prometheus', desc: 'Metrics + targets + alert rules', port: 9090, badge: 'LAN'},
  {title: 'Alertmanager', desc: 'Alert routing and silences', port: 9093, badge: 'LAN'},
  {title: 'cAdvisor', desc: 'Per-container CPU / memory / network', port: 8080, badge: 'LAN'},
];

const dataAdmin: Card[] = [
  {title: 'pgAdmin', desc: 'PostgreSQL administration', port: 5050, badge: 'LAN'},
  {title: 'MinIO Console', desc: 'Object storage (transcribe stack)', port: 9001, badge: 'LAN'},
  {title: 'Qdrant', desc: 'Vector DB dashboard', port: 6333, path: '/dashboard', badge: 'LAN'},
  {title: 'Open Terminal', desc: 'Web terminal — LAN/Tailscale only, never tunneled', port: 8022, badge: 'LAN'},
  {title: 'medkb API', desc: 'Swagger for RAG-as-a-Service', port: 8015, path: '/docs', badge: 'LAN'},
];

const labs: Card[] = [
  {title: 'AG-UI × LangGraph POC', desc: 'Two-agent CopilotKit proof of concept', port: 8104, badge: 'DEV'},
  {title: 'LangGraph Dev Server', desc: 'Local graph dev — never wire prod to this', port: 2026, badge: 'DEV'},
  {title: 'Logo Maker', desc: 'Logo generation service', port: 8012, badge: 'STOPPED'},
  {title: 'Portage Dev', desc: 'Portage development instance', port: 3003, badge: 'DEV'},
];

const external: Card[] = [
  {title: 'GitHub', desc: 'sdnydude repositories', href: 'https://github.com/sdnydude'},
  {title: 'Google Drive', desc: 'DHG documents and shared files', href: 'https://drive.google.com'},
  {title: 'LangSmith', desc: 'Agent traces + LangGraph Cloud deployments', href: 'https://smith.langchain.com'},
  {title: 'Doppler', desc: 'Secrets management (8 projects)', href: 'https://dashboard.doppler.com'},
  {title: 'Cloudflare Zero Trust', desc: 'Tunnels, Access policies, DNS', href: 'https://one.dash.cloudflare.com'},
  {title: 'Anthropic Console', desc: 'Claude API usage and keys', href: 'https://console.anthropic.com'},
];

function badgeClass(badge: Card['badge']): string {
  if (badge === 'DEV') return 'dhgBadge dhgBadgeDev';
  if (badge === 'STOPPED') return 'dhgBadge dhgBadgeStopped';
  return 'dhgBadge dhgBadgeLan';
}

function ServiceCard({card}: {card: Card}) {
  const suffix = card.path ?? '';
  const primary = card.href ?? `${LAN}:${card.port}${suffix}`;
  const isExternal = primary.startsWith('http');
  return (
    <div className="dhgCard">
      <div className="dhgCardTitle">
        {isExternal ? (
          <a href={primary} target="_blank" rel="noopener noreferrer">{card.title}</a>
        ) : (
          <Link to={primary}>{card.title}</Link>
        )}
        {card.badge && <span className={badgeClass(card.badge)}>{card.badge}</span>}
      </div>
      <div className="dhgCardDesc">{card.desc}</div>
      {card.port && (
        <div className="dhgCardLinks">
          <a href={`${LAN}:${card.port}${suffix}`} target="_blank" rel="noopener noreferrer">LAN</a>
          <a href={`${TS}:${card.port}${suffix}`} target="_blank" rel="noopener noreferrer">Tailscale</a>
        </div>
      )}
    </div>
  );
}

function Section({title, cards}: {title: string; cards: Card[]}) {
  return (
    <section className="dhgSection">
      <h2>{title}</h2>
      <div className="dhgGrid">
        {cards.map((c) => (
          <ServiceCard key={c.title} card={c} />
        ))}
      </div>
    </section>
  );
}

export default function Home(): React.ReactElement {
  return (
    <Layout title="DHG Hub" description="Digital Harmony Group — documentation and service launchpad">
      <div className="dhgHero">
        <h1>DHG Documentation Hub</h1>
        <p>AI Agents In Tune With You — docs and launchpad for every DHG project and service.</p>
      </div>
      <Section title="Project Documentation" cards={projects} />
      <Section title="Apps" cards={apps} />
      <Section title="Observability" cards={observability} />
      <Section title="Data & Admin" cards={dataAdmin} />
      <Section title="Labs" cards={labs} />
      <Section title="Cloud & External" cards={external} />
    </Layout>
  );
}
