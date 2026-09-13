-- 004_financial_views.sql
-- Vistas derivadas del diario. El diario (journal_entries + journal_lines) es
-- la única verdad contable; estas vistas NO se editan ni se materializan.
-- Portables: mismo SQL en Snowflake y sqlite.

-- Libro mayor: cada línea del diario con su cuenta y encabezado.
CREATE VIEW IF NOT EXISTS v_general_ledger AS
SELECT
  l.business_id,
  e.entry_id,
  e.transaction_number,
  e.entry_date,
  e.description,
  e.source_type,
  e.source_id,
  e.is_adjusting,
  l.line_id,
  l.line_order,
  a.account_id,
  a.account_number,
  a.account_name,
  a.account_type,
  a.account_subtype,
  a.normal_balance,
  a.financial_statement,
  l.debit,
  l.credit,
  l.memo
FROM journal_lines l
JOIN journal_entries e ON e.entry_id = l.entry_id AND e.business_id = l.business_id
JOIN accounts a ON a.account_id = l.account_id AND a.business_id = l.business_id
WHERE e.status = 'POSTED';

-- Saldos por cuenta (balanza de comprobación acumulada, ajustada).
CREATE VIEW IF NOT EXISTS v_account_balances AS
SELECT
  a.business_id,
  a.account_id,
  a.account_number,
  a.account_name,
  a.account_type,
  a.account_subtype,
  a.normal_balance,
  a.financial_statement,
  COALESCE(SUM(g.debit), 0)  AS total_debits,
  COALESCE(SUM(g.credit), 0) AS total_credits,
  CASE WHEN a.normal_balance = 'DEBIT'
       THEN COALESCE(SUM(g.debit), 0) - COALESCE(SUM(g.credit), 0)
       ELSE COALESCE(SUM(g.credit), 0) - COALESCE(SUM(g.debit), 0)
  END AS balance
FROM accounts a
LEFT JOIN v_general_ledger g ON g.account_id = a.account_id AND g.business_id = a.business_id
GROUP BY a.business_id, a.account_id, a.account_number, a.account_name, a.account_type,
         a.account_subtype, a.normal_balance, a.financial_statement;
