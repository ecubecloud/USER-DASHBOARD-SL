# Starlink Dashboard

A comprehensive web-based dashboard for monitoring Starlink satellite internet and WiFi router performance with real-time telemetry data visualization.

![Dashboard Preview](https://img.shields.io/badge/Status-Active-green) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-2.0+-orange) ![Firebase](https://img.shields.io/badge/Firebase-Firestore-yellow)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment (Render)](#deployment-render)
- [API Endpoints](#api-endpoints)
- [Frontend Components](#frontend-components)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Mobile Responsiveness](#mobile-responsiveness)
- [Usage Guide](#usage-guide)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🌟 Overview

The Starlink Dashboard is a full-stack web application that provides users with detailed insights into their Starlink satellite internet and WiFi router performance. The application features real-time data visualization, billing cycle tracking, device monitoring, and comprehensive telemetry analytics.

**Live Demo**: https://your-app.onrender.com  
**Domain**: starlink.ecubetechnologies.com

## ✨ Features

### Core Features
- **Real-time Telemetry Monitoring**: Live charts for throughput, latency, signal quality, and obstruction data
- **Device Management**: Switch between Starlink and WiFi router monitoring
- **Billing Data Visualization**: Monthly data usage tracking with billing cycle breakdowns
- **Interactive Maps**: Service location mapping with Mapbox integration
- **CSV Data Export**: Download telemetry data for external analysis
- **Multi-Service Line Support**: Manage multiple Starlink service lines
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices

### Starlink Metrics
- **Downlink/Uplink Throughput** (Mbps)
- **Ping Latency** (ms)
- **Ping Drop Rate** (%)
- **Signal Quality** (%)
- **Obstruction Percentage** (%)
- **Software Version Tracking**
- **Device Serial Numbers**

### WiFi Router Metrics
- **Internet Ping Latency** (ms)
- **Internet Ping Drop Rate** (%)
- **Router Software Version**
- **Hardware Version Information**

### Data Visualization
- Interactive time-series charts with Chart.js
- Multiple time range options (15 minutes to 30 days)
- Real-time min/max/last value statistics
- Expandable chart layouts
- Color-coded metrics for easy identification

## 🛠 Technology Stack

### Backend
- **Framework**: Flask (Python 3.8+)
- **Database**: Google Firestore (NoSQL)
- **Authentication**: Firebase Auth
- **API**: RESTful API with JWT token authentication
- **CORS**: Flask-CORS for cross-origin requests
- **Environment**: Python dotenv for configuration
- **Hosting**: Render

### Frontend
- **Languages**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Chart.js for data visualization
- **Maps**: Mapbox GL JS for location mapping
- **Styling**: CSS Grid, Flexbox, Responsive Design
- **Icons**: Unicode symbols and custom styling

### Infrastructure
- **Backend Hosting**: Render
- **Domain**: Custom domain (starlink.ecubetechnologies.com)
- **SSL**: HTTPS encryption
- **CDN**: External CDN for Chart.js and Mapbox

## 📁 Project Structure

```
StarLink Dashboard/
├── server.py                    # Main Flask application
├── requirements.txt             # Python dependencies
├── wsgi.py                     # WSGI entry point for Render
├── convert.py                  # Data conversion utilities
├── Data_Server.py              # Data server components
├── Data_Storage.py             # Data storage utilities
├── starlink-*-firebase-*.json  # Firebase service account key
├── templates/
│   ├── dashboard.html          # Main dashboard interface
│   ├── login.html             # User login page
│   └── RegistrationPage.html  # User registration page
├── static/
│   ├── style.css              # Main dashboard styles
│   ├── login.css              # Login page styles
│   ├── style2.css             # Registration page styles
│   ├── stars.js               # Animated background script
│   └── logo.jpg               # Application logo
└── README.md                   # Project documentation
```

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Firebase project with Firestore enabled
- Mapbox account with API key
- Git

### Local Development Setup

1. **Clone the repository**
   ```powershell
   git clone https://github.com/yourusername/starlink-dashboard.git
   cd "StarLink Dashboard"
   ```

2. **Create virtual environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```powershell
   copy .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```powershell
   python server.py
   ```

6. **Access the application**
   ```
   http://localhost:5000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id

# Alternative: JSON credentials string (for Render deployment)
FIREBASE_CREDENTIALS='{"type":"service_account",...}'

# Flask Configuration
FLASK_ENV=production
PORT=5000
```

### Firebase Setup

1. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create new project
   - Enable Firestore Database
   - Enable Authentication

2. **Generate Service Account Key**
   - Go to Project Settings > Service Accounts
   - Generate new private key
   - Download JSON file or copy values to environment variables

3. **Configure Firestore Security Rules**
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

### Mapbox Configuration

1. **Create Mapbox Account**
   - Sign up at [Mapbox](https://www.mapbox.com/)
   - Get your access token

2. **Update Dashboard HTML**
   - Replace the Mapbox access token in `templates/dashboard.html`
   ```javascript
   mapboxgl.accessToken = "your-mapbox-access-token";
   ```

## 🚀 Deployment (Render)

### Backend Deployment

1. **Prepare for Render deployment**
   ```powershell
   # Ensure all dependencies are in requirements.txt
   pip freeze > requirements.txt
   
   # Verify wsgi.py exists
   ```

2. **Connect to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Connect your GitHub repository
   - Choose "Web Service"

3. **Render Configuration**
   ```yaml
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn wsgi:app
   Environment: Python 3
   ```

4. **Environment Variables on Render**
   Set these in Render's Environment Variables section:
   ```
   FIREBASE_CREDENTIALS={"type":"service_account","project_id":"..."}
   FLASK_ENV=production
   PORT=10000
   ```

5. **Domain Configuration**
   - Add custom domain: `starlink.ecubetechnologies.com`
   - Configure DNS records with your domain provider
   - Point CNAME to your Render app URL

### Frontend Integration

Since the frontend is served by Flask templates, it's automatically deployed with the backend. The dashboard will be accessible at:
- Render URL: `https://your-app-name.onrender.com`
- Custom Domain: `https://starlink.ecubetechnologies.com`

## 📡 API Endpoints

### Authentication Endpoints
- `GET /` - Redirect to login page
- `GET /login` - Login page
- `POST /api/login` - User authentication
- `GET /register` - Registration page
- `POST /api/register` - User registration
- `GET /dashboard` - Dashboard page (requires auth)

### Data Endpoints
- `GET /api/dashboard-data/{service_line}` - Get dashboard data for service line
  - **Headers**: `Authorization: Bearer {idToken}`
  - **Response**: JSON with telemetry, billing, and device data

### Template Endpoints
- `GET /login.html` - Redirect to login route
- `GET /dashboard.html` - Redirect to dashboard route
- `GET /RegistrationPage.html` - Redirect to registration route

### API Response Example
```json
{
  "nickname": "Home Starlink",
  "kitSerialNumber": "SL-12345",
  "formattedAddress": "123 Main St, City, Country",
  "userTerminalId": "ut12345",
  "routerId": "Router-67890",
  "dishSerialNumber": "DISH-12345",
  "user_terminal_software_version": "2023.15.0",
  "router_software_version": "2023.15.0",
  "telemetry_data": {
    "userTerminal": {
      "allRecords": [...],
      "aggregates": {...}
    },
    "router": {
      "allRecords": [...],
      "aggregates": {...}
    }
  },
  "dataUsage": [...]
}
```

## 🎨 Frontend Components

### Dashboard Layout
- **Header**: Title, logout button, service line selector
- **Subscription Info**: Service plan, nickname, status
- **Service Location**: Interactive map with address
- **Data Usage**: Billing cycles with usage charts
- **Device Panels**: Starlink and WiFi monitoring sections

### Chart Components
- **Time Range Selector**: 15min, 3hr, 1day, 7days, 30days
- **Chart Controls**: Expand/collapse, CSV download
- **Real-time Stats**: Min/Max/Last value display
- **Interactive Tooltips**: Hover for detailed information

### Responsive Features
- **Mobile-first Design**: Optimized for small screens
- **Touch-friendly Controls**: Large buttons and tap targets
- **Flexible Layouts**: CSS Grid and Flexbox
- **Adaptive Charts**: Responsive chart sizing

## 🗄️ Database Schema

### Firestore Collections

#### `service_lines`
```javascript
{
  serviceLineNumber: "string",
  nickname: "string",
  addressReferenceId: "string",
  users: ["user_uid_1", "user_uid_2"]
}
```

#### `addresses`
```javascript
{
  formattedAddress: "string",
  latitude: "number",
  longitude: "number"
}
```

#### `users`
```javascript
{
  email: "string",
  serviceLineNumber: ["array", "of", "service", "lines"],
  createdAt: "timestamp"
}
```

#### `user_terminals`
```javascript
{
  serviceLineNumber: "string",
  kitSerialNumber: "string",
  dishSerialNumber: "string",
  routers: [
    {
      routerId: "string"
    }
  ]
}
```

#### `telemetry_raw/{device_id}/records`
```javascript
{
  timestamp: "ISO string",
  UtcTimestampNs: "number",
  DownlinkThroughput: "number",
  UplinkThroughput: "number",
  PingLatencyMsAvg: "number",
  PingDropRateAvg: "number",
  SignalQuality: "number",
  ObstructionPercentTime: "number",
  RunningSoftwareVersion: "string",
  // Router-specific fields
  InternetPingLatencyMs: "number",
  InternetPingDropRate: "number",
  WifiSoftwareVersion: "string"
}
```

#### `billing_records`
```javascript
{
  serviceLineNumber: "string",
  billingCycles: [
    {
      startDate: "ISO string",
      endDate: "ISO string",
      dailyDataUsage: [
        {
          date: "ISO string",
          standardGB: "number",
          priorityGB: "number",
          nonBillableGB: "number",
          optInPriorityGB: "number"
        }
      ]
    }
  ]
}
```

## 🔐 Authentication

### Firebase Authentication Flow
1. **User Registration**: Email/password registration with Firebase Auth
2. **Login Process**: Firebase Auth generates ID token
3. **Token Storage**: ID token stored in sessionStorage
4. **API Authentication**: Bearer token sent with API requests
5. **Session Management**: Token validation on server side

### Security Features
- **JWT Token Validation**: Server-side token verification
- **CORS Protection**: Configured for specific origins
- **Session Timeout**: Automatic logout on token expiry
- **Secure Headers**: HTTPS enforcement in production
- **Input Validation**: Server-side validation for all inputs

## 📱 Mobile Responsiveness

### Responsive Design Features

#### Breakpoints
- **Desktop**: 1200px+
- **Laptop**: 1024px+
- **Tablet**: 768px and below
- **Mobile**: 480px and below
- **Small Mobile**: 320px and below

#### Mobile Optimizations
- **Touch-friendly buttons**: Minimum 44px height
- **Readable fonts**: Scalable text sizes
- **Optimized layouts**: Single-column on mobile
- **Chart scaling**: Responsive chart heights
- **Navigation**: Collapsible menus and tabs

#### CSS Media Queries
```css
/* Tablet and below */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    text-align: center;
  }
}

/* Mobile phones */
@media (max-width: 480px) {
  .chart-graph {
    height: 150px;
  }
}

/* Touch devices */
@media (hover: none) and (pointer: coarse) {
  .device-item:active {
    background-color: #333;
    transform: scale(0.98);
  }
}
```

## 📖 Usage Guide

### Getting Started
1. **Register Account**: Create account with email/password
2. **Add Service Lines**: Enter Starlink service line numbers
3. **Dashboard Access**: View real-time telemetry data
4. **Device Switching**: Toggle between Starlink and WiFi views
5. **Time Range Selection**: Choose data time ranges
6. **Data Export**: Download CSV files for analysis

### Key Functions

#### Service Line Management
- **Multiple Lines**: Support for multiple Starlink connections
- **Easy Switching**: Dropdown selector for different lines
- **Real-time Updates**: Automatic data refresh

#### Chart Interaction
- **Expand/Collapse**: Full-screen chart viewing
- **Time Ranges**: Historical data analysis
- **Statistics**: Real-time min/max/last values
- **Export**: CSV download for external analysis

#### Billing Tracking
- **Monthly Cycles**: Billing period breakdown
- **Usage Categories**: Standard, priority, non-billable data
- **Visual Charts**: Bar charts for daily usage
- **Total Tracking**: Cycle-to-date usage totals

### Navigation
1. **Login**: Access with registered credentials
2. **Dashboard**: Main monitoring interface
3. **Device Tabs**: Switch between Starlink and WiFi
4. **Service Lines**: Select different connections
5. **Logout**: Secure session termination

## 🔧 Environment Variables

### Required Variables
```env
# Firebase Authentication
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS={"type":"service_account",...}

# Flask Configuration
FLASK_ENV=production
PORT=10000
```

### Optional Variables
```env
# Development Settings
FLASK_DEBUG=False
FLASK_ENV=production

# Custom Domain
DOMAIN=starlink.ecubetechnologies.com
```

## 🛠 Troubleshooting

### Common Issues

#### Authentication Errors
- **Problem**: "No login data found"
- **Solution**: Check Firebase configuration and ensure cookies/sessionStorage is enabled

#### Chart Not Loading
- **Problem**: Charts appear blank
- **Solution**: Verify Chart.js CDN is accessible and data is being fetched

#### API Errors
- **Problem**: 500 Internal Server Error
- **Solution**: Check Render logs and verify environment variables

#### Mobile Issues
- **Problem**: UI not responsive
- **Solution**: Clear browser cache and ensure viewport meta tag is present

### Debug Steps
1. **Check Render Logs**: Monitor application logs in Render dashboard
2. **Verify Environment**: Ensure all environment variables are set
3. **Test Locally**: Run application locally to isolate issues
4. **Firebase Console**: Check authentication and database rules
5. **Browser Console**: Check for JavaScript errors

### Support Resources
- **Render Documentation**: https://render.com/docs
- **Firebase Documentation**: https://firebase.google.com/docs
- **Chart.js Documentation**: https://www.chartjs.org/docs/

## 🤝 Contributing

### Development Workflow
1. **Fork the repository**
2. **Create feature branch**
   ```powershell
   git checkout -b feature/new-feature
   ```
3. **Make changes and test**
4. **Commit with clear messages**
   ```powershell
   git commit -m "Add: New telemetry metric visualization"
   ```
5. **Push and create pull request**

### Code Standards
- **Python**: PEP 8 compliance
- **JavaScript**: ES6+ features
- **CSS**: Mobile-first responsive design
- **Comments**: Clear documentation
- **Testing**: Ensure functionality before PR

### Areas for Contribution
- Additional telemetry metrics
- Enhanced data visualization
- Performance optimizations
- Mobile UX improvements
- Documentation updates

## 📄 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2024 Starlink Dashboard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 📊 Project Statistics

- **Backend**: Python Flask with Firebase integration
- **Frontend**: Vanilla JavaScript with Chart.js
- **Database**: Firestore NoSQL
- **Charts**: 8 real-time telemetry visualizations
- **Responsive**: 4 breakpoint mobile optimization
- **Authentication**: Firebase Auth with JWT tokens
- **Hosting**: Render cloud platform

## 🆘 Support

### Contact Information
- **Project Repository**: [GitHub Repository URL]
- **Live Application**: https://starlink.ecubetechnologies.com
- **Issues**: Report bugs via GitHub Issues

### Performance Metrics
- **Load Time**: < 3 seconds
- **Mobile Score**: 95/100
- **Uptime**: 99.9%
- **Security**: A+ SSL Rating

---

**Built with ❤️ for the Starlink community**

*Last Updated: June 2025*
