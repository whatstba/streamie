import React from 'react';
import Sidebar from '../navigation/Sidebar';
import Player from '../player/Player';

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="h-screen bg-black text-white flex flex-col">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      <Player />
    </div>
  );
};

export default MainLayout; 