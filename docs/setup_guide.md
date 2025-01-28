# EcoNest Security Camera Setup & Usage Guide

This guide provides **step-by-step** instructions to help you **install, configure, and run** the EcoNest Security Camera system on your **Raspberry Pi 4** using a **USB camera**. The system offers:

- **Live Streaming** over a local or public IP.  
- **Password Protection** via HTTP Basic Authentication.  
- **Video Recording** in 30-minute chunks.  
- **Anomaly Detection** to capture photos upon unusual activity.  
- **Automated Cleanup** of old video and anomaly files.

---

## Table of Contents

1. [Prerequisites](#prerequisites)  
2. [Hardware Setup](#hardware-setup)  
3. [Software Installation](#software-installation)  
4. [Configuration](#configuration)  
5. [Running the Security Camera](#running-the-security-camera)  
6. [Accessing the Live Stream](#accessing-the-live-stream)  
7. [Viewing Recorded Videos and Anomalies](#viewing-recorded-videos-and-anomalies)  
8. [Automating the Security Camera on Boot](#automating-the-security-camera-on-boot)  
9. [Troubleshooting](#troubleshooting)  
10. [Additional Notes](#additional-notes)

---

## 1. Prerequisites

### Hardware

- **Raspberry Pi 4** with Raspberry Pi OS installed.  
- **USB Camera**: Properly connected and recognized by the Raspberry Pi.  
- **Power Supply** suitable for Raspberry Pi 4.  
- **MicroSD Card** (≥ 16GB recommended).  
- **Internet Connection** (Ethernet or Wi-Fi).

### Software

- **Python 3.x** (pre-installed on Raspberry Pi OS).  
- **Git** to clone the repository (optional if you download as a ZIP).  
- **OpenCV, Flask, Flask-HTTPAuth, Werkzeug, and NumPy** (installed via `pip`).

---

## 2. Hardware Setup

1. **Connect the USB Camera**  
   - Plug your USB camera into one of the Raspberry Pi's USB ports.  
   - Verify detection with `lsusb`. You should see an entry for your camera.

2. **Position the Camera**  
   - Ensure it has a stable, unobstructed view.  
   - Provide proper lighting for best results with anomaly detection.

---

## 3. Software Installation

1. **Update the System**  
   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y