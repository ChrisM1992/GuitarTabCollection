# 🎸 GuitarTabCollection

> A powerful desktop application to organize, manage, and learn guitar tabs with Spotify integration.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎵 Overview

**GuitarTabCollection** is a feature-rich desktop application designed for guitarists who want to organize their tab collection, track learning progress, and discover new songs through Spotify integration. Whether you're a beginner or an experienced musician, this app helps you manage your guitar journey.

### Why GuitarTabCollection?
- 📊 **Organize tabs** by band, album, title, tuning, and genre
- ⭐ **Track progress** with ratings and learned/unlearned status  
- 🎵 **Spotify integration** — see what you're playing and find tabs instantly
- 📈 **Statistics dashboard** — visualize your learning progress
- 🎛️ **Pitch shifter** — adjust song pitch to your preference
- 💾 **Data backup & export** — export as CSV or backup your database
- 🔍 **Advanced filtering** — find exactly what you need
- 🎹 **Ultimate Guitar integration** — search directly from the app

---

## ✨ Key Features

### 📚 Tab Management
- Add tabs manually or in bulk
- Organize by **Band**, **Album**, **Title**, **Tuning**, **Genre**, and **Notes**
- Search and filter with advanced criteria
- Inline star rating system (1-5 stars)
- Edit tabs directly in the interface
- Notes field with date picker support

### 🎓 Learning Tracking
- Mark tabs as "Learned" or "Unlearned"
- View dedicated "Learned" tab collection
- Bulk operations on selected tabs
- Statistics dashboard showing:
  - Total tabs in collection
  - Learned vs. unlearned count
  - Genre breakdown
  - Rating distribution

### 🎵 Spotify Integration
- **Connect your Spotify account** with OAuth
- **Now Playing display** in the title bar with Spotify icon
- **One-click search** on Ultimate Guitar for current song
- Automatically resume where you left off
- Green, clickable now playing label

### 🎛️ Tools & Utilities
- **Pitch Shifter** — adjust song pitch (+/- semitones)
- **CSV Export** — export current view data
- **Database Backup** — backup your tabs collection
- **Print & HTML export** — styled HTML printable tabs

### ⌨️ Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Quick filter search |
| `F2` | Edit selected cell |
| `Delete` | Delete selected tab |
| `Ctrl+N` | Add new tab |
| `Ctrl+B` | Backup database |

---

## 🚀 Getting Started

### Requirements
- Python 3.11 or higher
- Windows / macOS / Linux

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ChrisM1992/GuitarTabCollection.git
   cd GuitarTabCollection
   ```

2. **Install dependencies**
   ```bash
   pip install PyQt5 -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

### First Time Setup

1. **Launch the app** — a local SQLite database is created automatically
2. **Connect Spotify** (optional)
   - Click the Spotify button in the top menu
   - Authorize via your browser
   - Your connection is saved automatically
3. **Start adding tabs**
   - Click "+" button or use `Ctrl+N`
   - Fill in Band, Album, Title, Tuning, Genre, Notes
   - Set rating and learning status

---

## 🔐 Spotify Integration Setup

To use Spotify features, you need to register a Spotify Developer application:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Accept the terms and create the app
4. Copy your **Client ID** and **Client Secret**
5. In the app settings, paste these credentials
6. Click "Connect to Spotify"
7. Authorize in your browser — done! ✓

**Note:** Your refresh token is saved locally. Spotify connection resumes automatically.

---

## 📊 Screenshots

### Main Tab Collection View
All your tabs organized in a beautiful dark theme with star ratings, tuning info, and one-click links to Ultimate Guitar or Spotify.

### Now Playing Display
```
GuitarTabs     🟢 Currently Playing: Artist – Song Title     ─ □ ✕
```
Click to search for that song on Ultimate Guitar!

### Statistics Dashboard
Visual breakdown of your collection:
- Total tabs learned/unlearned
- Genre distribution
- Rating breakdown chart

---

## 🛠️ Technical Details

### Architecture
- **GUI Framework:** PyQt5
- **Database:** SQLite
- **Spotify API:** OAuth 2.0 flow with refresh token
- **Threading:** Background polling for "Now Playing" updates
- **Export:** CSV format with full tab metadata

### Project Structure
```
GuitarTabCollection/
├── main.py                 # Entry point
├── guitar_tabs_app.py      # Main application UI
├── database_manager.py     # SQLite operations
├── spotify_client.py       # Spotify OAuth & polling
├── tabs_data_model.py      # Data model & filtering
├── title_checker.py        # Title validation
├── add_tab_dialog.py       # Tab entry dialog
├── add_tab_multi.py        # Bulk add dialog
├── pitch_shifter.py        # Pitch adjustment tool
├── stats_dashboard.py      # Statistics visualization
├── guitar_tabs.db          # SQLite database (auto-created)
└── settings.json           # User settings & Spotify tokens
```

---

## 📝 Recent Updates

### v0.46 - Spotify Now Playing Display (Latest)
- ✅ Fixed Spotify "Now Playing" display in title bar
- ✅ Added ClickableLabel for proper mouse event handling
- ✅ Implemented Spotify icon in now playing section
- ✅ Fixed polling to start immediately after authentication
- ✅ Improved layout with bold "Currently Playing:" label

### v0.45 - Statistics Dashboard
- Added interactive statistics dashboard
- Visual charts for collection analysis

### v0.44 - UI Modernization
- Modern dark theme
- Improved responsiveness
- Code cleanup and optimizations

---

## 🐛 Known Issues & TODO

- [ ] Dark mode toggle (currently dark theme only)
- [ ] Mobile companion app
- [ ] Cloud sync option
- [ ] YouTube tab preview integration
- [ ] Setlist creation & management

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

---

## 📧 Contact & Support

For issues, questions, or feature requests:
- Open an [Issue](https://github.com/ChrisM1992/GuitarTabCollection/issues)
- Check existing discussions

---

## 🎸 Tips & Tricks

### Pro Tips
- **Bulk rate songs:** Right-click a selection, choose "Set Rating"
- **Quick search:** Use `Ctrl+F` to instantly filter tabs
- **Pitch shifting:** Use the Pitch Shifter tool to adjust song keys
- **CSV export:** Export your collection for backup or sharing
- **Keyboard navigation:** `F2` to edit, `Delete` to remove

### Spotify Tips
- Keep your Spotify app running for accurate "Now Playing" updates
- Your Spotify token refresh automatically
- Click the green "Currently Playing" text to search on Ultimate Guitar

---

**Made with ❤️ for guitarists everywhere** 🎸

