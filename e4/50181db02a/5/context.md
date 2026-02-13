# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the dashboard-perf agent. Your task is to optimize dashboard rendering performance across 6 components.

## Task from TaskList: #4 — Frontend: Dashboard rendering performance

## Changes to make

### 4a. 3D Globe — `frontend/src/3d/scenes/GlobalNetwork.tsx`

1. Line 362: Change `dpr={[1, 2]}` to `dpr={[1, 1.5]}` — 44% fewer pixels on retina
2. Line 382: Change `<FloatingParticles count={2000} />` to `<FloatingParticles count={800} />`
3. L...

