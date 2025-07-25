'use client';

import React from 'react';
import { QueueListIcon, XMarkIcon } from '@heroicons/react/24/outline';

// This component is deprecated with server-side streaming
const QueueManager: React.FC = () => {
  return (
    <button
      disabled
      className="text-gray-600 cursor-not-allowed"
      title="Queue management is handled server-side"
    >
      <QueueListIcon className="h-5 w-5" />
    </button>
  );
};

export default QueueManager;