const { useState, useEffect, useMemo, useCallback } = React;

function App() {
  const [unlocked, setUnlocked] = useState(false);
  const [masterSet, setMasterSet] = useState(false);
  const [activeTab, setActiveTab] = useState("vault");
  const [accounts, setAccounts] = useState([]);
  const [stats, setStats] = useState({ total_accounts: 0, overdue_count: 0, weak_passwords: 0, security_score: 100 });
  const [searchQuery, setSearchQuery] = useState("");
  const [toastMsg, setToastMsg] = useState("");
  const [visiblePasswords, setVisiblePasswords] = useState({});

  // Auth inputs
  const [masterPassword, setMasterPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [authError, setAuthError] = useState("");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalService, setModalService] = useState("");
  const [modalUsername, setModalUsername] = useState("");
  const [modalPassword, setModalPassword] = useState("");
  const [isEditMode, setIsEditMode] = useState(false);

  // Generator State
  const [genLength, setGenLength] = useState(16);
  const [genUpper, setGenUpper] = useState(true);
  const [genLower, setGenLower] = useState(true);
  const [genDigits, setGenDigits] = useState(true);
  const [genSymbols, setGenSymbols] = useState(true);
  const [generatedPass, setGeneratedPass] = useState("");
  const [genStrength, setGenStrength] = useState({ score: 0, label: "Weak", color: "#EF4444" });

  // Initial status fetch
  const checkStatus = async () => {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      setMasterSet(data.master_set);
      setUnlocked(data.unlocked);
      if (data.unlocked) fetchAccounts();
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const fetchAccounts = async () => {
    try {
      const res = await fetch("/api/accounts");
      const data = await res.json();
      if (data.success) {
        setAccounts(data.accounts);
        setStats(data.stats);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(""), 2200);
  };

  const copyToClipboard = (text, msg) => {
    navigator.clipboard.writeText(text);
    showToast(msg);
  };

  // Toggle Password Visibility inside card
  const togglePassVisibility = (service) => {
    setVisiblePasswords(prev => ({
      ...prev,
      [service]: !prev[service]
    }));
  };

  // Auth Handling
  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError("");

    if (!masterSet) {
      if (masterPassword !== confirmPassword) {
        setAuthError("Passwords do not match!");
        return;
      }
      if (masterPassword.length < 6) {
        setAuthError("Password must be at least 6 characters.");
        return;
      }

      const res = await fetch("/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: masterPassword })
      });
      const data = await res.json();
      if (data.success) {
        setUnlocked(true);
        setMasterSet(true);
        fetchAccounts();
        showToast("Vault created successfully!");
      } else {
        setAuthError(data.error);
      }
    } else {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: masterPassword })
      });
      const data = await res.json();
      if (data.success) {
        setUnlocked(true);
        fetchAccounts();
        showToast("Vault unlocked!");
      } else {
        setAuthError(data.error);
      }
    }
  };

  const lockVault = async () => {
    await fetch("/api/lock", { method: "POST" });
    setUnlocked(false);
    setMasterPassword("");
    setConfirmPassword("");
    showToast("Vault Locked");
  };

  // Save Account
  const handleSaveAccount = async (e) => {
    e.preventDefault();
    if (!modalService || !modalUsername || !modalPassword) {
      alert("Please fill in all fields.");
      return;
    }

    const res = await fetch("/api/account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service: modalService,
        username: modalUsername,
        password: modalPassword,
        is_edit: isEditMode
      })
    });
    const data = await res.json();
    if (data.success) {
      setIsModalOpen(false);
      fetchAccounts();
      showToast(data.message);
    } else {
      alert(data.error);
    }
  };

  const handleDeleteAccount = async (service) => {
    if (confirm(`Delete account for '${service}'?`)) {
      const res = await fetch(`/api/account/${service}`, { method: "DELETE" });
      const data = await res.json();
      if (data.success) {
        fetchAccounts();
        showToast(data.message);
      }
    }
  };

  const openAddModal = () => {
    setModalService("");
    setModalUsername("");
    setModalPassword("");
    setIsEditMode(false);
    setIsModalOpen(true);
  };

  const openEditModal = (acc) => {
    setModalService(acc.service);
    setModalUsername(acc.username);
    setModalPassword(acc.password);
    setIsEditMode(true);
    setIsModalOpen(true);
  };

  // Generator Logic
  const handleGeneratePassword = async () => {
    const res = await fetch("/api/generate-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        length: genLength,
        upper: genUpper,
        lower: genLower,
        digits: genDigits,
        symbols: genSymbols
      })
    });
    const data = await res.json();
    setGeneratedPass(data.password);
    setGenStrength(data.strength);
  };

  useEffect(() => {
    if (activeTab === "generator") handleGeneratePassword();
  }, [activeTab, genLength, genUpper, genLower, genDigits, genSymbols]);

  // Filtered Accounts
  const filteredAccounts = useMemo(() => {
    return accounts.filter(acc =>
      acc.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
      acc.username.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [accounts, searchQuery]);

  // If locked, render Auth view
  if (!unlocked) {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          <div className="brand-icon" style={{ margin: "0 auto 16px auto", width: "56px", height: "56px", fontSize: "28px" }}>🔐</div>
          <h1 className="auth-title" style={{ marginBottom: "24px" }}>VaultGuard</h1>

          <form onSubmit={handleAuth}>
            <div className="form-group">
              <label className="form-label">{masterSet ? "Master Password" : "Create Master Password"}</label>
              <input
                type="password"
                className="form-input"
                placeholder="Enter master password"
                value={masterPassword}
                onChange={(e) => setMasterPassword(e.target.value)}
                autoFocus
              />
            </div>

            {!masterSet && (
              <div className="form-group">
                <label className="form-label">Confirm Master Password</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            )}

            {authError && <p style={{ color: "#EF4444", fontSize: "12px", marginBottom: "12px" }}>{authError}</p>}

            <button type="submit" className="btn-primary">
              {masterSet ? "UNLOCK VAULT" : "CREATE VAULT"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* 1. SIDEBAR */}
      <aside className="sidebar">
        <div>
          <div className="brand-header">
            <div className="brand-icon">🔐</div>
            <div>
              <h2 className="brand-title">VaultGuard</h2>
              <div className="status-badge">
                <span className="status-pulse"></span> Vault Unlocked
              </div>
            </div>
          </div>

          <nav className="nav-menu">
            <button className={`nav-item ${activeTab === "vault" ? "active" : ""}`} onClick={() => setActiveTab("vault")}>
              <span>📦</span> Accounts Vault
            </button>
            <button className={`nav-item ${activeTab === "generator" ? "active" : ""}`} onClick={() => setActiveTab("generator")}>
              <span>⚡</span> Password Generator
            </button>
            <button className={`nav-item ${activeTab === "audit" ? "active" : ""}`} onClick={() => setActiveTab("audit")}>
              <span>🔔</span> Security Audit {stats.overdue_count > 0 && <span className="badge badge-due" style={{ marginLeft: "auto" }}>{stats.overdue_count} Overdue</span>}
            </button>
          </nav>
        </div>

        <div>
          <div className="sidebar-card">
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontWeight: "700" }}>
              <span style={{ color: "var(--text-muted)" }}>Vault Health</span>
              <span style={{ color: "var(--accent-success)" }}>{stats.security_score}%</span>
            </div>
            <div className="health-bar-container">
              <div className="health-bar-fill" style={{ width: `${stats.security_score}%`, backgroundColor: stats.security_score >= 75 ? "#10B981" : "#F59E0B" }}></div>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>{stats.total_accounts} Total Stored Items</p>
          </div>

          <button className="lock-btn" onClick={lockVault}>
            🔒 Lock Vault
          </button>
        </div>
      </aside>

      {/* 2. MAIN CONTENT AREA */}
      <main className="main-content">
        {activeTab === "vault" && (
          <div>
            <div className="toolbar">
              <div className="search-input-wrapper">
                <span className="search-icon">🔍</span>
                <input
                  type="text"
                  className="form-input search-input"
                  placeholder="Search accounts by service or username..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button className="btn-primary" style={{ width: "auto", padding: "0 24px" }} onClick={openAddModal}>
                ➕ Add Account
              </button>
            </div>

            <div className="account-list">
              {filteredAccounts.length === 0 ? (
                <div className="sidebar-card" style={{ textAlign: "center", padding: "40px" }}>
                  <p style={{ color: "var(--text-muted)", fontWeight: "600" }}>📭 No accounts found in your vault.</p>
                </div>
              ) : (
                filteredAccounts.map((acc) => {
                  const isPassRevealed = visiblePasswords[acc.service];
                  return (
                    <div key={acc.service} className="account-card">
                      <div style={{ display: "flex", alignItems: "center" }}>
                        <div className="avatar">{acc.service[0].toUpperCase()}</div>
                        <div className="account-details">
                          <div className="account-title-row">
                            <h3 className="service-name">{acc.service}</h3>
                            <span className={`badge badge-${acc.status.level}`}>
                              {acc.status.badge_text}
                            </span>
                          </div>
                          <p className="account-meta">👤 {acc.username}</p>

                          {/* Show/Hide Password Toggle Line inside Card */}
                          <div className="password-row">
                            <span className={`password-text ${isPassRevealed ? "revealed" : ""}`}>
                              🔑 {isPassRevealed ? acc.password : "••••••••••••"}
                            </span>
                            <button
                              className={`btn-toggle-pass ${isPassRevealed ? "active" : ""}`}
                              onClick={() => togglePassVisibility(acc.service)}
                            >
                              {isPassRevealed ? "🙈 Hide" : "👁️ Show"}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="action-group">
                        <button className="btn-sm btn-copy-pass" onClick={() => copyToClipboard(acc.password, "Password copied to clipboard!")}>
                          📋 Password
                        </button>
                        <button className="btn-sm btn-copy-user" onClick={() => copyToClipboard(acc.username, "Username copied!")}>
                          👤 User
                        </button>
                        <button className="btn-sm btn-icon" onClick={() => openEditModal(acc)}>✏️</button>
                        <button className="btn-sm btn-danger" onClick={() => handleDeleteAccount(acc.service)}>🗑️</button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* TAB 2: PASSWORD GENERATOR */}
        {activeTab === "generator" && (
          <div className="sidebar-card" style={{ maxWidth: "600px", margin: "0 auto", padding: "30px" }}>
            <h2 style={{ fontSize: "22px", fontWeight: "800", marginBottom: "4px" }}>⚡ Password Generator</h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "20px" }}>Generate cryptographically strong passwords.</p>

            <div className="form-input" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", padding: "16px" }}>
              <span style={{ fontFamily: "monospace", fontSize: "18px", fontWeight: "700", color: "var(--accent-primary)" }}>{generatedPass}</span>
              <button className="btn-sm btn-copy-pass" onClick={() => copyToClipboard(generatedPass, "Generated password copied!")}>📋 Copy</button>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontWeight: "700", marginBottom: "4px" }}>
                <span style={{ color: "var(--text-muted)" }}>Strength</span>
                <span style={{ color: genStrength.color }}>{genStrength.label} ({genStrength.score}%)</span>
              </div>
              <div className="health-bar-container">
                <div className="health-bar-fill" style={{ width: `${genStrength.score}%`, backgroundColor: genStrength.color }}></div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Length: {genLength} characters</label>
              <input type="range" min="8" max="48" value={genLength} onChange={(e) => setGenLength(parseInt(e.target.value))} style={{ width: "100%" }} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "20px" }}>
              <label style={{ fontSize: "13px" }}><input type="checkbox" checked={genUpper} onChange={(e) => setGenUpper(e.target.checked)} /> Uppercase (A-Z)</label>
              <label style={{ fontSize: "13px" }}><input type="checkbox" checked={genLower} onChange={(e) => setGenLower(e.target.checked)} /> Lowercase (a-z)</label>
              <label style={{ fontSize: "13px" }}><input type="checkbox" checked={genDigits} onChange={(e) => setGenDigits(e.target.checked)} /> Digits (0-9)</label>
              <label style={{ fontSize: "13px" }}><input type="checkbox" checked={genSymbols} onChange={(e) => setGenSymbols(e.target.checked)} /> Symbols (!@#$)</label>
            </div>

            <button className="btn-primary" onClick={handleGeneratePassword}>🔄 Generate New Password</button>
          </div>
        )}

        {/* TAB 3: SECURITY AUDIT */}
        {activeTab === "audit" && (
          <div style={{ maxWidth: "700px", margin: "0 auto" }}>
            <div className="sidebar-card" style={{ padding: "24px", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: "800", marginBottom: "4px" }}>🔔 Password Rotation Audit</h2>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Passwords older than 120 days should be rotated to maintain high security.</p>
            </div>

            {accounts.filter(a => ["due", "overdue", "warning"].includes(a.status.level)).map(acc => (
              <div key={acc.service} className="account-card" style={{ borderColor: "rgba(239, 68, 68, 0.4)", background: "rgba(239, 68, 68, 0.05)" }}>
                <div>
                  <h4 style={{ fontWeight: "700", fontSize: "15px" }}>🔑 {acc.service}</h4>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Last changed {acc.status.days_passed} days ago</p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`badge badge-${acc.status.level}`}>{acc.status.badge_text}</span>
                  <button className="btn-sm btn-copy-pass" onClick={() => openEditModal(acc)}>Update Now</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* MODAL DIALOG */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ fontSize: "18px", fontWeight: "800", marginBottom: "20px" }}>{isEditMode ? "Edit Account" : "Add Account"}</h3>
            <form onSubmit={handleSaveAccount}>
              <div className="form-group">
                <label className="form-label">Service Name</label>
                <input type="text" className="form-input" placeholder="Google, Netflix" value={modalService} onChange={(e) => setModalService(e.target.value)} disabled={isEditMode} />
              </div>
              <div className="form-group">
                <label className="form-label">Username / Email</label>
                <input type="text" className="form-input" placeholder="user@gmail.com" value={modalUsername} onChange={(e) => setModalUsername(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input type="password" className="form-input" placeholder="Password" value={modalPassword} onChange={(e) => setModalPassword(e.target.value)} />
              </div>
              <div style={{ display: "flex", gap: "10px", marginTop: "24px" }}>
                <button type="button" className="btn-sm btn-copy-user" style={{ flex: 1, padding: "12px" }} onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" style={{ flex: 1 }}>Save Account</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TOAST NOTIFICATION */}
      {toastMsg && <div className="toast">✅ {toastMsg}</div>}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
