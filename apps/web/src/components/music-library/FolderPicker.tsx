'use client';

import React, { useRef, useState } from 'react';
import { FolderIcon, FolderOpenIcon } from '@heroicons/react/24/outline';

// Extend HTMLInputElement to include webkitdirectory
declare module 'react' {
  interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
    webkitdirectory?: string;
    directory?: string;
  }
}

interface FolderPickerProps {
  onFolderSelect: (path: string) => void;
  disabled?: boolean;
  className?: string;
}

const FolderPicker: React.FC<FolderPickerProps> = ({
  onFolderSelect,
  disabled = false,
  className = '',
}) => {
  const [isHovering, setIsHovering] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      // Get the path from the first file (all files in the same directory)
      const firstFile = files[0];
      // Extract directory path by removing the filename
      const fullPath = (firstFile as any).webkitRelativePath || firstFile.name;
      const pathParts = fullPath.split('/');
      const folderPath = pathParts.length > 1 ? pathParts.slice(0, -1).join('/') : '';

      // For webkitdirectory, we get the folder name from webkitRelativePath
      if ((firstFile as any).webkitRelativePath) {
        const relativePath = (firstFile as any).webkitRelativePath;
        const rootFolder = relativePath.split('/')[0];
        onFolderSelect(rootFolder);
      } else {
        onFolderSelect(folderPath || firstFile.name);
      }
    }

    // Reset the input value to allow selecting the same folder again
    event.target.value = '';
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        style={{ display: 'none' }}
        onChange={handleFileSelect}
        disabled={disabled}
      />

      <button
        onClick={handleClick}
        disabled={disabled}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className={`
          flex items-center gap-3 p-4 rounded-xl border-2 border-dashed
          transition-all duration-200 min-h-[120px] w-full
          ${
            disabled
              ? 'border-gray-600 bg-gray-800/30 cursor-not-allowed opacity-50'
              : isHovering
                ? 'border-purple-400 bg-purple-900/20 text-purple-300'
                : 'border-gray-500 bg-gray-800/50 hover:bg-gray-800 text-gray-300'
          }
          ${className}
        `}
      >
        <div className="flex flex-col items-center text-center w-full">
          {isHovering && !disabled ? (
            <FolderOpenIcon className="h-12 w-12 mb-3" />
          ) : (
            <FolderIcon className="h-12 w-12 mb-3" />
          )}

          <div>
            <p className="font-medium mb-1">{disabled ? 'Processing...' : 'Select Music Folder'}</p>
            <p className="text-sm opacity-75">
              {disabled
                ? 'Please wait while we process your music'
                : 'Choose a folder containing your music files'}
            </p>
          </div>
        </div>
      </button>
    </>
  );
};

export default FolderPicker;
