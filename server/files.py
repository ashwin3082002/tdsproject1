from textwrap import dedent
from datetime import datetime

README_TMPL = """# {title}

{summary}

## Setup
Static site deployed via GitHub Pages (GitHub Actions).

## Usage
Open **{pages_url}**.

## Code
- Minimal Bootstrap 5 + vanilla JS.
- See `script.js` for task logic.

## License
MIT
"""

# GitHub Actions: deploy to Pages
PAGES_WORKFLOW_YML = """name: Deploy GitHub Pages
on:
  push:
    branches: [ main ]
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: "pages"
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: mkdir -p dist && cp -r * dist/ || true
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
"""
