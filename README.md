# Eco-nest-Security-Camera
curl -fsSL https://tailscale.com/install.sh | sh
EcoNest Security Camera is a Python-based security system designed for Raspberry Pi 4 using a USB camera. This system streams live video to a public IP, allows remote access with password protection, stores recordings locally for the last 12 hours in 30-minute chunks, and detects anomalies by capturing photos when unusual activity is detected.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Live Streaming:** Stream video feed accessible via a web browser.
- **Password Protection:** Secure access with HTTP Basic Authentication.
- **Local Recording:** Store video recordings in 30-minute chunks.
- **Storage Management:** Automatically maintain only the last 12 hours of recordings.
- **Anomaly Detection:** Detect unusual activity and capture photos as evidence.
- **Automated Cleanup:** Delete oldest videos and anomaly photos when exceeding storage limits.

## Prerequisites

### Hardware

- **Raspberry Pi 4:** Ensure it's properly set up with Raspberry Pi OS.
- **USB Camera:** Must be compatible and properly connected to the Raspberry Pi.

### Software

- **Raspberry Pi OS:** Installed and updated.
- **Python 3.x:** Ensure Python 3 is installed.
- **Internet Connection:** Required for streaming and remote access.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/EcoNest_Security_Camera.git
   cd EcoNest_Security_Camera
