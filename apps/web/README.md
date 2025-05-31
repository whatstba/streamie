# Streamie Web App

A modern AI-powered DJ interface built with Next.js and React.

## ✨ New Features

### 🎵 Virtualized Track List
- **High Performance**: Uses [react-virtualized](https://github.com/bvaughn/react-virtualized) to efficiently render large music libraries
- **Auto-Analysis**: Automatically analyzes BPM when tracks are clicked - no separate button needed!
- **Smart Search**: Real-time search across track titles, artists, albums, and genres
- **Beautiful UI**: Modern design with album artwork, hover effects, and smooth animations

### 🔍 Enhanced Music Library
- Real-time track count display
- Visual feedback during analysis
- Improved artwork handling with fallbacks
- Responsive design that works on all screen sizes

## 🚀 Getting Started

1. **Start the Python backend**:
   ```bash
   cd ../python-worker
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

2. **Start the web app**:
   ```bash
   npm install
   npm run dev
   ```

3. **Add music**: Place your music files (MP3, M4A, WAV, FLAC, OGG) in `~/Downloads`

4. **Use the app**:
   - Browse your music library with the virtualized list
   - Search for tracks, artists, or albums
   - Click any track to select and automatically analyze its BPM
   - View track metadata and album artwork

## 🎛️ Features

- **Auto BPM Analysis**: Click any track to automatically get beat analysis
- **Virtualized Scrolling**: Smooth performance even with thousands of tracks
- **Search & Filter**: Find tracks instantly with real-time search
- **Album Artwork**: Automatic artwork display with fallbacks
- **Metadata Display**: Shows artist, album, genre, year, and duration
- **Visual Feedback**: Loading states and analysis progress indicators

## 🔧 Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Virtualization**: react-virtualized for high-performance lists
- **Icons**: Heroicons
- **Backend**: Python FastAPI with audio analysis capabilities

## 📱 UI Improvements

- Modern dark theme with purple accents
- Smooth hover effects and transitions
- Responsive layout that adapts to screen size
- Search functionality with clear/reset option
- Track count and filtered results display
- Visual analysis progress indicators

Visit http://localhost:3000 to see the app in action!

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
