# SQUISH_LAB

Robotic multi-image acquisition system for large-scale photoelastic granular experiments.

## Overview

Studying large granular systems with photoelasticimetry requires higher resolution than any single camera frame can provide. SQUISH_LAB solves this by mounting a high-resolution camera on a computer-controlled XY gantry that systematically tiles overlapping images across the entire experimental domain.

At each grid position the system captures **two images**: one without the polarizing analyzer filter (particle boundaries) and one with it (photoelastic stress fringe patterns). These pairs are later merged in FIJI and fed into [PeGS2](https://github.com/photoelasticity/PeGS2) for contact-force extraction and force-chain analysis.

This system was developed as part of a senior thesis investigating how force-chain structure and bulk mechanical response scale with granular system size.

## Hardware

| Component | Details |
|---|---|
| XY Gantry | Galil motion controller, gclib driver |
| Camera | 9504 × 6336 px with macro lens, ~268 mm FOV width |
| Microcontroller | ESP32-C3 Mini |
| Analyzer filter | Circular polarizer on 3D-printed servo arm |
| Shutter trigger | 4066 quad bilateral switch IC wired to camera's AF/RLS lines |
| 3D printed parts | `HotShoe.stl` (camera mount), `servo_arm.stl` (filter arm) |

### System diagram

```
┌─────────────────────────────────────────────┐
│                     PC                      │
│  gantry_workflowV2.py  (Tkinter GUI)        │
└────────────┬────────────────────┬───────────┘
             │ gclib (COM4)       │ pyserial (COM7)
             ▼                    ▼
    ┌─────────────────┐  ┌──────────────────────┐
    │ Galil Controller│  │    ESP32-C3 Mini      │
    └────────┬────────┘  │  servo_camera.ino     │
             │           └────┬──────────────────┘
             ▼                │
      ┌────────────┐    ┌─────┴─────────────────┐
      │  XY Gantry │    │ GPIO10: Servo          │
      │  + Camera  │    │ GPIO3:  AF (focus)     │
      └────────────┘    │ GPIO2:  RLS (shutter)  │
                        └───────────────────────┘
```

### 3D printed parts

- **`HotShoe.stl`** — attaches to the camera's hot shoe; provides a rigid mount point for the gantry arm
- **`servo_arm.stl`** — holds the servo motor and swings the analyzer filter in front of / away from the lens

## How it works

```
For each grid position (snake pattern):
  1. Gantry moves to (x, y)
  2. ESP32 triggers shutter  →  Image A (no filter)   — particle boundaries
  3. Servo swings filter in front of lens
  4. ESP32 triggers shutter  →  Image B (with filter)  — stress fringes
  5. Servo retracts filter
  6. Advance to next position

Post-processing (FIJI):
  Red channel of Image A  +  Green channel of Image B  →  Composite
  Composite → PeGS2 (particleDetect → contactDetect → diskSolve)
```

## Repo contents

| File | Description |
|---|---|
| `gantry_workflowV2.py` | Main GUI — gantry + camera + imaging sequence control |
| `servo_cameraV1.py` | Standalone CLI script for manual shutter + filter testing |
| `servo_camera/servo_camera.ino` | ESP32 firmware — handles SHUTTER / FILTER,ON / FILTER,OFF commands |
| `HotShoe.stl` | 3D model: camera hot shoe mount |
| `servo_arm.stl` | 3D model: servo filter arm |

## Setup

### Dependencies

```bash
pip install gclib pyserial
```

> `tkinter` is included in the Python standard library.  
> `gclib` also requires the [Galil software suite](https://www.galil.com/sw/pub/all/regusr/gclib/) installed on the host machine.

### Flash the ESP32

Open `servo_camera/servo_camera.ino` in the Arduino IDE with the **ESP32-C3** board package installed, then upload.

### Wiring (ESP32-C3)

| ESP32 pin | Connected to |
|---|---|
| GPIO10 | Servo signal wire |
| GPIO3 | Camera AF line (via 4066 IC) |
| GPIO2 | Camera RLS line (via 4066 IC) |
| GND | Camera GND, servo GND, 4066 GND |

> The 4066 quad bilateral switch replaces the mechanical connections of an external camera trigger. Pull-up resistors (10 kΩ) and decoupling capacitors (0.1 µF) prevent spurious triggers. A 500 ms software debounce enforces a minimum interval between shutter events.

### Run the GUI

```bash
python gantry_workflowV2.py
```

## GUI walkthrough

The GUI has four tabs:

**Gantry** — connect to the Galil controller, jog with arrow keys or on-screen buttons, zero the position, set the imaging start position. Press `Esc` for emergency stop.

**Imaging Setup** — enter the scan area (mm), overlap percentage, and camera FOV width. Click *Calculate Grid* to preview the grid dimensions and total image count. Click *Start Imaging Sequence* to run.

**Camera Control** — connect to the ESP32, manually fire the shutter with or without the filter, or move the filter independently for optical alignment.

**Safety Settings** — view and optionally override the encoder-unit travel limits. Gated behind a confirmation checkbox.

### Typical workflow

1. Connect gantry (Gantry tab → Connect)
2. Connect camera (Camera Control tab → Connect)
3. Jog to the desired start corner of the specimen
4. Click *Set as Start Position*
5. Enter scan area, overlap, and FOV in Imaging Setup
6. Click *Calculate Grid* — verify image count
7. Click *Start Imaging Sequence*

## Key parameters

| Parameter | Default | Notes |
|---|---|---|
| Encoder scale X | 2500 steps/mm | Gantry calibration |
| Encoder scale Y | 6250 steps/mm | Gantry calibration |
| Safety limit X | 1,660,768 steps (~664 mm) | |
| Safety limit Y | 3,084,965 steps (~493 mm) | |
| Camera resolution | 9504 × 6336 px | |
| FOV width | 268.29 mm | Adjust if lens changes |
| Default overlap | 20% | Configurable in GUI |
| Gantry serial | COM4 @ 19200 baud | Configurable in GUI |
| ESP32 serial | COM7 @ 115200 baud | Configurable in GUI |

## Related

- [PeGS2](https://github.com/photoelasticity/PeGS2) — photoelastic granular solver used for downstream force analysis
- [Thesis & Poster](https://drive.google.com/drive/folders/1sUnPxUD-HGdpFqXc2pegkpBfvlM7RySr?usp=sharing) — *Linking Bulk Response to Local Structure in Granular Material Using Photoelasticimetry*, Vir Goyal, 2025
