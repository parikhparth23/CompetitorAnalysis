import { useEffect, useState } from 'react'
import './App.css'

interface Weakness {
  title: string
  description: string
  severity: 'high' | 'medium' | 'low'
  category: string
}

interface AnalysisResult {
  competitor_name: string
  target_url: string
  weaknesses: Weakness[]
  analyzed_at: string
  raw_content_length: number
}

function App() {
  const [competitorName, setCompetitorName] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [activeTab, setActiveTab] = useState<'analyze' | 'results' | 'faq'>('analyze')
  const [error, setError] = useState<string | null>(null)
  const [model, setModel] = useState<string>(() => {
    try {
      return localStorage.getItem('preferred_model') || 'gemini-2.5-flash-lite'
    } catch {
      return 'gemini-2.5-flash-lite'
    }
  })
  const [modelOptions, setModelOptions] = useState<Array<{id:string,name:string,daily:string,note?:string}>>([
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', daily: '20', note: 'Severely limited' },
    { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash-Lite', daily: '1,500', note: 'Recommended for Free Tier' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', daily: '0 - 5', note: 'Often removed or restricted' },
  ])

  const handleAnalyze = async () => {
    if (!competitorName.trim() || !targetUrl.trim()) {
      setError('Please fill in both competitor name and website URL')
      return
    }

    // Auto-complete URL if needed
    let processedUrl = targetUrl.trim()

    // Add protocol if missing
    if (!processedUrl.startsWith('http://') && !processedUrl.startsWith('https://')) {
      processedUrl = 'https://' + processedUrl
    }

    // Add www if it's just a domain without subdomain
    if (processedUrl.startsWith('https://') && !processedUrl.includes('.') && !processedUrl.includes('localhost')) {
      processedUrl = processedUrl.replace('https://', 'https://www.')
    } else if (processedUrl.startsWith('https://') && processedUrl.split('.').length === 2 && !processedUrl.includes('localhost')) {
      // If it's like "samsung.com", add www
      const domain = processedUrl.replace('https://', '')
      if (domain.split('.').length === 2) {
        processedUrl = 'https://www.' + domain
      }
    }

    // Validate the processed URL
    try {
      new URL(processedUrl)
    } catch {
      setError(`Invalid URL format. Please enter a valid website URL.`)
      return
    }

    // Update the targetUrl with the processed version if it was modified
    if (processedUrl !== targetUrl) {
      setTargetUrl(processedUrl)
      console.log(`URL auto-completed: ${targetUrl} → ${processedUrl}`)
    }

    setIsAnalyzing(true)
    setAnalysisResult(null)
    setError(null)

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          competitor_name: competitorName.trim(),
          target_url: targetUrl.trim(),
          model: model,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        setAnalysisResult(result)
        setActiveTab('results')
      } else {
        try {
          const errorData = await response.json()
          setError(`Analysis failed: ${errorData.detail || 'Unknown error'}`)
        } catch (e) {
          setError(`Analysis failed: HTTP ${response.status} ${response.statusText}`)
        }
      }
    } catch (error) {
      setError('Unable to connect to analysis service. Please check your connection.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleNewAnalysis = () => {
    setAnalysisResult(null)
    setCompetitorName('')
    setTargetUrl('')
    setError(null)
    // Rehydrate user's last selected model (defensive) so the analyze form
    // shows the same model the user had selected previously.
    try {
      const stored = localStorage.getItem('preferred_model')
      if (stored) setModel(stored)
    } catch {}

    setActiveTab('analyze')
  }

  const exportCSV = () => {
    if (!analysisResult) return
    const headers = ['#', 'Title', 'Description', 'Severity', 'Category']
    const rows = analysisResult.weaknesses.map((w, i) => [
      String(i + 1),
      w.title,
      w.description.replace(/\n/g, ' '),
      w.severity,
      w.category,
    ])
    const csvContent = [headers, ...rows].map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\n')
    const blob = new Blob(["\uFEFF" + csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const name = (analysisResult.competitor_name || 'analysis').replace(/[^a-z0-9\-_]/gi, '_')
    a.download = `${name}-report.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const exportPDF = async () => {
    if (!analysisResult) return
    try {
      const mod = await import('jspdf')
      const jsPDF = (mod && (mod.jsPDF || mod.default))
      if (!jsPDF) throw new Error('jsPDF not available')

      const doc = new jsPDF({ unit: 'pt', format: 'a4' })
      const margin = 40
      let y = margin
      const title = `Analysis Report — ${analysisResult.competitor_name}`
      doc.setFontSize(18)
      doc.text(title, margin, y)
      y += 24
      doc.setFontSize(11)
      doc.text(`Website: ${analysisResult.target_url}`, margin, y)
      y += 18
      doc.text(`Analyzed: ${new Date(analysisResult.analyzed_at).toLocaleString()}`, margin, y)
      y += 22
      doc.setLineWidth(0.5)
      doc.line(margin, y, doc.internal.pageSize.width - margin, y)
      y += 12

      analysisResult.weaknesses.forEach((w, i) => {
        if (y > doc.internal.pageSize.height - margin - 80) {
          doc.addPage()
          y = margin
        }
        doc.setFontSize(12)
        doc.text(`${i + 1}. ${w.title} [${w.severity.toUpperCase()}]`, margin, y)
        y += 16
        const lines = doc.splitTextToSize(w.description, doc.internal.pageSize.width - margin * 2)
        doc.setFontSize(10)
        doc.text(lines, margin, y)
        y += lines.length * 12 + 12
      })

      const name = (analysisResult.competitor_name || 'analysis').replace(/[^a-z0-9\-_]/gi, '_')
      doc.save(`${name}-report.pdf`)
    } catch (err) {
      // If jspdf isn't installed, instruct the developer
      // eslint-disable-next-line no-console
      console.error(err)
      alert('PDF export requires the `jspdf` package. Run `npm install jspdf` inside the frontend folder and restart the dev server.')
    }
  }

  useEffect(() => {
    // Fetch supported models from backend. If it fails, fallback to bundled list above.
    const init = async () => {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_BASE_URL}/models`)
        if (res.ok) {
          const data = await res.json()
          if (data && Array.isArray(data.models) && data.models.length > 0) {
            setModelOptions(data.models)
            // If user hasn't selected or stored a model, default to first server-provided
            try {
              const stored = localStorage.getItem('preferred_model')
              if (!stored) {
                setModel(data.models[0].id)
              }
            } catch {}
          }
        }
      } catch (e) {
        // ignore, keep defaults
      }
    }
    init()
  }, [])

  const handleModelChange = (id: string) => {
    setModel(id)
    try {
      localStorage.setItem('preferred_model', id)
    } catch {}
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo">
              <span className="logo-icon">🎯</span>
              <h1>Competitor Analysis Pro</h1>
            </div>
            <p className="tagline">AI-Powered Competitive Intelligence</p>
          </div>
          <nav className="nav">
            <button
              className={`nav-btn ${activeTab === 'analyze' ? 'active' : ''}`}
              onClick={() => setActiveTab('analyze')}
            >
              🔍 Analyze
            </button>
            <button
              className={`nav-btn ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
              disabled={!analysisResult}
            >
              📊 Results
            </button>
            <button
              className={`nav-btn ${activeTab === 'faq' ? 'active' : ''}`}
              onClick={() => setActiveTab('faq')}
            >
              ❓ FAQ
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {activeTab === 'analyze' && (
          <div className="analyze-section">
            <div className="hero">
              <h2>Discover Your Competitors' Weaknesses</h2>
              <p>
                Use AI-powered analysis to identify competitive advantages and opportunities.
                Simply enter a competitor's name and website URL to get detailed insights.
              </p>
            </div>

            <div className="analysis-form">
              <div className="model-select" style={{ marginBottom: '1rem' }}>
                <label htmlFor="model" style={{ display: 'block', marginBottom: '.5rem', fontWeight: 600 }}>Model</label>
                <select
                  id="model"
                  value={model}
                  onChange={(e) => handleModelChange(e.target.value)}
                >
                  {modelOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name} · {opt.daily}/day — {opt.note}
                    </option>
                  ))}
                </select>
                <small>
                  Selected model affects rate limits; choose a free-tier friendly model when needed.
                </small>
              </div>
              <div className="form-group">
                <label htmlFor="competitor-name">
                  <span className="label-icon">🏢</span>
                  Competitor Name
                </label>
                <input
                  id="competitor-name"
                  type="text"
                  placeholder="e.g., Apple, Microsoft, Google"
                  value={competitorName}
                  onChange={(e) => setCompetitorName(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="target-url">
                  <span className="label-icon">🌐</span>
                  Website URL
                </label>
                <input
                  id="target-url"
                  type="text"
                  placeholder="e.g., samsung.com or https://apple.com"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className="form-input"
                />
              </div>

              {error && (
                <div className="error-message">
                  <span className="error-icon">⚠️</span>
                  {error}
                </div>
              )}

              <div className="analyze-actions">
                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className={`analyze-btn ${isAnalyzing ? 'loading' : ''}`}
                >
                  {isAnalyzing ? (
                    <>
                      <span className="spinner"></span>
                      Analyzing...
                    </>
                  ) : (
                    <>
                      🚀 Start Analysis
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="features">
              <div className="feature-card">
                <div className="feature-icon">🤖</div>
                <h3>AI-Powered Analysis</h3>
                <p>Advanced AI identifies weaknesses across pricing, features, support, and more</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">⚡</div>
                <h3>Fast & Accurate</h3>
                <p>Get comprehensive insights in seconds, not hours of manual research</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🎯</div>
                <h3>Actionable Intelligence</h3>
                <p>Receive specific, actionable recommendations to gain competitive advantage</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">📈</div>
                <h3>Custom Reports</h3>
                <p>Export tailored PDF and CSV reports to share findings with stakeholders.</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'results' && analysisResult && (
          <div className="results-section">
            <div className="results-header">
              <h2>Analysis Results for {analysisResult.competitor_name}</h2>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button onClick={exportCSV} className="export-btn" type="button">⬇️ Export CSV</button>
                <button onClick={exportPDF} className="export-btn" type="button">📄 Export PDF</button>
                <button onClick={handleNewAnalysis} className="new-analysis-btn">
                  🔄 New Analysis
                </button>
              </div>
            </div>

            <div className="results-summary">
              <div className="summary-card">
                <div className="summary-icon">🌐</div>
                <div className="summary-content">
                  <h4>Website</h4>
                  <p>{analysisResult.target_url}</p>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon">📄</div>
                <div className="summary-content">
                  <h4>Content Analyzed</h4>
                  <p>{analysisResult.raw_content_length.toLocaleString()} characters</p>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon">⏰</div>
                <div className="summary-content">
                  <h4>Analysis Date</h4>
                  <p>{new Date(analysisResult.analyzed_at).toLocaleString()}</p>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-icon">🎯</div>
                <div className="summary-content">
                  <h4>Weaknesses Found</h4>
                  <p className="weakness-count">{analysisResult.weaknesses.length}</p>
                </div>
              </div>
            </div>

            <div className="weaknesses-section">
              <h3>Identified Weaknesses ({analysisResult.weaknesses.length}):</h3>
              <div className="weaknesses-grid">
                {analysisResult.weaknesses.map((weakness, index) => (
                  <div
                    key={index}
                    className={`weakness-card severity-${weakness.severity}`}
                  >
                    <div className="weakness-header">
                      <h4>{index + 1}. {weakness.title}</h4>
                      <div className="weakness-badges">
                        <span className={`severity-badge severity-${weakness.severity}`}>
                          {weakness.severity.toUpperCase()}
                        </span>
                        <span className="category-badge">
                          {weakness.category}
                        </span>
                      </div>
                    </div>
                    <p className="weakness-description">{weakness.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'faq' && (
          <div className="faq-section">
            <h2>Frequently Asked Questions</h2>

            <div className="faq-grid">
              <div className="faq-card">
                <h4>🔍 How does the analysis work?</h4>
                <p>
                  Our AI-powered system scrapes your competitor's website content, analyzes it using
                  advanced machine learning, and identifies potential weaknesses and opportunities
                  across multiple business dimensions.
                </p>
              </div>

              <div className="faq-card">
                <h4>⏱️ How long does analysis take?</h4>
                <p>
                  Most analyses complete in 30-60 seconds. The time depends on the website size
                  and complexity of the content being analyzed.
                </p>
              </div>

              <div className="faq-card">
                <h4>🎯 What types of weaknesses are identified?</h4>
                <p>
                  We analyze pricing strategies, product features, customer support quality,
                  user experience issues, technical limitations, and market positioning gaps.
                </p>
              </div>

              <div className="faq-card">
                <h4>🌐 Which websites can be analyzed?</h4>
                <p>
                  Most corporate and business websites work well. Social media platforms
                  (Twitter, Facebook, Reddit) and heavily protected sites may not be accessible
                  due to their anti-scraping measures.
                </p>
              </div>

              <div className="faq-card">
                <h4>🔒 Is my data secure?</h4>
                <p>
                  All analysis happens in real-time and data is not stored permanently.
                  We only process the information needed for the competitive analysis.
                </p>
              </div>

              <div className="faq-card">
                <h4>💰 How much does it cost?</h4>
                <p>
                  Currently free for basic analysis. Enterprise plans with advanced features
                  and unlimited analyses are available upon request.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <p>&copy; 2025 Competitor Analysis Pro. Powered by AI for business intelligence.</p>
          <div className="footer-links">
            <a href="#privacy">Privacy Policy</a>
            <a href="#terms">Terms of Service</a>
            <a href="#contact">Contact Us</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
