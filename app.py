from flask import Flask, jsonify, render_template_string
import os

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "v1")

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AKS Canary — {{ version }}</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --v1-accent: #00e5ff;
    --v2-accent: #ff6b35;
    --accent: {{ '#00e5ff' if version == 'v1' else '#ff6b35' }};
    --bg: #050508;
    --surface: #0d0d14;
    --text: #e8e8f0;
    --muted: #5a5a72;
  }

  html, body {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    overflow: hidden;
  }

  /* animated grid background */
  .grid-bg {
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: gridDrift 20s linear infinite;
    pointer-events: none;
  }

  @keyframes gridDrift {
    0% { transform: translateY(0); }
    100% { transform: translateY(60px); }
  }

  /* vignette */
  .vignette {
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at center, transparent 40%, rgba(5,5,8,0.85) 100%);
    pointer-events: none;
    z-index: 1;
  }

  /* accent glow blob */
  .glow-blob {
    position: fixed;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, {{ 'rgba(0,229,255,0.07)' if version == 'v1' else 'rgba(255,107,53,0.07)' }} 0%, transparent 70%);
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 1;
    animation: blobPulse 4s ease-in-out infinite;
  }

  @keyframes blobPulse {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.7; }
    50% { transform: translate(-50%, -50%) scale(1.15); opacity: 1; }
  }

  /* main layout */
  .container {
    position: relative;
    z-index: 2;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 2rem;
  }

  /* top label */
  .top-label {
    font-size: 11px;
    letter-spacing: 0.3em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 2.5rem;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 0.2s;
  }

  /* version badge */
  .version-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1.5rem;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 0.4s;
  }

  .version-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent), 0 0 24px var(--accent);
    animation: dotPulse 2s ease-in-out infinite;
  }

  @keyframes dotPulse {
    0%, 100% { box-shadow: 0 0 8px var(--accent), 0 0 16px var(--accent); }
    50% { box-shadow: 0 0 16px var(--accent), 0 0 40px var(--accent), 0 0 60px var(--accent); }
  }

  .version-text {
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 400;
    color: var(--accent);
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  /* main heading */
  .heading {
    font-family: 'Syne', sans-serif;
    font-size: clamp(3rem, 8vw, 6.5rem);
    font-weight: 800;
    line-height: 0.95;
    text-align: center;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
    opacity: 0;
    animation: fadeUp 0.7s ease forwards 0.5s;
  }

  .heading .line-1 { color: var(--text); display: block; }
  .heading .line-2 {
    display: block;
    color: transparent;
    -webkit-text-stroke: 1px var(--accent);
    opacity: 0.6;
  }

  /* subtitle */
  .subtitle {
    font-size: 13px;
    color: var(--muted);
    letter-spacing: 0.05em;
    margin-bottom: 3rem;
    text-align: center;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 0.7s;
  }

  /* stats row */
  .stats {
    display: flex;
    gap: 2px;
    margin-bottom: 3rem;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 0.9s;
  }

  .stat {
    background: var(--surface);
    border: 1px solid rgba(255,255,255,0.05);
    padding: 1rem 1.5rem;
    min-width: 130px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }

  .stat:first-child { border-radius: 8px 0 0 8px; }
  .stat:last-child { border-radius: 0 8px 8px 0; }

  .stat::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
  }

  .stat:hover::before { opacity: 1; }

  .stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
    display: block;
    line-height: 1;
    margin-bottom: 6px;
  }

  .stat-label {
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
  }

  /* terminal block */
  .terminal {
    background: var(--surface);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    font-size: 12px;
    color: var(--muted);
    letter-spacing: 0.03em;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 1.1s;
    min-width: 340px;
    text-align: left;
  }

  .terminal .prompt { color: var(--accent); }
  .terminal .response { color: var(--text); margin-top: 4px; padding-left: 1rem; }

  /* bottom bar */
  .bottom-bar {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 2rem;
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
    z-index: 2;
    opacity: 0;
    animation: fadeUp 0.6s ease forwards 1.3s;
  }

  .bottom-bar span { display: flex; align-items: center; gap: 6px; }
  .bottom-bar .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--accent); }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* scanline overlay */
  .scanlines {
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.03) 2px,
      rgba(0,0,0,0.03) 4px
    );
    pointer-events: none;
    z-index: 3;
  }
</style>
</head>
<body>

<div class="grid-bg"></div>
<div class="glow-blob"></div>
<div class="vignette"></div>
<div class="scanlines"></div>

<div class="container">
  <div class="top-label">Azure Kubernetes Service &nbsp;·&nbsp; Canary Deployment</div>

  <div class="version-badge">
    <div class="version-dot"></div>
    <span class="version-text">{{ version }} — {{ 'stable' if version == 'v1' else 'canary' }}</span>
  </div>

  <h1 class="heading">
    <span class="line-1">Hello from</span>
    <span class="line-2">AKS Canary</span>
  </h1>

  <p class="subtitle">
    {{ '90% traffic · production stable' if version == 'v1' else '10% traffic · canary release' }}
  </p>

  <div class="stats">
    <div class="stat">
      <span class="stat-value">{{ '9' if version == 'v1' else '1' }}</span>
      <span class="stat-label">replicas</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ '90%' if version == 'v1' else '10%' }}</span>
      <span class="stat-label">traffic</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ version }}</span>
      <span class="stat-label">version</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ 'live' if version == 'v1' else 'canary' }}</span>
      <span class="stat-label">status</span>
    </div>
  </div>

  <div class="terminal">
    <span class="prompt">$ curl http://&lt;EXTERNAL_IP&gt;/</span>
    <div class="response">{"message": "Hello from AKS Canary", "version": "{{ version }}"}</div>
  </div>
</div>

<div class="bottom-bar">
  <span><div class="dot"></div> AKS Central India</span>
  <span><div class="dot"></div> Azure DevOps Pipeline</span>
  <span><div class="dot"></div> lakshyaacr.azurecr.io</span>
</div>

</body>
</html>"""


@app.route('/')
def home():
    return jsonify({
        "version": VERSION,
        "message": "Hello from AKS Canary"
    })


@app.route('/ui')
def ui():
    return render_template_string(HTML, version=VERSION)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)