'use client';

import React, { useState } from 'react';
import { QuestionMarkCircleIcon, XMarkIcon } from '@heroicons/react/24/outline';

const KeyboardShortcutsHelp: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const shortcuts = [
    { key: 'Space', description: 'Play/Pause current track' },
    { key: 'Shift + ←', description: 'Previous track' },
    { key: 'Shift + →', description: 'Next track' },
    { key: 'Shift + ↑', description: 'Volume up' },
    { key: 'Shift + ↓', description: 'Volume down' },
    { key: 'Ctrl/Cmd + M', description: 'Toggle mute' },
    { key: '← / →', description: 'Seek backward/forward (on progress bar)' },
    { key: 'Home / End', description: 'Jump to start/end (on progress bar)' },
  ];

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="text-gray-400 hover:text-white transition"
        title="Keyboard shortcuts"
        aria-label="Show keyboard shortcuts"
      >
        <QuestionMarkCircleIcon className="h-5 w-5" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg p-6 max-w-md w-full mx-4 border border-zinc-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Keyboard Shortcuts</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white transition"
                aria-label="Close"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3">
              {shortcuts.map((shortcut, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{shortcut.description}</span>
                  <kbd className="px-2 py-1 bg-zinc-800 rounded text-xs font-mono text-gray-300 border border-zinc-600">
                    {shortcut.key}
                  </kbd>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-zinc-700">
              <p className="text-xs text-gray-500">
                Shortcuts work when not typing in input fields
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default KeyboardShortcutsHelp;
