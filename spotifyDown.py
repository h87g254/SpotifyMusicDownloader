#!/usr/bin/env python3
"""
Spotify Playlist Downloader - Premium Edition v2

A beautiful, modern web interface with parallax effects, glassmorphism,
and stunning animations. Now with YouTube anti-bot detection!

Requirements:
    pip install flask spotipy yt-dlp

Usage:
    python spotify_premium_downloader.py
    Then open http://localhost:5000 in your browser
"""

import os
import re
import threading
import json
import time
import random
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, session
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global state
download_status = {
    "running": False,
    "current_track": "",
    "current_artist": "",
    "progress": 0,
    "total": 0,
    "completed": [],
    "failed": [],
    "log": [],
    "playlist_name": "",
    "playlist_image": "",
    "eta": ""
}

# ============== PREMIUM HTML TEMPLATE ==============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>Spotify Downloader Premium</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1DB954;
            --primary-dark: #1aa34a;
            --primary-glow: rgba(29, 185, 84, 0.4);
            --bg-dark: #0a0a0f;
            --bg-card: rgba(255, 255, 255, 0.03);
            --bg-card-hover: rgba(255, 255, 255, 0.06);
            --border: rgba(255, 255, 255, 0.08);
            --text: #ffffff;
            --text-muted: #888;
            --error: #ff4757;
            --success: #1DB954;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.2);
        }

        /* ===== PARALLAX BACKGROUND ===== */
        .parallax-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .gradient-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.5;
            animation: float 20s ease-in-out infinite;
        }

        .orb-1 {
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, #1DB954 0%, transparent 70%);
            top: -200px;
            right: -100px;
            animation-delay: 0s;
        }

        .orb-2 {
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, #6366f1 0%, transparent 70%);
            bottom: -150px;
            left: -100px;
            animation-delay: -5s;
        }

        .orb-3 {
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, #ec4899 0%, transparent 70%);
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            animation-delay: -10s;
            opacity: 0.3;
        }

        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(50px, -30px) scale(1.1); }
            50% { transform: translate(-30px, 50px) scale(0.95); }
            75% { transform: translate(-50px, -20px) scale(1.05); }
        }

        /* Floating particles */
        .particles {
            position: absolute;
            width: 100%;
            height: 100%;
        }

        .particle {
            position: absolute;
            width: 4px;
            height: 4px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            animation: rise 15s infinite;
        }

        @keyframes rise {
            0% {
                transform: translateY(100vh) scale(0);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100vh) scale(1);
                opacity: 0;
            }
        }

        /* Grid overlay */
        .grid-overlay {
            position: absolute;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
            background-size: 50px 50px;
            mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
        }

        /* ===== MAIN CONTENT ===== */
        .main-content {
            position: relative;
            z-index: 1;
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        /* ===== HEADER ===== */
        .header {
            text-align: center;
            margin-bottom: 60px;
            padding-top: 40px;
        }

        .logo {
            display: inline-flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }

        .logo-icon {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, var(--primary), #1ed760);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 10px 40px var(--primary-glow);
            animation: pulse-glow 3s ease-in-out infinite;
        }

        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 10px 40px var(--primary-glow); }
            50% { box-shadow: 0 10px 60px var(--primary-glow), 0 0 100px var(--primary-glow); }
        }

        .logo-text {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #888 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .tagline {
            font-size: 18px;
            color: var(--text-muted);
            font-weight: 300;
            letter-spacing: 0.5px;
        }

        .badge {
            display: inline-block;
            padding: 6px 14px;
            background: linear-gradient(135deg, var(--primary), #1ed760);
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 15px;
        }

        /* ===== GLASS CARD ===== */
        .glass-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        }

        .glass-card:hover {
            background: var(--bg-card-hover);
            border-color: rgba(255, 255, 255, 0.12);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 30px;
        }

        .card-icon {
            width: 48px;
            height: 48px;
            background: rgba(29, 185, 84, 0.1);
            border: 1px solid rgba(29, 185, 84, 0.2);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }

        .card-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 22px;
            font-weight: 600;
        }

        .card-subtitle {
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* ===== FORM ELEMENTS ===== */
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        @media (max-width: 600px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
        }

        .form-group {
            margin-bottom: 24px;
        }

        .form-group.full-width {
            grid-column: 1 / -1;
        }

        .form-label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .form-input {
            width: 100%;
            padding: 16px 20px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 15px;
            font-family: inherit;
            transition: all 0.3s ease;
        }

        .form-input::placeholder {
            color: rgba(255, 255, 255, 0.3);
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.1);
            background: rgba(0, 0, 0, 0.4);
        }

        .form-hint {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 8px;
        }

        .form-hint a {
            color: var(--primary);
            text-decoration: none;
        }

        .form-hint a:hover {
            text-decoration: underline;
        }
        
        .form-select {
            width: 100%;
            padding: 16px 20px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 15px;
            font-family: inherit;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .form-select option {
            background: #1a1a2e;
            color: #fff;
        }

        /* ===== BUTTON ===== */
        .btn-primary {
            width: 100%;
            padding: 18px 32px;
            background: linear-gradient(135deg, var(--primary), #1ed760);
            border: none;
            border-radius: 14px;
            color: #000;
            font-size: 16px;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-primary::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }

        .btn-primary:hover:not(:disabled)::before {
            left: 100%;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px var(--primary-glow);
        }

        .btn-primary:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-icon {
            font-size: 20px;
        }

        /* Loading spinner */
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(0,0,0,0.2);
            border-top-color: #000;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* ===== PROGRESS SECTION ===== */
        .progress-section {
            display: none;
        }

        .progress-section.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Playlist Info */
        .playlist-info {
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 20px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            margin-bottom: 30px;
        }

        .playlist-cover {
            width: 80px;
            height: 80px;
            border-radius: 12px;
            background: linear-gradient(135deg, #333, #222);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            overflow: hidden;
        }

        .playlist-cover img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .playlist-details h3 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }

        .playlist-details p {
            font-size: 14px;
            color: var(--text-muted);
        }

        /* Progress Bar */
        .progress-container {
            margin: 30px 0;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .progress-label {
            font-size: 14px;
            color: var(--text-muted);
        }

        .progress-percentage {
            font-size: 14px;
            font-weight: 600;
            color: var(--primary);
        }

        .progress-bar-track {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), #1ed760);
            border-radius: 4px;
            width: 0%;
            transition: width 0.3s ease;
            position: relative;
        }

        .progress-bar-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        /* Current Track */
        .current-track {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 20px;
            background: rgba(29, 185, 84, 0.05);
            border: 1px solid rgba(29, 185, 84, 0.1);
            border-radius: 14px;
            margin-bottom: 25px;
        }

        .track-visualizer {
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 30px;
        }

        .visualizer-bar {
            width: 4px;
            background: var(--primary);
            border-radius: 2px;
            animation: visualize 0.5s ease-in-out infinite alternate;
        }

        .visualizer-bar:nth-child(1) { height: 30%; animation-delay: 0s; }
        .visualizer-bar:nth-child(2) { height: 60%; animation-delay: 0.1s; }
        .visualizer-bar:nth-child(3) { height: 100%; animation-delay: 0.2s; }
        .visualizer-bar:nth-child(4) { height: 40%; animation-delay: 0.3s; }

        @keyframes visualize {
            to { height: 100%; }
        }

        .track-info {
            flex: 1;
            min-width: 0;
        }

        .track-name {
            font-weight: 600;
            font-size: 15px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .track-artist {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* Log Container */
        .log-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 14px;
            padding: 20px;
            max-height: 250px;
            overflow-y: auto;
        }

        .log-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }

        .log-header span {
            font-size: 14px;
            font-weight: 500;
        }

        .log-entries {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 12px;
        }

        .log-entry {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .log-icon {
            flex-shrink: 0;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
        }

        .log-entry.success .log-icon {
            background: rgba(29, 185, 84, 0.2);
            color: var(--success);
        }

        .log-entry.error .log-icon {
            background: rgba(255, 71, 87, 0.2);
            color: var(--error);
        }

        .log-entry.info .log-icon {
            background: rgba(99, 102, 241, 0.2);
            color: #6366f1;
        }

        .log-message {
            flex: 1;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.4;
        }

        /* Results */
        .results-section {
            display: none;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid var(--border);
        }

        .results-section.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }

        .results-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }

        .result-stat {
            text-align: center;
            padding: 25px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 16px;
        }

        .stat-value {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 42px;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .stat-value.success { color: var(--success); }
        .stat-value.failed { color: var(--error); }
        .stat-value.total { color: #6366f1; }

        .stat-label {
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* ===== FEATURES SECTION ===== */
        .features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 60px;
        }

        @media (max-width: 700px) {
            .features {
                grid-template-columns: 1fr;
            }
            .results-grid {
                grid-template-columns: 1fr;
            }
        }

        .feature {
            text-align: center;
            padding: 30px 20px;
        }

        .feature-icon {
            width: 50px;
            height: 50px;
            margin: 0 auto 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }

        .feature-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .feature-desc {
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* ===== FOOTER ===== */
        .footer {
            text-align: center;
            padding: 40px 20px;
            margin-top: 60px;
            color: var(--text-muted);
            font-size: 13px;
        }

        .footer a {
            color: var(--primary);
            text-decoration: none;
        }

        /* ===== TOAST NOTIFICATIONS ===== */
        .toast-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .toast {
            padding: 16px 24px;
            background: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: toastIn 0.3s ease;
            max-width: 350px;
        }

        .toast.success { border-left: 3px solid var(--success); }
        .toast.error { border-left: 3px solid var(--error); }

        @keyframes toastIn {
            from { opacity: 0; transform: translateX(100px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .toast-icon {
            font-size: 20px;
        }

        .toast-message {
            font-size: 14px;
        }
    </style>
</head>
<body>
    <!-- Parallax Background -->
    <div class="parallax-container">
        <div class="gradient-orb orb-1"></div>
        <div class="gradient-orb orb-2"></div>
        <div class="gradient-orb orb-3"></div>
        <div class="grid-overlay"></div>
        <div class="particles" id="particles"></div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="container">
            <!-- Header -->
            <header class="header">
                <div class="logo">
                    <div class="logo-icon">🎵</div>
                    <span class="logo-text">SpotiDown</span>
                </div>
                <p class="tagline">Transform your Spotify playlists into offline MP3 collections</p>
                <span class="badge">Premium Edition v2</span>
            </header>

            <!-- Configuration Card -->
            <div class="glass-card" id="config-card">
                <div class="card-header">
                    <div class="card-icon">🔐</div>
                    <div>
                        <div class="card-title">Connect to Spotify</div>
                        <div class="card-subtitle">Enter your API credentials to get started</div>
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Client ID</label>
                        <input type="text" class="form-input" id="client_id" placeholder="Enter your Client ID">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Client Secret</label>
                        <input type="password" class="form-input" id="client_secret" placeholder="Enter your Client Secret">
                    </div>
                </div>
                <p class="form-hint" style="margin-top: -10px; margin-bottom: 20px;">
                    Get your credentials from <a href="https://developer.spotify.com/dashboard" target="_blank">Spotify Developer Dashboard</a>
                </p>

                <div class="form-group">
                    <label class="form-label">Playlist URL</label>
                    <input type="text" class="form-input" id="playlist_url" placeholder="https://open.spotify.com/playlist/...">
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Output Directory</label>
                        <input type="text" class="form-input" id="output_dir" value="downloads" placeholder="C:\\Users\\YourName\\Music">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Browser for Cookies</label>
                        <select class="form-select" id="browser_choice">
                            <option value="chrome">Chrome</option>
                            <option value="edge">Edge</option>
                            <option value="firefox">Firefox</option>
                            <option value="opera">Opera</option>
                            <option value="brave">Brave</option>
                            <option value="none">None (may fail)</option>
                        </select>
                    </div>
                </div>
                <p class="form-hint">Cookies help bypass YouTube restrictions. Make sure the browser is closed.</p>

                <button class="btn-primary" id="download-btn" onclick="startDownload()">
                    <span class="btn-icon">⬇️</span>
                    <span id="btn-text">Start Download</span>
                </button>
            </div>

            <!-- Progress Card -->
            <div class="glass-card progress-section" id="progress-section">
                <div class="card-header">
                    <div class="card-icon">📥</div>
                    <div>
                        <div class="card-title">Downloading</div>
                        <div class="card-subtitle" id="playlist-name-display">Fetching playlist...</div>
                    </div>
                </div>

                <!-- Playlist Info -->
                <div class="playlist-info" id="playlist-info" style="display: none;">
                    <div class="playlist-cover" id="playlist-cover">🎵</div>
                    <div class="playlist-details">
                        <h3 id="playlist-title">Loading...</h3>
                        <p id="playlist-track-count">0 tracks</p>
                    </div>
                </div>

                <!-- Current Track -->
                <div class="current-track" id="current-track-section">
                    <div class="track-visualizer">
                        <div class="visualizer-bar"></div>
                        <div class="visualizer-bar"></div>
                        <div class="visualizer-bar"></div>
                        <div class="visualizer-bar"></div>
                    </div>
                    <div class="track-info">
                        <div class="track-name" id="current-track-name">Preparing...</div>
                        <div class="track-artist" id="current-track-artist"></div>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div class="progress-container">
                    <div class="progress-header">
                        <span class="progress-label" id="progress-label">0 of 0 tracks</span>
                        <span class="progress-percentage" id="progress-percentage">0%</span>
                    </div>
                    <div class="progress-bar-track">
                        <div class="progress-bar-fill" id="progress-bar"></div>
                    </div>
                </div>

                <!-- Log -->
                <div class="log-container">
                    <div class="log-header">
                        <span>📋</span>
                        <span>Activity Log</span>
                    </div>
                    <div class="log-entries" id="log-entries"></div>
                </div>

                <!-- Results -->
                <div class="results-section" id="results-section">
                    <div class="results-grid">
                        <div class="result-stat">
                            <div class="stat-value total" id="total-count">0</div>
                            <div class="stat-label">Total Tracks</div>
                        </div>
                        <div class="result-stat">
                            <div class="stat-value success" id="success-count">0</div>
                            <div class="stat-label">Downloaded</div>
                        </div>
                        <div class="result-stat">
                            <div class="stat-value failed" id="failed-count">0</div>
                            <div class="stat-label">Failed</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Features -->
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <div class="feature-title">Smart Download</div>
                    <div class="feature-desc">Auto-retries with multiple methods</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🎧</div>
                    <div class="feature-title">High Quality</div>
                    <div class="feature-desc">192kbps MP3 audio files</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔒</div>
                    <div class="feature-title">Private & Secure</div>
                    <div class="feature-desc">Everything runs locally on your machine</div>
                </div>
            </div>

            <!-- Footer -->
            <footer class="footer">
                <p>Built with ❤️ using Flask, Spotipy & yt-dlp</p>
            </footer>
        </div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toast-container"></div>

    <script>
        // Create floating particles
        function createParticles() {
            const container = document.getElementById('particles');
            const particleCount = 50;
            
            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
                particle.style.animationDelay = Math.random() * 15 + 's';
                particle.style.opacity = Math.random() * 0.5 + 0.1;
                container.appendChild(particle);
            }
        }
        createParticles();

        // Parallax effect on mouse move
        document.addEventListener('mousemove', (e) => {
            const orbs = document.querySelectorAll('.gradient-orb');
            const x = e.clientX / window.innerWidth;
            const y = e.clientY / window.innerHeight;
            
            orbs.forEach((orb, index) => {
                const speed = (index + 1) * 20;
                const xOffset = (x - 0.5) * speed;
                const yOffset = (y - 0.5) * speed;
                orb.style.transform = `translate(${xOffset}px, ${yOffset}px)`;
            });
        });

        // Toast notification
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
                <span class="toast-message">${message}</span>
            `;
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'toastIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        let pollInterval = null;

        async function startDownload() {
            const clientId = document.getElementById('client_id').value.trim();
            const clientSecret = document.getElementById('client_secret').value.trim();
            const playlistUrl = document.getElementById('playlist_url').value.trim();
            const outputDir = document.getElementById('output_dir').value.trim();
            const browserChoice = document.getElementById('browser_choice').value;

            if (!clientId || !clientSecret || !playlistUrl) {
                showToast('Please fill in all required fields', 'error');
                return;
            }

            // Update UI
            const btn = document.getElementById('download-btn');
            const btnText = document.getElementById('btn-text');
            btn.disabled = true;
            btnText.innerHTML = '<div class="spinner"></div> Starting...';
            
            document.getElementById('progress-section').classList.add('active');
            document.getElementById('log-entries').innerHTML = '';
            document.getElementById('results-section').classList.remove('active');
            document.getElementById('playlist-info').style.display = 'none';

            try {
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                    },
                    body: JSON.stringify({
                        client_id: clientId,
                        client_secret: clientSecret,
                        playlist_url: playlistUrl,
                        output_dir: outputDir,
                        browser: browserChoice
                    })
                });

                const data = await response.json();

                if (data.error) {
                    showToast(data.error, 'error');
                    addLog(data.error, 'error');
                    resetButton();
                    return;
                }

                btnText.textContent = 'Downloading...';
                pollInterval = setInterval(pollStatus, 500);

            } catch (error) {
                showToast('Failed to start download', 'error');
                resetButton();
            }
        }

        async function pollStatus() {
            try {
                const response = await fetch('/status');
                const status = await response.json();

                // Update progress
                const percent = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
                document.getElementById('progress-bar').style.width = percent + '%';
                document.getElementById('progress-percentage').textContent = percent + '%';
                document.getElementById('progress-label').textContent = `${status.progress} of ${status.total} tracks`;

                // Update current track
                if (status.current_track) {
                    document.getElementById('current-track-name').textContent = status.current_track;
                    document.getElementById('current-track-artist').textContent = status.current_artist || '';
                }

                // Update playlist info
                if (status.playlist_name && document.getElementById('playlist-info').style.display === 'none') {
                    document.getElementById('playlist-info').style.display = 'flex';
                    document.getElementById('playlist-title').textContent = status.playlist_name;
                    document.getElementById('playlist-track-count').textContent = status.total + ' tracks';
                    document.getElementById('playlist-name-display').textContent = status.playlist_name;
                    
                    if (status.playlist_image) {
                        document.getElementById('playlist-cover').innerHTML = 
                            `<img src="${status.playlist_image}" alt="Cover">`;
                    }
                }

                // Add log entries
                status.log.forEach(entry => addLog(entry.message, entry.type));

                // Check if finished
                if (!status.running && status.progress > 0) {
                    clearInterval(pollInterval);
                    document.getElementById('results-section').classList.add('active');
                    document.getElementById('total-count').textContent = status.total;
                    document.getElementById('success-count').textContent = status.completed.length;
                    document.getElementById('failed-count').textContent = status.failed.length;
                    
                    document.getElementById('current-track-name').textContent = 'Complete!';
                    document.getElementById('current-track-artist').textContent = '';
                    
                    showToast(`Downloaded ${status.completed.length} of ${status.total} tracks!`, 'success');
                    resetButton();
                }

            } catch (error) {
                console.error('Poll error:', error);
            }
        }

        function addLog(message, type = 'info') {
            const container = document.getElementById('log-entries');
            const icons = { success: '✓', error: '✗', info: 'ℹ' };
            
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            const iconDiv = document.createElement('div');
            iconDiv.className = 'log-icon';
            iconDiv.textContent = icons[type];
            entry.appendChild(iconDiv);

            const msgDiv = document.createElement('div');
            msgDiv.className = 'log-message';
            msgDiv.textContent = message;
            entry.appendChild(msgDiv);
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }

        function resetButton() {
            const btn = document.getElementById('download-btn');
            const btnText = document.getElementById('btn-text');
            btn.disabled = false;
            btnText.innerHTML = '<span class="btn-icon">⬇️</span> Start Download';
        }

        // Save credentials to localStorage
        document.getElementById('client_id').addEventListener('change', saveCredentials);
        document.getElementById('client_secret').addEventListener('change', saveCredentials);
        
        function saveCredentials() {
            localStorage.setItem('spotify_client_id', document.getElementById('client_id').value);
            localStorage.setItem('spotify_client_secret', document.getElementById('client_secret').value);
        }

        // Load saved credentials
        window.addEventListener('load', () => {
            const savedId = localStorage.getItem('spotify_client_id');
            const savedSecret = localStorage.getItem('spotify_client_secret');
            if (savedId) document.getElementById('client_id').value = savedId;
            if (savedSecret) document.getElementById('client_secret').value = savedSecret;
        });
    </script>
</body>
</html>
"""


# ============== HELPER FUNCTIONS ==============

def extract_playlist_id(playlist_url: str) -> str:
    patterns = [
        r"spotify\.com/playlist/([a-zA-Z0-9]+)",
        r"spotify:playlist:([a-zA-Z0-9]+)",
        r"^([a-zA-Z0-9]{22})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, playlist_url)
        if match:
            return match.group(1)
    raise ValueError(f"Invalid playlist URL: {playlist_url}")


def sanitize_filename(name: str) -> str:
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name.strip()


def add_log(message: str, log_type: str = "info"):
    download_status["log"].append({"message": message, "type": log_type})


def clean_error_message(msg: str) -> str:
    """Remove ANSI color codes from error messages."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\[0;[0-9]+m|\[0m')
    cleaned = ansi_escape.sub('', str(msg))
    # Also remove any remaining escape sequences
    cleaned = re.sub(r'\[[\d;]+m', '', cleaned)
    return cleaned


def download_worker(client_id: str, client_secret: str, playlist_url: str, output_dir: str, browser: str):
    global download_status
    
    download_status = {
        "running": True,
        "current_track": "",
        "current_artist": "",
        "progress": 0,
        "total": 0,
        "completed": [],
        "failed": [],
        "log": [],
        "playlist_name": "",
        "playlist_image": "",
        "eta": ""
    }
    
    try:
        add_log("🔐 Connecting to Spotify...", "info")
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        playlist_id = extract_playlist_id(playlist_url)
        
        # Get playlist info with image
        playlist_info = sp.playlist(playlist_id, fields="name,images,tracks(total)")
        playlist_name = playlist_info.get("name", "Unknown")
        total_tracks = playlist_info.get("tracks", {}).get("total", 0)
        images = playlist_info.get("images", [])
        
        download_status["playlist_name"] = playlist_name
        download_status["playlist_image"] = images[0]["url"] if images else ""
        download_status["total"] = total_tracks
        
        add_log(f"📋 Found: {playlist_name} ({total_tracks} tracks)", "info")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        add_log(f"📁 Output: {output_path.absolute()}", "info")
        
        if browser != "none":
            add_log(f"🍪 Using {browser.title()} cookies for authentication...", "info")
        
        # Fetch all tracks
        tracks = []
        offset = 0
        while True:
            results = sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=100,
                fields="items(track(name,artists(name))),next"
            )
            for item in results.get("items", []):
                track = item.get("track")
                if track:
                    artists = track.get("artists", [])
                    artist = artists[0]["name"] if artists else "Unknown Artist"
                    name = track.get("name", "Unknown")
                    tracks.append({"artist": artist, "track": name})
            if not results.get("next"):
                break
            offset += 100
        
        # Download each track
        for idx, track_info in enumerate(tracks, 1):
            artist = track_info["artist"]
            track_name = track_info["track"]
            search_query = f"{artist} - {track_name}"
            
            download_status["current_track"] = track_name
            download_status["current_artist"] = artist
            download_status["progress"] = idx
            
            safe_name = sanitize_filename(search_query)
            output_template = str(output_path / f"{safe_name}.%(ext)s")
            
            # Check if file already exists
            expected_file = output_path / f"{safe_name}.mp3"
            if expected_file.exists():
                download_status["completed"].append(search_query)
                add_log(f"{track_name} - {artist} (already exists)", "success")
                continue
            
            # Enhanced yt-dlp options
            ydl_opts = {
                "default_search": "ytsearch1",
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "outtmpl": output_template,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": False,
                "noplaylist": True,
                "overwrites": False,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-us,en;q=0.5",
                },
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 30,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                    }
                },
            }
            
            # Add browser cookies if selected
            if browser != "none":
                ydl_opts["cookiesfrombrowser"] = (browser,)
            
            success = False
            last_error = ""
            
            # Try with selected browser, then fallback to no cookies
            browsers_to_try = []
            if browser != "none":
                browsers_to_try.append(browser)
            browsers_to_try.append(None)  # Last resort: no cookies
            
            for attempt_browser in browsers_to_try:
                try:
                    if attempt_browser:
                        # Only set cookies if we have a browser
                        ydl_opts["cookiesfrombrowser"] = (attempt_browser,)
                        # Reduce timeout for cookie attempts
                        ydl_opts["socket_timeout"] = 10
                    else:
                        ydl_opts.pop("cookiesfrombrowser", None)
                        ydl_opts["socket_timeout"] = 30
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([f"ytsearch1:{search_query}"])
                    
                    download_status["completed"].append(search_query)
                    add_log(f"{track_name} - {artist}", "success")
                    success = True
                    break
                    
                except Exception as e:
                    last_error = clean_error_message(str(e))
                    # Log the specific browser failure but don't stop unless all fail
                    if attempt_browser:
                        add_log(f"Warning: Failed to use {attempt_browser} cookies: {last_error[:50]}...", "info")
                    continue
            
            if not success:
                download_status["failed"].append(search_query)
                short_error = last_error[:50] + "..." if len(last_error) > 50 else last_error
                short_error = short_error.replace("ERROR:", "").strip()
                add_log(f"{track_name}: {short_error}", "error")
            
            # Delay between tracks
            time.sleep(random.uniform(1.0, 2.0))
        
        completed = len(download_status['completed'])
        failed = len(download_status['failed'])
        add_log(f"🎉 Complete! {completed} downloaded, {failed} failed", "info")
        
    except Exception as e:
        add_log(f"Error: {clean_error_message(str(e))}", "error")
    
    finally:
        download_status["running"] = False


# ============== FLASK ROUTES ==============

@app.route("/")
def index():
    if 'csrf_token' not in session:
        session['csrf_token'] = os.urandom(24).hex()
    return render_template_string(HTML_TEMPLATE, csrf_token=session['csrf_token'])


@app.route("/start", methods=["POST"])
def start_download():
    global download_status
    
    if download_status.get("running"):
        return jsonify({"error": "Download already in progress"})
    
    # CSRF Protection
    token = request.headers.get('X-CSRFToken')
    if not token or token != session.get('csrf_token'):
        return jsonify({"error": "Invalid CSRF token"}), 403
    
    data = request.json
    client_id = data.get("client_id", "").strip()
    client_secret = data.get("client_secret", "").strip()
    playlist_url = data.get("playlist_url", "").strip()
    output_dir = data.get("output_dir", "downloads").strip()
    browser = data.get("browser", "chrome").strip()
    
    if not all([client_id, client_secret, playlist_url]):
        return jsonify({"error": "Missing required fields"})
    
    thread = threading.Thread(
        target=download_worker,
        args=(client_id, client_secret, playlist_url, output_dir, browser)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})


@app.route("/status")
def get_status():
    status_copy = download_status.copy()
    download_status["log"] = []
    return jsonify(status_copy)


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🎵  SpotiDown Premium Edition v2                       ║
    ║                                                           ║
    ║   Open your browser to:                                  ║
    ║   → http://localhost:5000                                ║
    ║                                                           ║
    ║   Press Ctrl+C to stop the server                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=False, port=5000, threaded=True)