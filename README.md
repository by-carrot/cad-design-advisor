# CAD Design Advisor

Analyzes a physical part file and recommends how to assemble it without screws or adhesives. Detects flat mating surfaces geometrically, filters joining patterns against your production constraints, generates parametric 3D reference geometry for the top recommendation, and explains the tradeoffs in plain language.

![CAD Design Advisor screenshot](docs/screenshot.png)

## The problem

First-time product designers know what they want to make but not how to join it. "Use snap fits" is not actionable advice. The geometry, material, volume, and production method all constrain which patterns are even valid, and within the valid set the tradeoffs are non-obvious. Getting this wrong means a prototype that falls apart or a production design that cannot be injection molded.

CAD Design Advisor takes your actual part file plus four constraint inputs and tells you specifically what joining pattern to use, why, and what to model in Fusion 360.

## What it does

| Capability | Detail |
|---|---|
| Mesh analysis | Detects dominant flat planes using face normal clustering. Identifies top, bottom, and vertical mating surfaces by area and orientation. |
| Constraint filtering | Matches joining patterns against product type, production method, material, volume, and budget tier. All filtering is deterministic Python with no LLM involvement. |
| Pattern recommendations | Ranks compatible patterns and explains why each one fits or does not fit the specific constraint combination. |
| Snap geometry generation | Generates a parametric CadQuery model of the recommended snap feature at the detected mating surface location. Rendered in a Three.js 3D viewer. |
| Fusion 360 guidance | Provides actionable modeling steps for the top recommended pattern, specific to the material and production method selected. |

## Architecture and design decisions

### The LLM never touches geometry

All mesh analysis, plane detection, and surface identification runs in deterministic Python using trimesh and scipy. The LLM receives only the constraint inputs and a structured summary of compatible patterns. It classifies and interprets. It never measures, computes, or reasons about coordinates.

This is the same principle used throughout the codebase. Geometry is a deterministic problem. Language models are unreliable arithmetic engines. Mixing them produces errors that are hard to detect and hard to debug.

**Rejected alternative:** Sending the mesh to Claude Vision and asking it to identify mating surfaces in natural language. Rejected because the output is spatial descriptions that require a translation layer to convert into coordinates, that translation layer introduces failure modes at every step, and the result is less reliable than a five-line scipy clustering function.

### Structured JSON knowledge base over RAG

The joining pattern knowledge base is a single JSON file with six patterns sourced from Bayer, Fictiv, PennEngineering, and plasticstoday. RAG was rejected for the same reason it was rejected in CAD Auditor: the domain is compact and fully known. Every pattern, every geometry parameter, every material constraint fits in one file. RAG adds retrieval latency and retrieval errors with no benefit when the entire knowledge base fits comfortably in a single prompt.

**Source citations are embedded in the knowledge base entries** so parameter ranges are traceable to their original engineering references, not to training data.

### Plane detection by normal clustering, not RANSAC

Face normals are clustered against six canonical directions (±X, ±Y, ±Z) using dot product thresholds rather than Open3D's RANSAC plane detection. RANSAC is more robust for irregular or noisy geometry but slower and harder to reason about. For cosmetic casings, the dominant mating surfaces are almost always axis-aligned, making canonical clustering accurate enough and significantly faster.

**Limitation:** Non-axis-aligned mating surfaces (angled parting lines, chamfered rims) are not detected by the current implementation. This is a known gap and the next iteration will add RANSAC as a fallback for meshes where canonical clustering finds fewer than three planes.

### CadQuery for parametric snap generation, not mesh boolean operations

The generated snap geometry is a parametric CadQuery model placed at the detected mating surface centroid. It is not a boolean operation applied to the uploaded mesh. Boolean operations on arbitrary mesh geometry are fragile: they depend on mesh quality, face orientation consistency, and watertightness. Parametric generation is reliable regardless of input mesh quality.

**Consequence:** The generated STL is a reference model showing what the snap feature should look like and where it should be placed, not a modified version of the uploaded part. The user models the actual feature in Fusion 360 using the reference as a visual target. This is the correct scope for a tool at this stage.

### Synchronous FastAPI endpoints

All endpoints are synchronous. The geometry processing is CPU-bound and runs in milliseconds for typical cosmetic casing files. Async would add complexity with no latency benefit for the current load profile.

### Input validation at the API boundary

Product type, production method, material, and budget tier are validated against explicit allowlists before the filtering layer runs. The alternative is silent empty results when a user passes a typo, which is harder to debug than a clear error message listing valid options.

## Installation

```bash
conda create -n cad-advisor python=3.11
conda activate cad-advisor
conda install -c cadquery -c conda-forge cadquery
pip install fastapi uvicorn anthropic pytest trimesh scipy numpy open3d
```

## Running the server

```bash
conda activate cad-advisor
cd cad-design-advisor
uvicorn src.api.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

To enable real LLM interpretation, set your Anthropic API key before starting the server:

```bash
set ANTHROPIC_API_KEY=your_key_here
uvicorn src.api.main:app --reload
```

Without the key, the tool runs in mock mode and returns placeholder rationale text. All geometry processing, filtering, and snap generation work normally without the key.

## Running the tests

```bash
python -m pytest tests/ -v
```

Expected output: 22 passed. Tests cover constraint filtering (8 cases), mesh analysis (8 cases), and snap geometry generation (6 cases).

## Project structure

```
cad-design-advisor/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI endpoints
│   │   └── interpreter.py   # LLM interpretation layer
│   ├── filtering/
│   │   └── filter.py        # Deterministic constraint filtering
│   ├── geometry/
│   │   └── mesh_analyzer.py # Plane detection and mating surface identification
│   ├── knowledge_base/
│   │   └── patterns.json    # Joining pattern KB with sourced geometry parameters
│   └── modification/
│       └── snap_generator.py # CadQuery parametric snap generation
├── templates/
│   └── index.html           # Three.js frontend
├── tests/
│   ├── test_filter.py
│   ├── test_mesh_analyzer.py
│   └── test_snap_generator.py
├── uploads/                 # Uploaded STL files (gitignored)
├── outputs/                 # Generated snap geometry STL files (gitignored)
└── conftest.py
```

## Knowledge base sources

Geometry parameters in `patterns.json` are sourced from primary engineering references, not from LLM training data.

| Pattern | Primary source |
|---|---|
| Cantilever snap | Bayer MaterialScience LLC, Snap-fit joints for plastics: a design guide (2013) |
| Annular snap | Bayer MaterialScience LLC, Snap-fit joints for plastics: a design guide (2013) |
| Living hinge | Fictiv, Living Hinge Design guide (2025); Beall, Plastics Today (2002) |
| Press fit | Jiga.io, Press Fit Tolerances guide (2025); ScienceDirect interference fit overview |
| Bayonet lock | Seetronic, Bayonet Connector Guide (2025) |
| Threaded insert | PennEngineering, SI Threaded Inserts for Plastics datasheet (2022) |

## Current limitations

The snap generator currently implements cantilever and annular patterns only. Press fit, living hinge, bayonet, and threaded insert geometry generation are not yet implemented. Non-axis-aligned mating surface detection is not yet implemented. The tool is scoped to cosmetic casings as the primary product type; other product types are partially supported through the knowledge base but have not been validated.

## Status

- [x] Knowledge base with sourced geometry parameters
- [x] Constraint filtering layer with 8 passing tests
- [x] Mesh analysis and plane detection with 8 passing tests
- [x] CadQuery snap geometry generation with 6 passing tests
- [x] FastAPI backend with recommend, interpret, and analyze endpoints
- [x] Three.js frontend with 3D viewer and recommendation cards
- [x] Mock interpretation fallback when API key is absent
- [ ] RANSAC fallback for non-axis-aligned mating surfaces
- [ ] Snap generation for press fit, living hinge, bayonet, threaded insert
- [ ] Eval set with labeled STL files and expected pattern outputs
- [ ] Live demo link
