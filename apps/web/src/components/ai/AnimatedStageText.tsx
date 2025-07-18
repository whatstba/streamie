'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AnimatedStageTextProps {
  text: string;
  className?: string;
}

export default function AnimatedStageText({ text, className = '' }: AnimatedStageTextProps) {
  // Split text into words for individual animation
  const words = text.split(' ');
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={text}
        className={`flex flex-wrap justify-center gap-x-2 ${className}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {words.map((word, index) => (
          <motion.span
            key={`${word}-${index}`}
            className="inline-block"
            initial={{ 
              opacity: 0, 
              y: 20,
              filter: 'blur(10px)'
            }}
            animate={{ 
              opacity: 1, 
              y: 0,
              filter: 'blur(0px)'
            }}
            transition={{
              duration: 0.5,
              delay: index * 0.1,
              ease: [0.25, 0.1, 0.25, 1]
            }}
          >
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent font-semibold">
              {word}
            </span>
          </motion.span>
        ))}
      </motion.div>
    </AnimatePresence>
  );
}