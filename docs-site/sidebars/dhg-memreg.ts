import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  memregSidebar: [
    'getting-started',
    'features',
    'capture-scripts',
    'ingestion',
    'hooks',
    'kb-search',
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/data-model',
      ],
    },
    'operations',
  ],
};

export default sidebars;
