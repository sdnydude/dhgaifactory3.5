import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'DHG Documentation',
  tagline: 'Digital Harmony Group — engineering documentation for all projects',
  favicon: 'img/favicon.svg',

  url: 'https://docs.digitalharmonyai.com',
  baseUrl: '/',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  markdown: {
    hooks: {
      onBrokenMarkdownImages: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'projects',
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          // Ship-log files are NNN-prefixed and their generated indexes link by
          // filename — keep URLs identical to filenames.
          numberPrefixParser: false,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        docsRouteBasePath: '/',
        indexBlog: false,
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'DHG Docs',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'projectsSidebar',
          position: 'left',
          label: 'Projects',
        },
        {
          type: 'dropdown',
          label: 'Tools',
          position: 'left',
          items: [
            {label: 'DHG Promptmaster', href: 'http://10.0.0.251:8020'},
            {label: 'Open WebUI', href: 'https://chat.digitalharmonyai.com'},
            {label: 'Portage', href: 'https://portage.digitalharmonyai.com'},
            {label: 'Grafana', href: 'https://grafana.digitalharmonyai.com'},
            {label: 'Prometheus (LAN)', href: 'http://10.0.0.251:9090'},
            {label: 'pgAdmin (LAN)', href: 'http://10.0.0.251:5050'},
            {label: 'Registry API', href: 'https://registry.digitalharmonyai.com/docs'},
          ],
        },
        {
          href: 'https://github.com/sdnydude',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Projects',
          items: [
            {label: 'Infrastructure', to: '/infrastructure/getting-started'},
            {label: 'AI Factory', to: '/dhg-ai-factory/getting-started'},
            {label: 'Memreg', to: '/dhg-memreg/getting-started'},
            {label: 'Memory Pipeline', to: '/memory-pipeline/getting-started'},
            {label: 'Open WebUI', to: '/open-webui/getting-started'},
            {label: 'Portage', to: '/portage/getting-started'},
          ],
        },
        {
          title: 'Services',
          items: [
            {label: 'DHG Frontend', href: 'https://app.digitalharmonyai.com'},
            {label: 'DHG Promptmaster (LAN)', href: 'http://10.0.0.251:8020'},
            {label: 'Grafana', href: 'https://grafana.digitalharmonyai.com'},
            {label: 'Prometheus (LAN)', href: 'http://10.0.0.251:9090'},
            {label: 'pgAdmin (LAN)', href: 'http://10.0.0.251:5050'},
            {label: 'Open Terminal (LAN)', href: 'http://10.0.0.251:8022'},
          ],
        },
        {
          title: 'External',
          items: [
            {label: 'GitHub', href: 'https://github.com/sdnydude'},
            {label: 'LangSmith', href: 'https://smith.langchain.com'},
            {label: 'Doppler', href: 'https://dashboard.doppler.com'},
            {label: 'Cloudflare Zero Trust', href: 'https://one.dash.cloudflare.com'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Digital Harmony Group`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'yaml', 'sql', 'typescript'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
