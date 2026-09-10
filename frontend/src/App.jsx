import { useCallback, useEffect, useState } from "react";

// En dev pega directo al backend local; en producción (o dentro de Tauri)
// esto debería venir de una variable de entorno de build, no hardcodeado.
const API_BASE = "http://localhost:8000";
const CUSTOMER_ID = "cust_1"; // cliente de ejemplo que trae el mock

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // useCallback ANTES del useEffect que lo usa — si no, loadAccounts todavía
  // no existe cuando el useEffect trata de referenciarlo (ver README del
  // framework: "React Hook Order Pattern").
  const loadAccounts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/accounts/customer/${CUSTOMER_ID}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAccounts(data);
      if (data.length > 0) setSelectedAccount(data[0].id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTransactions = useCallback(async (accountId) => {
    if (!accountId) return;
    const res = await fetch(`${API_BASE}/accounts/${accountId}/transactions`);
    const data = await res.json();
    setTransactions(data);
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  useEffect(() => {
    loadTransactions(selectedAccount);
  }, [selectedAccount, loadTransactions]);

  const simulatePurchase = async () => {
    await fetch(`${API_BASE}/accounts/${selectedAccount}/transactions/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merchant_id: "demo_merchant",
        amount: Math.round(Math.random() * 500 * 100) / 100,
        description: "Compra simulada (demo)",
      }),
    });
    loadTransactions(selectedAccount);
  };

  if (loading) return <p style={{ padding: 24 }}>Cargando…</p>;
  if (error) {
    return (
      <p style={{ padding: 24, color: "crimson" }}>
        No pude conectar al backend ({error}). ¿Corriste{" "}
        <code>uvicorn app.main:app --reload</code> en <code>backend/</code>?
      </p>
    );
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24, maxWidth: 640 }}>
      <h1>HackMTY 2026 — Capital One</h1>
      <p style={{ color: "#666" }}>
        Starter conectado al backend. Reemplaza esta pantalla por la idea real
        del equipo — lo que importa es que ya hay datos de Nessie (o del
        mock) fluyendo de punta a punta.
      </p>

      <h2>Cuentas</h2>
      <ul>
        {accounts.map((acc) => (
          <li
            key={acc.id}
            style={{
              cursor: "pointer",
              fontWeight: acc.id === selectedAccount ? "bold" : "normal",
            }}
            onClick={() => setSelectedAccount(acc.id)}
          >
            {acc.nickname ?? acc.type} — ${acc.balance.toLocaleString()}
          </li>
        ))}
      </ul>

      <h2>Transacciones</h2>
      <button onClick={simulatePurchase}>Simular compra (demo en vivo)</button>
      <ul>
        {transactions.map((tx) => (
          <li key={tx.id}>
            {tx.date} — {tx.description} — ${tx.amount.toLocaleString()} ({tx.type})
          </li>
        ))}
      </ul>
    </div>
  );
}
