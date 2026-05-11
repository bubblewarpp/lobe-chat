'use client';

import dynamic from 'next/dynamic';

const DevPanelInner = dynamic(() => import('@/features/DevPanel'), { ssr: false });

const DevPanel = () => {
  if (process.env.NODE_ENV !== 'development') return null;

  return <DevPanelInner />;
};

export default DevPanel;
