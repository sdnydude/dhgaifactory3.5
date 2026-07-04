/* Patchbay service map. `statusKey` matches registry patchbay_service.SERVICES
   so LEDs reflect live TCP probes. `project` ties an app/doc to a docs project
   so Talkback citations can light the right modules. */

export const LAN = 'http://10.0.0.251';
export const TS = 'http://100.107.14.51';

export type Jack = 'TUNNEL' | 'LAN' | 'TS';

export interface Module {
  name: string;
  port?: number;
  desc: string;
  statusKey?: string;      // registry status key; absent → static state
  staticState?: 'on' | 'warn' | 'off';
  tunnel?: string;         // tunnel hostname → the hot (TUNNEL) jack
  path?: string;           // suffix for LAN/TS links, e.g. '/dashboard'
  jacks: Jack[];
  project?: string;        // docs project this module belongs to
  keywords?: string;       // extra filter/citation match terms
}

export interface Rack {
  title: string;
  code: string;
  modules: Module[];
}

export interface Tape {
  spine: string;
  title: string;
  desc: string;
  href: string;
  project: string;
  keywords?: string;
}

export const racks: Rack[] = [
  {
    title: 'Apps',
    code: 'RACK 01',
    modules: [
      {name: 'Frontend', port: 3000, statusKey: 'frontend', desc: 'Chat and human-review inbox', tunnel: 'https://app.digitalharmonyai.com', jacks: ['TUNNEL']},
      {name: 'Open WebUI', port: 3080, statusKey: 'open-webui', desc: 'Chat with local + cloud models', tunnel: 'https://chat.digitalharmonyai.com', jacks: ['TUNNEL'], project: 'open-webui'},
      {name: 'Portage', port: 3002, statusKey: 'portage', desc: 'Inventory & marketplace selling', tunnel: 'https://portage.digitalharmonyai.com', jacks: ['TUNNEL'], project: 'portage'},
      {name: 'Promptmaster', port: 8020, statusKey: 'promptmaster', desc: 'Prompt library & management', jacks: ['LAN', 'TS'], keywords: 'prompt'},
      {name: 'LM Studio', port: 1234, staticState: 'off', desc: 'Model server on the Mac (fafaudiodesk)', jacks: ['TS'], keywords: 'model mac'},
      {name: 'Registry API', port: 8011, statusKey: 'registry', desc: 'Swagger for the DHG registry', tunnel: 'https://registry.digitalharmonyai.com/docs', path: '/docs', jacks: ['TUNNEL'], project: 'dhg-ai-factory'},
      {name: 'VS Engine', port: 8013, statusKey: 'vs-engine', desc: 'Verbalized Sampling engine', tunnel: 'https://vs.digitalharmonyai.com/docs', path: '/docs', jacks: ['TUNNEL']},
    ],
  },
  {
    title: 'Monitoring',
    code: 'RACK 02',
    modules: [
      {name: 'Grafana', port: 3001, statusKey: 'grafana', desc: 'Golden signals, Mission Control', tunnel: 'https://grafana.digitalharmonyai.com', jacks: ['TUNNEL', 'LAN']},
      {name: 'Prometheus', port: 9090, statusKey: 'prometheus', desc: 'Metrics, targets, alert rules', jacks: ['LAN', 'TS']},
      {name: 'Alertmanager', port: 9093, statusKey: 'alertmanager', desc: 'Routing and silences', jacks: ['LAN', 'TS']},
      {name: 'cAdvisor', port: 8080, statusKey: 'cadvisor', desc: 'Per-container CPU / mem / net', jacks: ['LAN', 'TS']},
    ],
  },
  {
    title: 'Data & Admin',
    code: 'RACK 03',
    modules: [
      {name: 'pgAdmin', port: 5050, statusKey: 'pgadmin', desc: 'PostgreSQL administration', jacks: ['LAN', 'TS'], keywords: 'postgres database'},
      {name: 'MinIO', port: 9001, statusKey: 'minio', desc: 'Object storage console', jacks: ['LAN', 'TS']},
      {name: 'Qdrant', port: 6333, statusKey: 'qdrant', desc: 'Vector DB dashboard', path: '/dashboard', jacks: ['LAN', 'TS']},
      {name: 'Terminal', port: 8022, statusKey: 'terminal', desc: 'Web shell — private network only', jacks: ['LAN', 'TS']},
      {name: 'medkb API', port: 8015, statusKey: 'medkb', desc: 'RAG-as-a-Service', path: '/docs', jacks: ['LAN', 'TS']},
    ],
  },
  {
    title: 'Labs',
    code: 'RACK 04',
    modules: [
      {name: 'AG-UI POC', port: 8104, statusKey: 'agui-poc', desc: 'Two-agent CopilotKit experiment', jacks: ['LAN']},
      {name: 'LangGraph Dev', port: 2026, statusKey: 'langgraph-dev', desc: 'Graph dev server — dev only', jacks: ['LAN'], keywords: 'dev'},
      {name: 'Logo Maker', port: 8012, statusKey: 'logo-maker', desc: 'Stopped — docker start away', jacks: ['LAN']},
      {name: 'Portage Dev', port: 3003, statusKey: 'portage-dev', desc: 'Development instance', jacks: ['LAN'], project: 'portage'},
    ],
  },
];

export const tapes: Tape[] = [
  {spine: 'Factory', title: 'AI Factory', desc: 'LangGraph agents, orchestrators, and the registry', href: '/dhg-ai-factory/getting-started', project: 'dhg-ai-factory', keywords: 'langgraph agents registry'},
  {spine: 'Portage', title: 'Portage', desc: 'Scan-to-listing pipeline, marketplace adapters, API', href: '/portage/getting-started', project: 'portage', keywords: 'ebay seller inventory listing'},
  {spine: 'Memreg', title: 'Memreg', desc: 'Knowledge base and memory capture pipeline', href: '/dhg-memreg/getting-started', project: 'dhg-memreg', keywords: 'kb memory capture'},
  {spine: 'Memory', title: 'Memory Pipeline', desc: 'Session hooks, capture scripts, endpoints', href: '/memory-pipeline/getting-started', project: 'memory-pipeline', keywords: 'hooks session'},
  {spine: 'WebUI', title: 'Open WebUI', desc: 'Models, tools, slash commands, knowledge bases', href: '/open-webui/getting-started', project: 'open-webui', keywords: 'chat models tools'},
  {spine: 'Infra', title: 'Infrastructure', desc: 'Doppler, Cloudflare tunnels, shared services', href: '/infrastructure/getting-started', project: 'infrastructure', keywords: 'doppler tunnels secrets'},
];

export interface OffsiteLink {
  label: string;
  href: string;
}

export const offsite: OffsiteLink[] = [
  {label: 'github/sdnydude', href: 'https://github.com/sdnydude'},
  {label: 'smith.langchain.com', href: 'https://smith.langchain.com'},
  {label: 'dashboard.doppler.com', href: 'https://dashboard.doppler.com'},
  {label: 'one.dash.cloudflare.com', href: 'https://one.dash.cloudflare.com'},
  {label: 'console.anthropic.com', href: 'https://console.anthropic.com'},
  {label: 'drive.google.com', href: 'https://drive.google.com'},
];

export const suggestions: string[] = [
  'how do I publish a listing to eBay?',
  'why is Logo Maker stopped?',
  'where do agent traces go?',
];
