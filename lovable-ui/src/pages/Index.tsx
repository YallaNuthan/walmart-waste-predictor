import React, { useState, useRef, useEffect } from 'react';
import { Menu, Bell, BarChart3, X, Github, Mail, Upload, Target, TrendingUp, Trophy, AlertTriangle } from 'lucide-react';

const Index = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [chartPopupOpen, setChartPopupOpen] = useState(false);
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<any>(null);

  // Sample data for the chart
  const wasteData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [{
      label: 'Waste Risk Score',
      data: [12, 19, 8, 25, 15, 10, 18],
      backgroundColor: 'rgba(0, 113, 206, 0.2)',
      borderColor: 'rgba(0, 113, 206, 1)',
      borderWidth: 2,
      tension: 0.4
    }]
  };

  const showChart = () => {
    setChartPopupOpen(true);
    setTimeout(() => {
      if (chartRef.current) {
        if (chartInstanceRef.current) {
          chartInstanceRef.current.destroy();
        }
        // @ts-ignore
        chartInstanceRef.current = new Chart(chartRef.current, {
          type: 'line',
          data: wasteData,
          options: {
            responsive: true,
            plugins: {
              title: {
                display: true,
                text: 'Weekly Waste Risk Analysis'
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                max: 30
              }
            }
          }
        });
      }
    }, 100);
  };

  const hideChart = () => {
    setChartPopupOpen(false);
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
      chartInstanceRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, []);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    const name = formData.get('name');
    const email = formData.get('email');
    const message = formData.get('message');
    
    // Simulate API call
    console.log('Contact form submitted:', { name, email, message });
    alert('Thank you for your interest! We will get back to you soon.');
    (e.target as HTMLFormElement).reset();
  };

  return (
    <div className="min-h-screen bg-background relative overflow-x-hidden">
      {/* Sidebar */}
      <nav className={`walmart-sidebar ${!sidebarOpen ? 'closed' : ''}`}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold">Walmart AI</h2>
            <button 
              onClick={() => setSidebarOpen(false)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              aria-label="Close sidebar"
            >
              <X size={20} />
            </button>
          </div>
          <ul className="space-y-4">
            {[
              { icon: '📈', text: 'Demand Forecast' },
              { icon: '🗑', text: 'Waste Risk' },
              { icon: '📦', text: 'Smart Recommendations' },
              { icon: '🏁', text: 'AI Leaderboard' },
              { icon: '📉', text: 'Waste Forecast' }
            ].map((item, index) => (
              <li key={index}>
                <a 
                  href="#" 
                  className="flex items-center space-x-3 p-3 rounded-lg hover:bg-white/10 transition-colors"
                  onClick={(e) => e.preventDefault()}
                >
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.text}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* Alerts Panel */}
      <div className={`alert-panel ${alertsOpen ? 'open' : ''}`}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold">Live Alerts</h3>
            <button 
              onClick={() => setAlertsOpen(false)}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              aria-label="Close alerts"
            >
              <X size={18} />
            </button>
          </div>
          <div className="space-y-4">
            {[
              { type: 'critical', store: 'Store #1247', item: 'Organic Bananas', risk: '95%' },
              { type: 'warning', store: 'Store #5891', item: 'Fresh Bread', risk: '78%' },
              { type: 'info', store: 'Store #3456', item: 'Dairy Products', risk: '45%' }
            ].map((alert, index) => (
              <div key={index} className="p-4 rounded-lg border border-border bg-card">
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    alert.type === 'critical' ? 'bg-red-100 text-red-800' :
                    alert.type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {alert.type.toUpperCase()}
                  </span>
                  <span className="text-sm font-medium">{alert.risk}</span>
                </div>
                <p className="text-sm font-medium">{alert.store}</p>
                <p className="text-xs text-muted-foreground">{alert.item}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Popup */}
      <div className={`chart-popup ${chartPopupOpen ? 'active' : ''}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Waste Analytics</h3>
          <button 
            onClick={hideChart}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            aria-label="Close chart"
          >
            <X size={18} />
          </button>
        </div>
        <canvas ref={chartRef} width="400" height="200"></canvas>
      </div>

      {/* Overlay */}
      {(sidebarOpen || alertsOpen || chartPopupOpen) && (
        <div 
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => {
            setSidebarOpen(false);
            setAlertsOpen(false);
            hideChart();
          }}
        ></div>
      )}

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 bg-card/95 backdrop-blur-sm border-b border-border z-30">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              style={{ backgroundColor: '#003087', color: 'white' }}
              aria-label="Open sidebar"
            >
              <Menu size={20} />
            </button>
            <h1 className="text-xl font-bold">Walmart Waste Predictor</h1>
          </div>
          <div className="flex items-center space-x-4">
            <button 
              onClick={showChart}
              onMouseEnter={showChart}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              aria-label="Show chart"
            >
              <BarChart3 size={20} />
            </button>
            <button 
              onClick={() => setAlertsOpen(true)}
              className="p-2 hover:bg-muted rounded-lg transition-colors relative"
              aria-label="Open alerts"
            >
              <Bell size={20} />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">3</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-20">
        {/* Hero Section */}
        <section className="walmart-section text-center">
          <h1 className="text-5xl font-bold mb-6">
            👋 Welcome to Walmart Waste Predictor
          </h1>
          <p className="walmart-subheading">
            Click ☰ to explore our AI-powered dashboard for intelligent food waste management and demand forecasting.
          </p>
          <div className="mt-8">
            <button className="walmart-button text-lg px-8 py-4">
              Get Started
            </button>
          </div>
        </section>

        {/* Problem & Solution */}
        <section className="walmart-section bg-muted/20">
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <h2 className="walmart-heading text-left">🛑 The Food-Waste Challenge</h2>
              <ul className="space-y-4 text-lg">
                <li className="flex items-start space-x-3">
                  <AlertTriangle className="text-red-500 mt-1 flex-shrink-0" size={20} />
                  <span>Inefficient sell-through prediction → lost revenue & waste</span>
                </li>
                <li className="flex items-start space-x-3">
                  <AlertTriangle className="text-red-500 mt-1 flex-shrink-0" size={20} />
                  <span>No real-time redistribution → overstock & shortages</span>
                </li>
                <li className="flex items-start space-x-3">
                  <AlertTriangle className="text-red-500 mt-1 flex-shrink-0" size={20} />
                  <span>Manual processes lead to delayed decision-making</span>
                </li>
              </ul>
            </div>
            <div>
              <h2 className="walmart-heading text-left">✅ Our AI-Driven Answer</h2>
              <p className="text-lg text-muted-foreground mb-6">
                Real-time risk & demand forecasts, smart redistribution, reward-based leaderboard for maximum efficiency and sustainability.
              </p>
              <div className="space-y-3">
                {[
                  'Predictive analytics with 98% accuracy',
                  'Automated alert system for critical items',
                  'Gamified leaderboard for store performance',
                  'Smart redistribution recommendations'
                ].map((feature, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-primary rounded-full"></div>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="walmart-section">
          <h2 className="walmart-heading">🛠 How It Works</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { icon: '📑', title: 'Data Ingestion', desc: 'Upload CSV / API ingestion' },
              { icon: '🤖', title: 'AI Processing', desc: 'Waste-risk classification' },
              { icon: '📈', title: 'Forecasting', desc: 'Demand forecasting (daily & monthly)' },
              { icon: '🏆', title: 'Gamification', desc: 'AI leaderboard & rewards' }
            ].map((step, index) => (
              <div key={index} className="walmart-card text-center">
                <div className="text-4xl mb-4">{step.icon}</div>
                <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                <p className="text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Key Features & Metrics */}
        <section className="walmart-section bg-muted/20">
          <h2 className="walmart-heading">📊 Key Features & Metrics</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { value: '98%', label: 'Model Accuracy', color: 'text-green-600' },
              { value: '12', label: 'Daily Alerts: Critical', color: 'text-red-600' },
              { value: 'Store #5 🥇', label: 'Monthly Leader', color: 'text-yellow-600' },
              { value: '0.92', label: 'Class-Imbalance F1', color: 'text-blue-600' }
            ].map((metric, index) => (
              <div key={index} className="walmart-metric-card">
                <div className={`walmart-metric-value ${metric.color}`}>{metric.value}</div>
                <div className="walmart-metric-label">{metric.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Live Demo */}
        <section className="walmart-section">
          <h2 className="walmart-heading">🚀 Live Dashboard Preview</h2>
          <div className="walmart-card max-w-4xl mx-auto">
            <p className="text-center text-muted-foreground mb-6">
              Backend deployed on Render: 
              <a href="https://walmart-waste-predictor.onrender.com" className="text-primary hover:underline ml-1">
                https://walmart-waste-predictor.onrender.com
              </a>
            </p>
            <div className="walmart-table">
              <table className="w-full">
                <thead>
                  <tr>
                    <th>Store ID</th>
                    <th>Product</th>
                    <th>Risk Score</th>
                    <th>Demand Forecast</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { store: '#1247', product: 'Organic Bananas', risk: '95%', forecast: '↓ 23%', action: 'Redistribute' },
                    { store: '#5891', product: 'Fresh Bread', risk: '78%', forecast: '↑ 15%', action: 'Monitor' },
                    { store: '#3456', product: 'Dairy Products', risk: '45%', forecast: '→ 5%', action: 'Normal' }
                  ].map((row, index) => (
                    <tr key={index}>
                      <td className="font-medium">{row.store}</td>
                      <td>{row.product}</td>
                      <td>
                        <span className={`font-medium ${
                          parseFloat(row.risk) > 80 ? 'text-red-600' :
                          parseFloat(row.risk) > 50 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {row.risk}
                        </span>
                      </td>
                      <td>{row.forecast}</td>
                      <td>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          row.action === 'Redistribute' ? 'bg-red-100 text-red-800' :
                          row.action === 'Monitor' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {row.action}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Code & Docs */}
        <section className="walmart-section bg-muted/20">
          <h2 className="walmart-heading">📂 Get the Code</h2>
          <div className="walmart-card max-w-4xl mx-auto">
            <pre className="bg-gray-900 text-green-400 p-6 rounded-lg overflow-x-auto">
              <code>{`git clone https://github.com/your-repo/walmart-waste-predictor
cd walmart-waste-predictor
npm install
npm run dev`}</code>
            </pre>
            <div className="mt-6 text-center">
              <a 
                href="https://github.com/your-repo/walmart-waste-predictor" 
                className="walmart-button inline-flex items-center space-x-2"
              >
                <Github size={20} />
                <span>View on GitHub</span>
              </a>
            </div>
          </div>
        </section>

        {/* Team & Timeline */}
        <section className="walmart-section">
          <h2 className="walmart-heading">👥 Team & Timeline</h2>
          <div className="max-w-3xl mx-auto">
            <div className="space-y-0">
              {[
                { date: 'Jun 1', event: 'Project Kickoff' },
                { date: 'Jun 15', event: 'Model Training' },
                { date: 'Jun 30', event: 'Frontend Integration' },
                { date: 'Jul 5', event: 'Final Submission' }
              ].map((item, index) => (
                <div key={index} className="timeline-item">
                  <div className="timeline-date">{item.date}</div>
                  <div className="timeline-content">{item.event}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Contact & Footer */}
        <section className="walmart-section bg-muted/20">
          <h2 className="walmart-heading">📫 Next Steps</h2>
          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleFormSubmit} className="space-y-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium mb-2">Name *</label>
                <input 
                  type="text" 
                  id="name" 
                  name="name" 
                  required 
                  className="walmart-input"
                  aria-label="Your name"
                />
              </div>
              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2">Email *</label>
                <input 
                  type="email" 
                  id="email" 
                  name="email" 
                  required 
                  className="walmart-input"
                  aria-label="Your email address"
                />
              </div>
              <div>
                <label htmlFor="message" className="block text-sm font-medium mb-2">Message *</label>
                <textarea 
                  id="message" 
                  name="message" 
                  required 
                  className="walmart-textarea"
                  placeholder="Tell us about your interest in the Walmart Waste Predictor..."
                  aria-label="Your message"
                ></textarea>
              </div>
              <button type="submit" className="walmart-button w-full">
                Send Message
              </button>
            </form>
          </div>
        </section>

        {/* Footer */}
        <footer className="bg-[hsl(var(--sidebar-bg))] text-[hsl(var(--sidebar-foreground))] py-12">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <p className="text-lg mb-4">Built for Walmart Sparkathon 2025</p>
            <div className="flex items-center justify-center space-x-6">
              <a 
                href="https://github.com/your-repo/walmart-waste-predictor" 
                className="hover:text-blue-300 transition-colors flex items-center space-x-1"
                aria-label="GitHub repository"
              >
                <Github size={20} />
                <span>GitHub</span>
              </a>
              <a 
                href="mailto:team@walmart-waste-predictor.com" 
                className="hover:text-blue-300 transition-colors flex items-center space-x-1"
                aria-label="Send email"
              >
                <Mail size={20} />
                <span>Contact</span>
              </a>
            </div>
            <div className="mt-6 pt-6 border-t border-white/20">
              <p className="text-sm text-white/60">
                © 2025 Walmart Waste Predictor Team. Built with AI for a sustainable future.
              </p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default Index;
