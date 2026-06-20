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
- Mark tabs as "In Practice List" or remove them
- View dedicated "Practice List" collection
- Bulk operations on selected tabs
- Statistics dashboard showing:
  - Total tabs in collection
  - Practice list count
  - Genre breakdown
  - Rating distribution

### 🎵 Spotify Integration
- **Connect your Spotify account** with OAuth
- **Now Playing display** in the title bar with Spotify icon
- **One-click "Add" button** to instantly add current track to Practice List
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
   - Set rating and add to Practice List

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

## 🎨 Features Overview

### Main Tab Collection View
*The main interface showing your complete tab collection with Band, Album, Title, Tuning, Rating, and Genre columns. Dark theme with Ultimate Guitar and Spotify quick-access buttons.*

**What you see:**
- Full tab database with search and filter
- Inline star rating system (1-5 stars)
- Quick access buttons to Ultimate Guitar and Spotify
- Sort and organize tabs by artist and genre

### Now Playing Display (Spotify Integration)
*Spotify integration in the title bar showing the current track with green Spotify icon.*

**Features:**
- Shows currently playing song from Spotify in real-time
- Clickable link to search the track on Ultimate Guitar
- **"+ Add"** button to instantly add track to Practice List
- Auto-updates every 5 seconds when music is playing

### Statistics Dashboard  
*Visual analytics showing your learning progress at a glance.*

**Shows:**
- Total tabs and learning statistics
- Rating distribution chart
- Top bands by tab count
- Genre breakdown
- Completion percentage

### Practice List
*Dedicated view for tracks you're learning or want to learn.*

**Features:**
- All your practice tracks with learning dates
- Ratings and genre classification
- Track your progress and learning journey
- Add tracks via one-click or context menu

### Pitch Calculator Tool
*Built-in tool to adjust song tunings to your preference.*

**Features:**
- Select guitar type (6-string or 7-string)
- Choose target tuning
- Get detailed pitch shift information per string
- Add tunings to your collection

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
├── settings.json           # User settings & Spotify tokens
└── docs/screenshots/       # Screenshot assets
```

---

## 📝 Recent Updates

### v0.47 - Practice List & Spotify One-Click (Latest)
- ✅ Renamed "Learned" to "Practice List"
- ✅ Added one-click "+ Add" button for Spotify tracks
- ✅ Improved UI terminology

### v0.46 - Spotify Now Playing Display
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
- Use the **"+ Add"** button to quickly build your Practice List

---

**Made with ❤️ for guitarists everywhere** 🎸
