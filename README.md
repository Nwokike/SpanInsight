<p align="center">
  <img src="src/assets/logo.png" alt="Spaninsight" width="320" />
</p>

<p align="center">
  A high-performance, privacy-first data intelligence platform for smart data collection, analysis and reporting
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android" />
  <img src="https://img.shields.io/badge/Built%20with-Flet%200.85-00B0FF?style=for-the-badge&logo=flutter&logoColor=white" alt="Built with Flet" />
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</p>

---

## Download

| Platform | Download | Notes |
|:--------:|:--------:|:------|
| 🤖 **Android** | [![Play Store](https://img.shields.io/badge/Google_Play-414141?style=flat-square&logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.spaninsight.app) | Recommended for most users |

### Android (APK direct download)

| Variant | Download | Notes |
|:--------|:--------:|:-----|
| 📱 **ARM64** (most phones) | [**spaninsight-arm64-v8a.apk**](https://github.com/Nwokike/spaninsight/releases/latest/download/spaninsight-arm64-v8a.apk) | Modern 64-bit devices |
| 📱 **ARMv7** (older phones) | [**spaninsight-armeabi-v7a.apk**](https://github.com/Nwokike/spaninsight/releases/latest/download/spaninsight-armeabi-v7a.apk) | 32-bit ARM devices |
| 💻 **x86_64** (emulators) | [**spaninsight-x86_64.apk**](https://github.com/Nwokike/spaninsight/releases/latest/download/spaninsight-x86_64.apk) | Chromebooks & emulators |

---

## Core Capabilities

| Capability | Description |
|:---|:---|
| **Collaborative Workspace** | Multi-collaborator workspaces grouped under secure 6-digit PIN keys. Sync analyses, reports, and survey forms in real-time. |
| **Recipe Re-execution** | Data residency is guaranteed. Raw datasets remain local to each collaborator. Shared analysis steps are processed as recipes that re-execute inside local sandboxes. |
| **Smart Surveys** | Natural language survey generation (Text/Voice) with real-time preview — great for student research and customer feedback. |
| **Expert Code Terminal** | Full VS Code-style terminal with expandable code editor. Write, edit, and execute Python directly — no AI required. All data intelligence stays under your control. |
| **Autopilot Engine** | Multi-pass analysis orchestration for comprehensive automated report generation. |
| **Professional Export** | Export reports as PDF and PowerPoint with secure cloud sharing via ephemeral links. |
| **Local Security** | Sandbox-restricted Python execution environment ensuring 100% data residency. |

---

## Screenshots

### Widescreen & Tablet Experience

<p align="center">
  <img src="screenshots/home_desktop_light.png" width="90%" alt="Workspace Home Screen" />
</p>
<p align="center"><em>Workspace Home Screen — seamlessly collaborate and organize project files</em></p>

<p align="center">
  <img src="screenshots/autopilot_desktop_dark.png" width="90%" alt="AI Autopilot Engine" />
</p>
<p align="center"><em>Autonomous AI Autopilot — multi-pass local analysis orchestration for report generation</em></p>

### Mobile Experience

<table>
  <tr>
    <td width="50%"><img src="screenshots/home_dark.png" width="100%" alt="Home Dashboard" /></td>
    <td width="50%"><img src="screenshots/watch_ads_to_add_more_credit_light.png" width="100%" alt="AdMob & Credits" /></td>
  </tr>
  <tr>
    <td align="center"><em>Home Dashboard — dark theme optimized for local secure workspace sync</em></td>
    <td align="center"><em>AdMob & Rewards — watch buffered interstitial ads to top-up daily free credits</em></td>
  </tr>
</table>

<table>
  <tr>
    <td width="33%"><img src="screenshots/form_tab_mobile_light_with_form_prompt.png" width="100%" alt="Smart Survey Builder" /></td>
    <td width="33%"><img src="screenshots/live_form(f.spaninsight.com)_mobile.png" width="100%" alt="Public Mobile Survey View" /></td>
    <td width="33%"><img src="screenshots/expanded_form_showing_5_live_responses_mobile_dark.png" width="100%" alt="Responses Dashboard" /></td>
  </tr>
  <tr>
    <td align="center"><em>Smart Survey Builder — generate forms from voice or text prompts</em></td>
    <td align="center"><em>Public Web Survey — responsive client interface for fast data collection</em></td>
    <td align="center"><em>Live Responses — track user feedback in real time with quick-actions</em></td>
  </tr>
</table>

<table>
  <tr>
    <td width="50%"><img src="screenshots/analyses_mobile_light_showing_block_with_chart_table_description.png" width="100%" alt="Interactive Data Analysis" /></td>
    <td width="50%"><img src="screenshots/live_report_mobile(report.spaninsight.com).png" width="100%" alt="Interactive Shared Reports" /></td>
  </tr>
  <tr>
    <td align="center"><em>Local Data Analysis — visual charts, tables, and sandboxed execution blocks</em></td>
    <td align="center"><em>Interactive Shared Reports — public-facing web insights hosted on report.spaninsight.com</em></td>
  </tr>
</table>

<table>
  <tr>
    <td width="50%"><img src="screenshots/save_to_pdf_preview_mobile.png" width="100%" alt="PDF Print Preview" /></td>
    <td width="50%"><img src="screenshots/shared_ppt_report_mobile.png" width="100%" alt="PowerPoint Export" /></td>
  </tr>
  <tr>
    <td align="center"><em>Export to PDF — native layout engine with print preview controls</em></td>
    <td align="center"><em>PowerPoint Slide Generator — export report structures into PPT format</em></td>
  </tr>
</table>

---

## Features

- **Privacy-First AI** — Analysis runs locally; only AI prompts touch the secure gateway, never your raw dataset files.
- **Dynamic Workspaces** — Create, join, and switch between separate project workspaces instantly via a top-right switcher drop-down.
- **Voice-to-Insight** — Use natural language voice commands to query your data or build survey forms.
- **Expert Code Mode** — Expandable VS Code-style terminal for direct Python execution. Write your own code, bypass AI entirely, and keep full control of your analysis.
- **Editable Code Blocks** — View, edit, and re-run the Python code behind every analysis result — both AI-suggested and hand-written.
- **Local Sandbox** — Built-in Python runtime (`pandas`, `matplotlib`) runs in a restricted environment.
- **Credit-Based System** — AI tasks use a transparent credit system with generous daily free allowances.
- **Responsive Widescreen & Mobile** — High-performance, optimized deployments across widescreen and Android layouts.
- **Resilient Mobile Sandbox** — Hardened client environment utilizing sandboxed directory access (`FLET_APP_STORAGE_DATA`/`TEMP`) for maximum permission security and zero PermissionError crashes.

---

## Architecture

| Layer | Technology | Purpose |
|:---|:---|:---|
| **Frontend** | Flet | Reactive UI with vibrant styling, dark mode, and smooth transitions |
| **Compute** | Local Python Runtime | Pandas-based data processing & Matplotlib rendering |
| **Secure Edge Gateway** | Secure Gateway (api.spaninsight.com) | Private multi-model AI orchestration with automatic failover |
| **Edge Metadata Store** | Secure Edge Database | Workspace configurations, collaborative forms, and response indices |
| **Ephemeral Cache Store** | Ephemeral Secure Storage | Fast-loading shared interactive reports (7-day lifecycle) |
| **Local Storage** | Platform Keychain | Encrypted client-side credentials & offline project states |

### Visual Flow

```mermaid
graph TB
    subgraph SPANINSIGHT_APP ["📱 SPANINSIGHT CLIENT (Local-First APP)"]
        UI["🎨 Flet Reactive UI (Home | Analysis | Forms | Reports | Settings)"]
        Runtime["⚙️ Local Python Runtime (Pandas, Matplotlib)"]
        UI --> Runtime
    end

    subgraph SECURE_EDGE_GATEWAY ["🔒 SECURE EDGE GATEWAY (api.spaninsight.com)"]
        Inference["🤖 Autonomous AI Inference Engine"]
        D1["💾 Secure Edge Database"]
        R2["📦 Ephemeral Storage Bucket"]
        Verify["🔑 Cryptographic Challenge Verification"]
    end

    Runtime ==>|HTTPS TLS 1.3| SECURE_EDGE_GATEWAY
```

---

## Credit System

| Action                  | Credits     |
| ----------------------- | ----------- |
| AI Suggestion           | 1           |
| Custom Prompt / Voice   | 3           |
| Autopilot (Full Report) | 15          |
| **Daily Allowance**     | **50 FREE** |
| Manual Code Execution   | **FREE** (no credits needed) |

---

## Privacy & Security

Spaninsight is designed with a **Privacy-First** philosophy.

1. **Local Execution**: Data processing (filtering, grouping, analysis) happens entirely on your device.
2. **Encryption**: All communication with the AI gateway is encrypted via TLS 1.3.
3. **Data Residency**: We do not store your uploaded CSV/Excel/JSON files. Insights are generated on the fly.
4. **Sandbox Isolation**: AI-generated code runs in a restricted Python environment with no file system or network access.

---

## Legal Disclaimer

Spaninsight is a data analysis tool. While it uses advanced AI to suggest insights, users are responsible for verifying the accuracy of automated reports before making business decisions. Spaninsight does not take responsibility for data loss resulting from local sandbox execution errors.
