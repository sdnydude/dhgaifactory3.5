import React from 'react';
import Layout from '@theme/Layout';
import Patchbay from '@site/src/components/Patchbay';

export default function Home(): React.ReactElement {
  return (
    <Layout
      title="DHG Patchbay"
      description="Digital Harmony Group — documentation and live-service launchpad with the Talkback assistant"
      noFooter
    >
      <Patchbay />
    </Layout>
  );
}
