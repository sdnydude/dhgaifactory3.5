import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'DHG Documentation',
  tagline: 'Digital Harmony Group — engineering documentation for all projects',
  favicon: 'img/favicon.ico',

  url: 'http://10.0.0.251',
  baseUrl: '/',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

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
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'DHG Docs',
      items: [
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
            {label: 'AI Factory', to: '/dhg-ai-factory/getting-started'},
            {label: 'Memreg', to: '/dhg-memreg/getting-started'},
            {label: 'Memory Pipeline', to: '/memory-pipeline/getting-started'},
            {label: 'Portage', to: '/portage/getting-started'},
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
