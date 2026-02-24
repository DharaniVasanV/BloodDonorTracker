from flask import Flask, render_template_string, jsonify
from firebase_config import db
from auth import auth_bp
from blood_requests import requests_bp
from hospitals import hospitals_bp
from donors import donors_bp
import os

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(requests_bp)
app.register_blueprint(hospitals_bp)
app.register_blueprint(donors_bp)

# ----------------------------
# Dashboard HTML Template (Hospital Focus)
# ----------------------------
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Hospital Emergency Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
    <style>
        :root { 
            --bg: #0f172a; 
            --surface: rgba(30, 41, 59, 0.6); 
            --surface-hover: rgba(51, 65, 85, 0.8);
            --primary: #ef4444; 
            --primary-dark: #dc2626;
            --primary-glow: rgba(239, 68, 68, 0.3);
            --secondary: #6366f1; 
            --text: #f8fafc; 
            --muted: #94a3b8; 
            --border: rgba(255, 255, 255, 0.1); 
            --glass: rgba(255, 255, 255, 0.03);
            --radius-lg: 24px;
            --radius-md: 16px;
            --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.4);
        }
        
        * { box-sizing: border-box; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        
        body { 
            margin: 0; 
            font-family: 'Outfit', 'Inter', sans-serif; 
            background: var(--bg); 
            color: var(--text); 
            display: flex; 
            height: 100vh; 
            overflow: hidden; 
            background-image: 
                radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(239, 68, 68, 0.05) 0%, transparent 50%);
        }
        
        /* Animations */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 
            0% { transform: scale(1); box-shadow: 0 0 0 0 var(--primary-glow); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        .pulse { animation: pulse 2s infinite; }

        /* Sidebar Navigation */
        aside { 
            width: 280px; 
            background: rgba(15, 23, 42, 0.8); 
            backdrop-filter: blur(20px);
            border-right: 1px solid var(--border);
            color: white; 
            display: flex; 
            flex-direction: column; 
            z-index: 1000; 
        }
        .sidebar-brand { 
            padding: 40px 28px; 
            font-weight: 800; 
            font-size: 24px; 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            letter-spacing: -1px;
            color: white;
        }
        .sidebar-nav { flex: 1; padding: 0 16px; }
        .nav-item { 
            padding: 14px 20px; 
            display: flex; 
            align-items: center; 
            gap: 14px; 
            cursor: pointer; 
            border-radius: 16px;
            color: var(--muted); 
            font-weight: 600; 
            margin-bottom: 8px;
            font-size: 15px;
            position: relative;
        }
        .nav-item:hover { background: rgba(255, 255, 255, 0.05); color: white; transform: translateX(4px); }
        .nav-item.active { 
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.15), transparent);
            color: white; 
            box-shadow: inset 2px 0 0 var(--primary);
        }
        .nav-item i { font-size: 20px; width: 28px; }
        
        /* Main Viewport */
        main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        .top-bar { 
            height: 80px; 
            background: rgba(15, 23, 42, 0.4); 
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border); 
            display: flex; 
            align-items: center; 
            justify-content: space-between; 
            padding: 0 40px; 
            z-index: 100;
        }
        .content-area { flex: 1; overflow-y: auto; padding: 40px; scroll-behavior: smooth; }
        
        /* Dashboard Sections */
        .dashboard-section { display: none; }
        .dashboard-section.active { display: block; animation: fadeIn 0.4s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Summary Grid */
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; margin-bottom: 40px; }
        .summary-card { 
            background: var(--surface); 
            backdrop-filter: blur(10px);
            padding: 30px; 
            border-radius: var(--radius-lg); 
            border: 1px solid var(--border);
            display: flex; 
            flex-direction: column;
            box-shadow: var(--shadow);
        }
        .summary-card .label { font-size: 12px; font-weight: 800; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; }
        .summary-card .value { font-size: 36px; font-weight: 800; color: white; letter-spacing: -1px; }
        .summary-card i { 
            font-size: 24px; margin-bottom: 20px; 
            width: 54px; height: 54px; border-radius: 16px;
            display: grid; place-items: center;
            background: var(--glass);
        }
        
        /* Map Container */
        #map { 
            height: 550px; width: 100%; border-radius: 32px; 
            border: 1px solid var(--border); z-index: 1; 
            box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.5);
        }
        
        /* Utils */
        .card { 
            background: var(--surface); 
            backdrop-filter: blur(10px);
            padding: 32px; 
            border-radius: var(--radius-lg); 
            border: 1px solid var(--border); 
            box-shadow: var(--shadow);
        }
        .card h3 { margin-top: 0; font-size: 20px; font-weight: 700; margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
        
        .btn { 
            background: linear-gradient(135deg, var(--primary), #b91c1c); 
            color: white; border: none; padding: 14px 28px; 
            border-radius: 14px; font-weight: 700; cursor: pointer; 
            box-shadow: 0 4px 12px var(--primary-glow);
            font-size: 14px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px var(--primary-glow); filter: brightness(1.1); }
        .btn:active { transform: translateY(0); }

        .badge { font-size: 10px; padding: 5px 12px; border-radius: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge-red { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.2); }
        .badge-blue { background: rgba(99, 102, 241, 0.2); color: #c7d2fe; border: 1px solid rgba(99, 102, 241, 0.2); }
        .badge-green { background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.2); }
        
        /* Auth */
        #authOverlay { 
            position: fixed; inset: 0; background: #020617; 
            z-index: 9999; display: flex; align-items:center; justify-content: center; 
            background-image: 
                radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(239, 68, 68, 0.1) 0%, transparent 50%);
        }
        .auth-card { 
            background: var(--surface); 
            backdrop-filter: blur(20px);
            border-radius: 32px; 
            padding: 48px; 
            width: 100%; 
            max-width: 480px; 
            box-shadow: 0 50px 100px -20px rgba(0, 0, 0, 0.7);
            border: 1px solid var(--border);
        }
        
        /* Modal */
        .modal-overlay { 
            position: fixed; inset: 0; background: rgba(2, 6, 23, 0.85); 
            z-index: 2000; display: none; align-items: center; justify-content: center; 
            backdrop-filter: blur(16px); 
        }
        .modal { 
            background: #1e293b; border-radius: 32px; width: 95%; max-width: 680px; 
            padding: 40px; border: 1px solid var(--border); box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.8);
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }
        .modal-close { cursor: pointer; color: var(--muted); font-size: 24px; }
        
        /* Table */
        table { width: 100%; border-collapse: separate; border-spacing: 0 8px; margin-top: 16px; }
        th { text-align: left; padding: 12px 20px; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
        td { background: var(--glass); padding: 16px 20px; font-size: 14px; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
        td:first-child { border-left: 1px solid var(--border); border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        td:last-child { border-right: 1px solid var(--border); border-top-right-radius: 12px; border-bottom-right-radius: 12px; }

        /* Form Controls */
        .form-group { margin-bottom: 24px; }
        .form-group label { display: block; font-size: 13px; font-weight: 700; color: var(--muted); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        input, select { 
            width: 100%; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border); 
            padding: 14px 18px; border-radius: 14px; color: white; font-size: 15px;
            font-family: inherit;
        }
        input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 4px var(--primary-glow); }
    </style>
</head>
<body>

    <!-- Auth Section -->
    <div id="authOverlay">
        <!-- Login Card -->
        <div class="auth-card" id="loginCard">
            <h2 style="margin-top:0; color:var(--primary)"><i class="fa-solid fa-hospital"></i> Hospital Login</h2>
            <div class="form-group">
                <label>Email Address</label>
                <input type="email" id="loginEmail" placeholder="hospital@emergency.com">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="loginPass" placeholder="••••••••">
            </div>
            <button class="btn" onclick="login()">Sign In</button>
            <p style="text-align:center; font-size:12px; margin-top:16px; color:var(--muted)">Don't have an account? <a href="javascript:void(0)" onclick="toggleAuth('register')" style="color:var(--primary)">Register</a></p>
        </div>

        <!-- Register Card -->
        <div class="auth-card" id="registerCard" style="display:none; max-width: 500px">
            <h2 style="margin-top:0; color:var(--primary)"><i class="fa-solid fa-file-signature"></i> Hospital Registration</h2>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 12px">
                <div class="form-group">
                    <label>Hospital Name</label>
                    <input type="text" id="regName" placeholder="City General Hospital">
                </div>
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" id="regEmail" placeholder="admin@hospital.com">
                </div>
                <div class="form-group">
                    <label>Phone Number</label>
                    <input type="text" id="regPhone" placeholder="+91 9876543210">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="regPass" placeholder="••••••••">
                </div>
                <div class="form-group">
                    <label>Latitude</label>
                    <input type="number" id="regLat" step="any" placeholder="12.9716">
                </div>
                <div class="form-group">
                    <label>Longitude</label>
                    <input type="number" id="regLon" step="any" placeholder="77.5946">
                </div>
            </div>
            <div class="form-group">
                <label style="display:flex; align-items:center; gap:8px; cursor:pointer">
                    <input type="checkbox" id="regBloodBank" style="width:auto"> Has Blood Bank?
                </label>
            </div>
            <button class="btn" onclick="register()">Create Account</button>
            <p style="text-align:center; font-size:12px; margin-top:16px; color:var(--muted)">Already have an account? <a href="javascript:void(0)" onclick="toggleAuth('login')" style="color:var(--primary)">Sign In</a></p>
        </div>
    </div>

    <!-- Main App UI -->
    <aside>
        <div class="sidebar-brand">
            <div style="background:var(--primary); width:40px; height:40px; border-radius:12px; display:grid; place-items:center; box-shadow:0 8px 16px var(--primary-glow)">
                <i class="fa-solid fa-heart-pulse" style="color:white; font-size:20px"></i>
            </div>
            <span>LifeLink<span style="color:var(--primary)">LMS</span></span>
        </div>
        <div class="sidebar-nav">
            <div class="nav-item active" onclick="showSection('overview')" data-nav="overview">
                <i class="fa-solid fa-house"></i> Overview
            </div>
            <div class="nav-item" onclick="showSection('requests')" data-nav="requests">
                <i class="fa-solid fa-truck-medical"></i> Emergencies
            </div>
            <div class="nav-item" onclick="showSection('donors-map')" data-nav="donors-map">
                <i class="fa-solid fa-map-location-dot"></i> Live Map
            </div>
            <div class="nav-item" onclick="showSection('inventory')" data-nav="inventory">
                <i class="fa-solid fa-box-archive"></i> Inventory
            </div>
        </div>
        <div style="padding:24px; border-top:1px solid var(--border)">
             <div class="nav-item" onclick="logout()" style="color:#fca5a5; margin-bottom:0">
                <i class="fa-solid fa-right-from-bracket"></i> Logout
            </div>
        </div>
    </aside>

    <main>
        <div class="top-bar">
            <h2 id="sectionTitle" style="margin:0; font-size:18px; font-weight:700">Dashboard Overview</h2>
            <div style="display:flex; align-items:center; gap:24px">
                <div style="text-align:right">
                    <div id="hospitalInfo" style="font-weight:700; font-size:14px">Loading...</div>
                    <div style="font-size:11px; color:var(--muted)">Emergency Unit 01</div>
                </div>
                <div style="width:44px; height:44px; border-radius:14px; background:var(--glass); display:grid; place-items:center; border:1px solid var(--border)">
                    <i class="fa-solid fa-hospital-user" style="color:var(--primary); font-size:18px"></i>
                </div>
            </div>
        </div>

        <div class="content-area">
            <!-- Section: Overview -->
            <div id="section-overview" class="dashboard-section active">
                <div class="summary-grid">
                    <div class="summary-card">
                        <i class="fa-solid fa-fire-pulse pulse" style="color:#ef4444"></i>
                        <span class="label">Active Emergencies</span>
                        <span class="value" id="statActiveReqs">0</span>
                    </div>
                    <div class="summary-card">
                        <i class="fa-solid fa-hand-holding-droplet" style="color:#f59e0b"></i>
                        <span class="label">Fulfilled Today</span>
                        <span class="value" id="statFulfilled">0</span>
                    </div>
                    <div class="summary-card">
                        <i class="fa-solid fa-hospital-user" style="color:#10b981"></i>
                        <span class="label">Nearby Blood Banks</span>
                        <span class="value" id="statHospitals">0</span>
                    </div>
                    <div class="summary-card">
                        <i class="fa-solid fa-users" style="color:#6366f1"></i>
                        <span class="label">Ready Donors (10km)</span>
                        <span class="value" id="statDonors">0</span>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 380px; gap: 32px">
                    <div class="card" style="min-height: 440px">
                        <h3 style="display:flex; justify-content:space-between; align-items:center">
                            <span><i class="fa-solid fa-clock-rotate-left"></i> Live Operations</span>
                            <button class="btn" style="padding:8px 16px; font-size:12px" onclick="showSection('requests')">New Request</button>
                        </h3>
                        <div id="overviewRequests" style="margin-top:24px">
                             <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:240px; color:var(--muted)">
                                <i class="fa-solid fa-circle-check" style="font-size:48px; margin-bottom:16px; opacity:0.3"></i>
                                <p>All clear. No active requests.</p>
                             </div>
                        </div>
                    </div>
                    <div class="card">
                        <h3><i class="fa-solid fa-chart-pie"></i> Pulse Analytics</h3>
                        <div style="height: 340px; display:flex; flex-direction:column; gap:24px; justify-content:center">
                            <div>
                                <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:10px; font-weight:600">
                                    <span>Emergency Response Efficiency</span>
                                    <span style="color:var(--primary)">92%</span>
                                </div>
                                <div style="height:10px; background:var(--glass); border-radius:5px; overflow:hidden">
                                    <div style="width:92%; height:100%; background:linear-gradient(90deg, var(--primary), #ef4444); box-shadow:0 0 10px var(--primary-glow)"></div>
                                </div>
                            </div>
                            <div>
                                <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:10px; font-weight:600">
                                    <span>Donor Engagement Rate</span>
                                    <span style="color:var(--secondary)">68%</span>
                                </div>
                                <div style="height:10px; background:var(--glass); border-radius:5px; overflow:hidden">
                                    <div style="width:68%; height:100%; background:linear-gradient(90deg, var(--secondary), #6366f1)"></div>
                                </div>
                            </div>
                            <div style="background:var(--glass); padding:20px; border-radius:18px; border:1px solid var(--border)">
                                <h4 style="margin:0 0 8px 0; font-size:14px; color:white">Strategy Tip</h4>
                                <p style="font-size:12px; color:var(--muted); line-height:1.6; margin:0">Increasing broadcast radius slightly during night hours improves fulfillment speed by 14%.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section: Requests Management -->
            <div id="section-requests" class="dashboard-section">
                <div style="display:grid; grid-template-columns: 380px 1fr; gap: 32px">
                    <div class="card">
                        <h3><i class="fa-solid fa-bullhorn" style="color:var(--primary)"></i> Broadcast Emergency</h3>
                        <div style="background:var(--glass); padding:20px; border-radius:18px; margin-bottom:24px; border:1px solid var(--border)">
                            <p style="font-size:12px; color:var(--muted); margin:0">Broadcasts notify all eligible donors within the calculated radius immediately.</p>
                        </div>
                        <div class="form-group">
                            <label>Target Blood Group</label>
                            <select id="reqBloodGroup">
                                <option>A+</option><option>A-</option><option>B+</option><option>B-</option>
                                <option>AB+</option><option>AB-</option><option>O+</option><option>O-</option>
                            </select>
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px">
                            <div class="form-group">
                                <label>Units Required</label>
                                <input type="number" id="reqQty" value="1" min="1">
                            </div>
                            <div class="form-group">
                                <label>Criticality</label>
                                <select id="reqLevel">
                                    <option value="normal">Normal</option>
                                    <option value="urgent">Urgent</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Response Window (Minutes)</label>
                            <input type="number" id="reqTime" value="30">
                        </div>
                        <button class="btn" style="width:100%; height:50px; font-size:15px" onclick="createRequest()">
                            <i class="fa-solid fa-tower-broadcast"></i> Initiate Broadcast
                        </button>
                    </div>
                    <div class="card">
                        <h3><i class="fa-solid fa-list-check"></i> Active Broadcasts</h3>
                        <div id="activeRequestsTable" style="margin-top:16px">
                            <div style="text-align:center; padding:40px; color:var(--muted)">
                                <i class="fa-solid fa-clipboard-list" style="font-size:48px; opacity:0.2; margin-bottom:16px"></i>
                                <p>No active broadcasts at the moment.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section: Live Map -->
            <div id="section-donors-map" class="dashboard-section">
                <div id="map"></div>
            </div>
            
            <!-- Section: Inventory (New) -->
            <div id="section-inventory" class="dashboard-section">
                <div class="card">
                    <h3><i class="fa-solid fa-boxes-stacked"></i> Blood Group Inventory</h3>
                    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top:24px">
                        <div style="background:var(--glass); padding:24px; border-radius:20px; text-align:center; border:1px solid var(--border)">
                            <div style="font-size:24px; font-weight:800; color:var(--primary); margin-bottom:8px">A+</div>
                            <div style="font-size:12px; color:var(--muted); text-transform:uppercase">Available: 12 Units</div>
                        </div>
                        <div style="background:var(--glass); padding:24px; border-radius:20px; text-align:center; border:1px solid var(--border)">
                            <div style="font-size:24px; font-weight:800; color:var(--primary); margin-bottom:8px">B+</div>
                            <div style="font-size:12px; color:var(--muted); text-transform:uppercase">Available: 8 Units</div>
                        </div>
                        <div style="background:var(--glass); padding:24px; border-radius:20px; text-align:center; border:1px solid var(--border)">
                            <div style="font-size:24px; font-weight:800; color:var(--primary); margin-bottom:8px">O+</div>
                            <div style="font-size:12px; color:var(--muted); text-transform:uppercase">Available: 15 Units</div>
                        </div>
                        <div style="background:var(--glass); padding:24px; border-radius:20px; text-align:center; border:1px solid var(--border)">
                            <div style="font-size:24px; font-weight:800; color:var(--primary); margin-bottom:8px">AB+</div>
                            <div style="font-size:12px; color:var(--muted); text-transform:uppercase">Available: 5 Units</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Modal: Request Details -->
    <div id="detailsModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <div>
                    <h2 id="modalTitle" style="margin:0; color:white">Tracking Responders</h2>
                    <div id="modalSub" style="font-size:12px; color:var(--muted); margin-top:4px">Real-time donor arrival status</div>
                </div>
                <span class="modal-close" onclick="closeModal()">&times;</span>
            </div>
            <div id="modalContent">
                <div id="donorList">
                    <table id="donorTable">
                        <thead>
                            <tr><th>Donor Identity</th><th>Status</th><th style="text-align:right">Action</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        let map, hospitalMarker;
        let donors = {};
        let hospitalToken = localStorage.getItem('hospitalToken');

        if (hospitalToken) {
            document.getElementById('authOverlay').style.display = 'none';
            initApp();
        }

        async function login() {
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPass').value;
            const res = await fetch('/hospital/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password})
            });
            const data = await res.json();
            if (data.token) {
                localStorage.setItem('hospitalToken', data.token);
                location.reload();
            } else {
                alert(data.message);
            }
        }

        async function register() {
            const payload = {
                hospital_name: document.getElementById('regName').value,
                email: document.getElementById('regEmail').value,
                phone: document.getElementById('regPhone').value,
                password: document.getElementById('regPass').value,
                latitude: document.getElementById('regLat').value,
                longitude: document.getElementById('regLon').value,
                has_blood_bank: document.getElementById('regBloodBank').checked
            };

            const res = await fetch('/hospital/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.status === 201) {
                alert("Registration successful! Please login.");
                toggleAuth('login');
            } else {
                alert(data.message || "Registration failed");
            }
        }

        function toggleAuth(view) {
            document.getElementById('loginCard').style.display = view === 'login' ? 'block' : 'none';
            document.getElementById('registerCard').style.display = view === 'register' ? 'block' : 'none';
        }

        function initApp() {
            map = L.map('map').setView([20.5937, 78.9629], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            initHospital();
            updateDashboard();
            setInterval(updateDashboard, 5000);
        }

        async function initHospital() {
            const res = await fetch('/hospital/profile', {
                headers: {'Authorization': `Bearer ${hospitalToken}`}
            });
            const hospital = await res.json();
            document.getElementById('hospitalInfo').innerText = hospital.hospital_name;
            
            if (hospital.latitude && hospital.longitude) {
                const hLat = parseFloat(hospital.latitude);
                const hLon = parseFloat(hospital.longitude);
                map.setView([hLat, hLon], 13);
                L.marker([hLat, hLon], {
                    icon: L.divIcon({
                        className: 'hospital-marker',
                        html: '<div style="background:var(--primary); color:white; width:36px; height:36px; border-radius:50%; display:grid; place-items:center; box-shadow:0 0 0 4px rgba(239, 68, 68, 0.2)"><i class="fa-solid fa-hospital" style="font-size:18px"></i></div>',
                        iconSize: [36, 36],
                        iconAnchor: [18, 18]
                    })
                }).addTo(map).bindPopup(`<b>${hospital.hospital_name}</b> (Main Unit)`);
                
                // Add Radius Circle for active requests will be done in updateDashboard
                hospitalMarker = {lat: hLat, lon: hLon};
            }
        }

        function showSection(id) {
            document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            
            const section = document.getElementById(`section-${id}`);
            if(section) {
                section.classList.add('active');
                document.getElementById('sectionTitle').innerText = id.charAt(0).toUpperCase() + id.slice(1).replace('-', ' ');
            }
            
            // Highlight nav using data-nav
            const navItem = document.querySelector(`.nav-item[data-nav="${id}"]`);
            if(navItem) navItem.classList.add('active');

            if (id === 'donors-map' && map) {
                setTimeout(() => map.invalidateSize(), 150);
            }
        }

        async function updateDashboard() {
            try {
                const summaryRes = await fetch('/dashboard/summary', {
                    headers: {'Authorization': `Bearer ${hospitalToken}`}
                });
                const summary = await summaryRes.json();
                document.getElementById('statActiveReqs').innerText = summary.active_requests;
                document.getElementById('statFulfilled').innerText = summary.fulfilled_today;
                document.getElementById('statHospitals').innerText = summary.nearby_blood_banks;
                document.getElementById('statDonors').innerText = summary.nearby_donors;

                const res = await fetch('/latest_data');
                const data = await res.json();
                
                Object.keys(data).forEach(id => {
                    const u = data[id];
                    const markerColor = (u.emergency || '').toLowerCase() === 'yes' ? '#ef4444' : '#6366f1';
                    if (!donors[id]) {
                        donors[id] = L.circleMarker([u.lat, u.lon], {
                            radius: 8,
                            fillColor: markerColor,
                            color: "#fff",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8
                        }).addTo(map).bindPopup(`<b>${u.name}</b><br>Group: ${u.blood_group || 'O+'}`);
                    } else {
                        donors[id].setLatLng([u.lat, u.lon]);
                    }
                });

                fetchRequests();
            } catch (err) {
                console.error("Dashboard update failed:", err);
            }
        }

        async function fetchRequests() {
            const res = await fetch('/requests/list', {
                headers: {'Authorization': `Bearer ${hospitalToken}`}
            });
            const requests = await res.json();
            const list = document.getElementById('overviewRequests');
            const table = document.getElementById('activeRequestsTable');
            list.innerHTML = '';
            table.innerHTML = '';
            
            if(requests.length === 0) {
                 list.innerHTML = `
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:240px; color:var(--muted)">
                        <i class="fa-solid fa-circle-check" style="font-size:48px; margin-bottom:16px; opacity:0.3"></i>
                        <p>All clear. No active requests.</p>
                    </div>`;
                 table.innerHTML = `
                    <div style="text-align:center; padding:40px; color:var(--muted)">
                        <i class="fa-solid fa-clipboard-list" style="font-size:48px; opacity:0.2; margin-bottom:16px"></i>
                        <p>No active broadcasts at the moment.</p>
                    </div>`;
                 return;
            }

            requests.forEach(req => {
                const statusColor = req.status === 'open' ? 'badge-red' : 'badge-blue';
                const progress = (req.quantity_confirmed / req.quantity_required) * 100;
                const cardHtml = `
                    <div class="card" style="margin-bottom:20px; padding:24px; background:var(--glass)">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
                            <div style="display:flex; align-items:center; gap:12px">
                                <div style="width:48px; height:48px; background:var(--primary-glow); border-radius:12px; display:grid; place-items:center; color:var(--primary); font-weight:800; font-size:18px">
                                    ${req.blood_group}
                                </div>
                                <div>
                                    <div style="font-weight:700; color:white">Emergency Blood Request</div>
                                    <div style="font-size:11px; color:var(--muted)">ID: ${req.request_id.substring(0,8)}...</div>
                                </div>
                            </div>
                            <span class="badge ${statusColor}">${req.status.toUpperCase()}</span>
                        </div>
                        <div style="margin-bottom:16px">
                            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:8px">
                                <span style="color:var(--muted)">Fulfillment Progress</span>
                                <span style="color:white; font-weight:700">${req.quantity_confirmed} / ${req.quantity_required} Units</span>
                            </div>
                            <div style="height:8px; background:rgba(0,0,0,0.3); border-radius:4px; overflow:hidden">
                                <div style="width:${progress}%; height:100%; background:var(--primary); box-shadow:0 0 10px var(--primary-glow)"></div>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center">
                            <div style="display:flex; gap:16px">
                                <div style="font-size:11px; color:var(--muted)">
                                    <i class="fa-solid fa-triangle-exclamation" style="color:#ef4444"></i> Priority: <b>${(req.critical_level || 'Normal').toUpperCase()}</b>
                                </div>
                                <div style="font-size:11px; color:var(--muted)">
                                    <i class="fa-solid fa-clock"></i> Window: <b>${req.required_time_minutes}m</b>
                                </div>
                            </div>
                            <div style="display:flex; gap:8px">
                                <button class="btn" style="padding:8px 16px; font-size:12px; background:var(--secondary)" onclick="viewDetails('${req.request_id}')">Donors</button>
                                ${req.status === 'open' ? `<button class="btn" style="padding:8px 16px; font-size:12px; background:#475569" onclick="cancelRequest('${req.request_id}')">Cancel</button>` : ''}
                            </div>
                        </div>
                    </div>
                `;
                list.insertAdjacentHTML('beforeend', cardHtml);
                table.insertAdjacentHTML('beforeend', cardHtml);
            });
        }

        async function viewDetails(id) {
            const res = await fetch(`/requests/${id}/donors`, {
                headers: {'Authorization': `Bearer ${hospitalToken}`}
            });
            const donorsList = await res.json();
            const tbody = document.querySelector('#donorTable tbody');
            tbody.innerHTML = donorsList.length ? '' : '<tr><td colspan="3" style="text-align:center">No donors have accepted yet.</td></tr>';
            
            donorsList.forEach(d => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><b>${d.name}</b><br><small>${d.phone.substring(0,6)}****</small></td>
                    <td><span class="badge ${d.status === 'arrived' ? 'badge-blue' : 'badge-red'}">${d.status.replace('_',' ')}</span></td>
                    <td>
                        ${d.status !== 'arrived' ? `<button class="btn" style="padding:4px 8px; font-size:10px" onclick="confirmArrival('${id}', '${d.phone}')">Arrived</button>` : '<i class="fa-solid fa-check" style="color:var(--success)"></i>'}
                    </td>
                `;
                tbody.appendChild(tr);
            });
            document.getElementById('detailsModal').style.display = 'flex';
        }

        async function confirmArrival(reqId, phone) {
            const res = await fetch('/requests/confirm-arrival', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${hospitalToken}`
                },
                body: JSON.stringify({request_id: reqId, phone})
            });
            if((await res.json()).status === 'success') viewDetails(reqId);
        }

        async function cancelRequest(id) {
            if(!confirm("Cancel this broadcast?")) return;
            await fetch('/requests/cancel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${hospitalToken}`
                },
                body: JSON.stringify({request_id: id})
            });
            updateDashboard();
        }

        async function createRequest() {
            const payload = {
                blood_group: document.getElementById('reqBloodGroup').value,
                quantity_required: document.getElementById('reqQty').value,
                required_time_minutes: document.getElementById('reqTime').value,
                critical_level: document.getElementById('reqLevel').value
            };
            const res = await fetch('/requests/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${hospitalToken}`
                },
                body: JSON.stringify(payload)
            });
            if(res.status === 201) {
                alert("Broadcast successful!");
                updateDashboard();
                showSection('overview');
            }
        }

        function closeModal() { document.getElementById('detailsModal').style.display = 'none'; }
        
        function logout() {
            localStorage.removeItem('hospitalToken');
            location.reload();
        }

        if (hospitalToken) {
            document.getElementById('authOverlay').style.display = 'none';
            initApp();
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route("/health")
def health():
    return {"status": "ok", "app": "Hospital Emergency Dashboard"}

@app.errorhandler(404)
def not_found(e):
    return jsonify({"message": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"message": "Internal server error", "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
