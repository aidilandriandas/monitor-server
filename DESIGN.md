# Design Direction: Sentinel NOC

## Identity & Personality
- **Product**: Sentinel NOC (Network Operations Center & Homelab Infrastructure Sentinel)
- **Audience**: Systems engineers, devops, homelab administrators running Linux, Docker, and Proxmox VE clusters.
- **Personality**: Grounded, utilitarian, high-density, authoritative, fast. No decorative filler or cartoon elements.

## Design Dials
- **Energy**: 2 (Controlled, functional precision with clear hierarchy)
- **Rhythm**: 2 (Structured grid with contextual card and tabular density)
- **Motion**: 1 (Purposeful transitions on state changes only, no ambient distracting animations)

## Style Direction: Datacenter NOC (Cinematic Wallpaper + Solid High-Contrast Cards)
- **Style Concept**: High-precision Network Operations Center with an atmospheric enterprise datacenter wallpaper background and crisp, solid obsidian cards.
- **Surface Layering**:
  - Background: Cinematic enterprise datacenter server room wallpaper (`/static/datacenter_bg.jpg`) with a deep moody dark overlay `linear-gradient(to bottom, rgba(6, 9, 19, 0.78) 0%, rgba(6, 9, 19, 0.88) 35%, rgba(6, 9, 19, 0.94) 100%)`.
  - Cards: Solid, razor-sharp obsidian panels `#0d1322` with `1px solid rgba(255, 255, 255, 0.08)` and subtle top bevel highlight `inset 0 1px 0 0 rgba(255, 255, 255, 0.06)`. No murky blur.
  - Inset Wells: Deep `#080c16` for tables and metric groups with `1px solid rgba(255, 255, 255, 0.05)`.
  - Interactive Lift: Smooth 200ms cubic-bezier transition with subtle cyan accent border on hover (`border-color: rgba(56, 189, 248, 0.4)`).
- **Text & Contrast**:
  - Strict WCAG AAA/AA contrast (minimum 7:1 for headings, 4.5:1 for body).
  - Primary text: Crisp white `#ffffff` / `#f8fafc`.
  - Secondary: Slate-300 `#cbd5e1` and Slate-400 `#94a3b8`.
  - Monospace telemetry: JetBrains Mono for exact character alignment and zero drift.

## Functional Rules
- Every metric must reflect real backend data; no placeholder or synthetic graphs.
- Every button must execute a real API action or provide concrete utility.
- All interactive consoles and tables must feature empty, loading, and error states.
