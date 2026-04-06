# F1 Race Replay 🏎️ 🏁

A personal fork of [IAmTomShaw/f1-race-replay](https://github.com/IAmTomShaw/f1-race-replay).

**Maintained by:** Abhinav Singh  
**GitHub:** [github.com/abhinavsingh](https://github.com/abhinavsingh)

## About
An interactive Formula 1 race visualisation and data analysis tool built with Python.
Personalised and extended as part of my Python development journey.

## Features
- Race Replay Visualisation — watch driver positions unfold in real time on a rendered track
- Live Leaderboard — driver positions and tyre compounds updated each lap
- Driver Telemetry — speed, gear, DRS status for selected drivers
- Interactive Controls — pause, rewind, fast forward, adjust playback speed
- Qualifying Session Support — telemetry visualisation for qualifying replays
- Sprint Session Support — replay sprint races with full HUD

## Controls
| Key | Action |
|---|---|
| `SPACE` | Pause / Resume |
| `← →` | Rewind / Fast Forward |
| `↑ ↓` | Change playback speed |
| `1–4` | Set speed directly |
| `R` | Restart replay |
| `D` | Toggle DRS zones |
| `L` | Toggle driver names |
| `B` | Toggle progress bar |

## Requirements
- Python 3.11+
- FastF1
- Arcade
- numpy

## Setup
```bash