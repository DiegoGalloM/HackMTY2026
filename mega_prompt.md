# CAPITAL ONE BUSINESS — HACKMTY 2026
## Full Product, Accounting, Data, Financial Intelligence, and AI Implementation

You are the **lead senior full-stack engineer, financial-systems architect, product engineer, database architect, and AI engineer** responsible for completing an existing HackMTY 2026 project called **Capital One Business**.

This is not a planning exercise.

Your responsibility is to inspect the existing repository, understand how the current application works, design the minimum coherent extensions required by this specification, **implement them into the existing project, run and test the application, verify frontend ↔ backend ↔ Snowflake connectivity, repair integration problems, and continue until the requested product flows work end-to-end**.

Do not stop after producing recommendations, architecture diagrams, SQL schemas, components, endpoints, or pseudocode.

A feature is not complete merely because its individual files exist.

A feature is complete only when its full user flow works through the actual application.

---

# 1. PRODUCT CONTEXT

The product is called **Capital One Business**.

It is being built for the **Capital One challenge at HackMTY 2026**, focused on SMB cash-flow and working-capital intelligence.

The intended customer is not a professional accountant or CFO.

The primary customer is a **nano/micro-business owner**, usually around 1–5 people, potentially someone turning a hobby, side hustle, informal activity, or small service operation into a business.

Examples include:

- home bakeries;
- food vendors;
- beauty businesses;
- small retail sellers;
- service businesses;
- construction contractors;
- transportation businesses;
- online or hobby sellers.

These users may know almost nothing about accounting.

The central product philosophy is:

> **The owner should run the business. Capital One Business should quietly handle the financial complexity underneath.**

The user should not have to understand debits, credits, journals, ledgers, trial balances, inventory accounting, liquidity ratios, or working capital in order to benefit from them.

Professional accounting rigor should exist underneath an extremely simple user experience.

---

# 2. CORE PRODUCT PROMISE

The intended experience can be summarized as:

> **Use your business card for business purchases. Sell through Capital One Business. We automatically organize your inventory, books, financial statements, financial health, and business intelligence—and you can ask your business questions in plain English.**

The system should transform everyday business activity into structured financial intelligence.

Conceptually:

```text
Business activity
      ↓
Automatic data capture
      ↓
Business events
      ↓
Inventory + accounting consequences
      ↓
Journal
      ↓
General Ledger
      ↓
Trial Balance
      ↓
Financial Statements
      ↓
Financial Ratios / Cash-Flow Intelligence
      ↓
AI interpretation
      ↓
Natural-language financial assistant
```

The application should feel simple even though this architecture is sophisticated.

---

# 3. EXISTING PROJECT — INSPECT BEFORE MODIFYING

Before making substantial changes:

1. Inspect the entire repository.
2. Read the existing project-context and architecture documentation if present.
3. Inspect the actual source code rather than trusting potentially stale documentation.
4. Inspect the current Snowflake schema/migrations.
5. Trace the current frontend routes and component hierarchy.
6. Trace the backend routers, services, Pydantic models, storage abstractions, environment configuration, and external-provider abstractions.
7. Inspect the current tests and deployment configuration.
8. Run the current test/build commands when practical to establish a baseline.
9. Identify which existing abstractions should be preserved versus refactored.

The repository has historically contained approximately this architecture:

```text
Frontend
React 19
Vite
React Router
Framer Motion
Tailwind
Mixed TS/JS

Backend
FastAPI
Pydantic
Python
httpx

Storage
MemoryProfileStore
SnowflakeProfileStore

Bank/demo provider
NessieClient
MockNessieClient
RealNessieClient

Existing domains
Business onboarding
Business profiles
Bank/accounts/transactions
Financial education
Main banking-style screens
Analysis screen
```

There may be differences in the live repository by the time you receive this task.

**The live source code is authoritative.**

Do not blindly reproduce outdated project-context observations.

Re-verify them.

---

# 4. EXISTING BUSINESS PROFILE

The current onboarding collects business context such as:

```text
Business category
Category detail
Operating days
City
Employee range
Yes/no business questions
Description of a normal business week
Potentially text/audio description
Inventory-related information
Business behavior/context
```

This information is important.

Do not treat onboarding as an isolated survey.

Use it to improve:

- account creation;
- chart-of-accounts templates;
- transaction classification;
- inventory configuration;
- financial explanations;
- financial recommendations;
- AI answers;
- business-specific contextual education.

---

# 5. EXPERIENCE PRINCIPLE: OUTCOMES FIRST, ACCOUNTING SECOND

The average user should usually see:

```text
You sold $84 today.

Your estimated gross profit was $37.

Inventory was updated automatically.

Cash health: Good.
```

rather than:

```text
Debit Cash
Credit Revenue
Debit COGS
Credit Inventory

Current Ratio = 1.34
```

The accounting details must exist and be available in appropriate advanced financial views, but they should not be the default mental model.

The normal user's mental model should be:

```text
I purchased something.
I sold something.
The app handled the rest.
```

Never force a normal user to choose:

- debit versus credit;
- accounting statement;
- ledger posting;
- account number;
- accounting treatment,

unless there is genuinely no safer or simpler way to resolve ambiguity.

Even ambiguity resolution should use plain business language.

For example:

```text
What was this Amazon purchase for?

[ Inventory ]
[ Equipment ]
[ Regular business expense ]
[ Personal purchase ]
```

is preferable to:

```text
Choose debit account.
```

---

# 6. UI/UX INTEGRATION REQUIREMENT

Do not bolt the new functionality onto the app as unrelated pages.

First understand the existing navigation, information architecture, visual language, interaction patterns, mobile layout, and user journey.

Then determine where the new functionality belongs naturally.

Preserve the visual identity of the existing product.

The user should feel that these capabilities were always intended to be part of the application.

Likely conceptual areas include:

```text
Home / Account
Sell
Transactions
Inventory
Analysis / Financial Health
Education
Financials / Books
AI Assistant
```

Do not treat those names as mandatory.

Choose navigation and information architecture based on the actual existing UI.

The product should remain easy enough for someone who does not know finance.

---

# 7. CRITICAL DEFINITION OF DONE

Throughout this task, use this rule:

> **Existing code is not the same as working functionality.**

For every feature, verify the entire chain.

For example, QR selling is NOT complete when a QR component renders.

It is complete when:

```text
Owner defines product/service
        ↓
Data persists
        ↓
Owner selects item
        ↓
Sale/order is created
        ↓
QR represents that specific order
        ↓
Customer can open checkout
        ↓
Payment can be completed or convincingly simulated
        ↓
Backend receives authoritative payment-success event
        ↓
Order becomes paid
        ↓
Inventory is updated
        ↓
Journal entries are generated
        ↓
Journal validation succeeds
        ↓
Ledger reflects it
        ↓
Financial statements reflect it
        ↓
Ratios/analytics reflect it
        ↓
Frontend updates correctly
        ↓
Financial assistant can answer questions about it
```

If an arrow is broken, the feature is unfinished.

---

# 8. DATA-SOURCE PHILOSOPHY

Do not make Nessie the foundation of the financial system.

Nessie is useful as a demo/fake transaction source and potentially as one implementation of a transaction-provider interface.

Its account types and data should not constrain the accounting architecture.

Prefer a provider abstraction conceptually similar to:

```text
TransactionProvider

├── NessieTransactionProvider
├── DemoTransactionProvider
└── FutureBankTransactionProvider
```

The financial system should operate on normalized internal business events, not directly on Nessie-specific structures.

If realistic live banking connectivity is unavailable during the hackathon, implement a convincing demo provider capable of generating the same normalized events.

**Demo reliability outranks dependence on fragile external services.**

---

# 9. AUTOMATIC BUSINESS-CARD DATA CAPTURE

The intended product promise is that the owner uses a dedicated business card for business purchases.

Those transactions should automatically enter the system.

A card/bank transaction can reliably provide information such as:

```text
transaction ID
amount
merchant
date/time
direction
description
possible merchant/category metadata
payment/account information
```

It does NOT necessarily identify individual receipt items.

Do not pretend that it does.

Keep raw card transactions distinct from interpreted accounting events.

A raw transaction represents:

> what the system observed.

A journal entry represents:

> what the system concluded happened financially.

Preserve that separation.

---

# 10. RECEIPT ENRICHMENT

Support an architecture through which purchases can optionally be enriched by receipt information.

Example:

```text
Card transaction
Restaurant Depot
$486.28
        ↓
Receipt attached / matched
        ↓
Extracted receipt items
Chicken
Rice
Oil
...
        ↓
Inventory update
        ↓
More confident accounting classification
```

If receipt OCR/vision can be implemented reliably within available infrastructure, implement it.

Otherwise create the data model/provider boundary and an excellent deterministic demo path using sample receipt data.

Do not allow optional OCR complexity to jeopardize the primary demo.

The goal is to demonstrate that receipt-level detail can improve:

- inventory;
- COGS;
- purchase classification;
- accounting confidence.

---

# 11. SELLING SYSTEM

Implement a natural **Sell** experience for the owner.

The user must be able to create reusable products and services.

The owner should configure an item once rather than rebuilding its accounting/inventory configuration during every sale.

Conceptually:

```text
SELLABLE ITEM

Name
Description
Type: Product / Service
Selling price
Tax configuration if applicable
Active/inactive
Optional image
Inventory/resource requirements
```

Products may consume inventory resources.

Services may consume no inventory, although services must be allowed to consume materials when appropriate.

For example:

```text
Haircut
$35
No resources
```

versus:

```text
Hair Coloring
$120

Resources:
120 ml dye
2 gloves
```

Do not create completely separate systems if one generalized sellable-item model is cleaner.

---

# 12. BILL OF MATERIALS / RECIPE MODEL

Products should support a bill of materials / recipe.

Example:

```text
Chocolate Cake

Selling price:
$25

Recipe:
Flour       0.50 kg
Eggs        4 units
Chocolate   0.25 kg
Sugar       0.20 kg
```

This relationship must be persisted.

When two cakes are sold:

```text
Flour       -1.00 kg
Eggs        -8 units
Chocolate   -0.50 kg
Sugar       -0.40 kg
```

The owner should not manually record these deductions after every sale.

This is one of the core automation features of the product.

---

# 13. QR SALES FLOW

When the owner wants to sell something:

1. Open the Sell experience.
2. Select one or more predefined product/service items.
3. Select quantity.
4. Review total.
5. Create an order.
6. Generate a QR representing that specific order.

The QR must NOT merely represent an editable payment amount.

It represents an already-defined sale/order.

Conceptually:

```text
ORDER ORD-1847

2 × Chocolate Cake
Total $50
Status AWAITING_PAYMENT
```

The QR may resolve to something conceptually like:

```text
/pay/<opaque-order-token>
```

The customer scans it.

The customer should NOT need to manually specify:

- what they are purchasing;
- transaction amount;
- merchant;
- item names.

That information was defined by the seller.

The customer experience should be approximately:

```text
Maria's Bakery

2 × Chocolate Cake

Total
$50.00

[ Pay $50 ]
```

Keep the customer checkout friction extremely low.

---

# 14. CUSTOMER INFORMATION

Do not assume scanning a QR automatically identifies a customer.

Capture only customer information legitimately available through the checkout/payment flow or voluntarily provided where appropriate.

Support:

```text
Known customer
Newly identified customer
Guest / anonymous customer
```

Customer identity should not be required for completing a normal sale unless the payment provider genuinely requires something.

Where customer identity is available, create useful business intelligence such as:

```text
first purchase
last purchase
purchase count
lifetime revenue
average order value
products purchased
purchase frequency
```

Avoid unnecessary storage of sensitive payment information.

The application itself should not store raw card numbers or similarly sensitive payment credentials.

Use payment-provider tokens/identifiers when applicable.

---

# 15. PAYMENT CONFIRMATION IS THE AUTHORITATIVE SALE EVENT

Do NOT update inventory or books when the QR is merely generated or scanned.

The state flow should be:

```text
Order created
      ↓
QR generated
      ↓
Customer scans
      ↓
Checkout opened
      ↓
Payment succeeds
      ↓
AUTHORITATIVE PAYMENT CONFIRMATION
      ↓
Financial consequences occur
```

A customer may scan and abandon payment.

Only successful payment should trigger the final committed sale effects.

If using an external payment processor, prefer the processor's authoritative server-side success event/webhook rather than relying only on a client-side redirect.

If external credentials/services are unavailable, implement a demo payment provider that produces the same internal authoritative event.

---

# 16. INVENTORY ARCHITECTURE

Implement proper inventory records.

A reasonable conceptual structure includes:

```text
INVENTORY_ITEMS

inventory_item_id
owner_id / business_id
name
unit_of_measure
quantity_on_hand
average_unit_cost
inventory_value
reorder information if useful
active
timestamps
```

Do not blindly duplicate derived values if they can be calculated safely.

Use clear identifiers and tenant/business scoping.

Inventory must support both:

```text
Quantity
Financial cost/value
```

because operational inventory and accounting inventory are related but not identical concepts.

---

# 17. INVENTORY MOVEMENTS

Do not update inventory quantities without history.

Maintain an inventory movement/event log.

Conceptually:

```text
INVENTORY_MOVEMENTS

movement_id
business_id
inventory_item_id
movement_type
quantity_delta
unit_cost
total_cost
source_type
source_id
timestamp
```

Potential movement sources include:

```text
purchase
sale consumption
manual adjustment
refund
waste
initial balance
```

The inventory balance should remain reconstructable/auditable.

---

# 18. INVENTORY VALUATION

For this hackathon, prefer a simple, defensible inventory-costing approach.

Use **weighted-average cost** unless the existing system strongly justifies another method.

Example:

```text
Existing:
20 eggs
Total value = $6

New purchase:
30 eggs
Cost = $12

New:
50 eggs
Total value = $18
Average cost = $0.36 / egg
```

If a product consumes four eggs:

```text
COGS contribution from eggs:
4 × $0.36
```

Use this cost information to create the appropriate COGS and inventory accounting consequences.

Do not introduce FIFO/LIFO complexity unless there is a compelling implementation reason.

---

# 19. ACCOUNTING CORE

Build a proper deterministic double-entry accounting engine.

Do NOT use an LLM as the authoritative calculator for accounting balances.

The journal is the accounting source of truth.

Every posted journal entry must satisfy:

```text
SUM(DEBITS) = SUM(CREDITS)
```

Do not incorrectly assume every journal entry consists of exactly one debit and one credit.

One transaction may contain multiple debit and/or credit lines.

Example:

```text
Equipment            DR 10,000
Cash                              CR 4,000
Loan Payable                      CR 6,000
```

This is one valid journal entry.

---

# 20. CHART OF ACCOUNTS

Create a business-scoped chart of accounts.

Follow this numbering philosophy:

```text
1000–1999  Assets
2000–2999  Liabilities
3000–3999  Equity / Owner Capital
4000–4999  Revenue
5000–5999  Costs / Expenses / Taxes
```

Subdivide intelligently inside those ranges where useful.

Example:

```text
1000 Assets
1010 Cash
1020 Business Bank Account
1100 Accounts Receivable
1200 Inventory
1500 Equipment

2000 Liabilities
2010 Accounts Payable
2100 Sales Tax Payable
2200 Loans Payable

3000 Equity
3010 Owner Capital
3020 Owner Draw
3100 Retained Earnings

4000 Revenue
4010 Product Sales
4020 Service Revenue

5000 Cost / Expenses / Taxes
5010 Cost of Goods Sold
5100 Supplies Expense
5200 Rent Expense
5300 Payroll Expense
5400 Utilities
5500 Tax Expense
```

Exact accounts can adapt by business type.

The onboarding business category may be used to initialize an appropriate chart-of-accounts template.

For example, restaurant, beauty, construction, retail, and service businesses should not necessarily start with identical specialized accounts.

---

# 21. ACCOUNTS TABLE

At minimum, accounts should support concepts equivalent to:

```text
ACCOUNT_ID
BUSINESS_ID / OWNER_ID
ACCOUNT_NUMBER
ACCOUNT_NAME
ACCOUNT_TYPE
ACCOUNT_SUBTYPE
NORMAL_BALANCE
FINANCIAL_STATEMENT
PARENT_ACCOUNT_ID if hierarchical accounts are useful
IS_ACTIVE
CREATED_AT
UPDATED_AT
```

Relevant `ACCOUNT_TYPE` values might include:

```text
ASSET
LIABILITY
EQUITY
REVENUE
EXPENSE
```

Normal balances:

```text
Assets       DEBIT
Expenses     DEBIT
Liabilities CREDIT
Equity       CREDIT
Revenue      CREDIT
```

Financial statement exposure should distinguish at least:

```text
BALANCE_SHEET
INCOME_STATEMENT
```

Use safe enums/contracts where appropriate.

---

# 22. JOURNAL DATA MODEL

Prefer separate journal-header and journal-line concepts.

Conceptually:

```text
JOURNAL_ENTRIES

ENTRY_ID
BUSINESS_ID
TRANSACTION_NUMBER
ENTRY_DATE
DESCRIPTION
SOURCE_TYPE
SOURCE_ID
STATUS
CREATED_AT
POSTED_AT
```

and:

```text
JOURNAL_LINES

LINE_ID
ENTRY_ID
ACCOUNT_ID
DEBIT
CREDIT
MEMO
```

If redundant `BUSINESS_ID` on lines materially improves safe tenant filtering, use it consistently.

Requirements:

- transaction number identifies related accounting lines;
- all lines from the same accounting event share the journal-entry relationship;
- a line must not contain both a nonzero debit and nonzero credit;
- negative debit/credit semantics should be handled consistently rather than becoming accidental data corruption;
- totals must balance before posting;
- duplicate source events must not accidentally post twice;
- journal entries should be auditable;
- source lineage should be preserved.

---

# 23. DO NOT CREATE ONE JOURNAL TABLE PER USER

Use shared multi-tenant tables with a tenant/business identifier.

Do NOT create:

```text
JOURNAL_DIEGO
JOURNAL_SARAH
JOURNAL_USER_123
```

Instead:

```text
JOURNAL_ENTRIES
JOURNAL_LINES
```

with mandatory business scoping.

Apply the same architecture to other domain tables where practical.

---

# 24. SOURCE EVENT → JOURNAL PIPELINE

Accounting should be driven by normalized business events.

Examples:

```text
SALE_COMPLETED
PURCHASE_CAPTURED
INVENTORY_ADJUSTMENT
OWNER_CONTRIBUTION
OWNER_DRAW
TRANSFER
REFUND
EXPENSE
ADJUSTING_ENTRY
```

Keep the generation logic in backend/domain services rather than scattered across React components.

A successful sale of $50 with $8.80 of inventory cost might generate:

```text
Journal Entry: Sale

DR Cash / Payment Receivable        50.00
CR Sales Revenue                    50.00
```

and:

```text
Journal Entry: Cost recognition

DR Cost of Goods Sold                8.80
CR Inventory                         8.80
```

These may be represented as separate journal entries or a coherent compound accounting event depending on implementation clarity.

Maintain source linkage either way.

---

# 25. SALES TAX

Do not assume all customer cash received equals revenue.

If the checkout includes sales tax, support:

```text
Sale before tax     $50
Sales tax            $4
Customer pays       $54
```

Accounting:

```text
DR Cash                     54
CR Sales Revenue            50
CR Sales Tax Payable         4
```

Do not overbuild tax compliance for the hackathon.

Implement enough to preserve correct accounting semantics and extensibility.

---

# 26. PURCHASE CLASSIFICATION

A raw card transaction generally identifies the cash/bank side of the transaction but may not perfectly identify the other accounting account.

Example:

```text
HOME DEPOT
-$428.93
```

Known side:

```text
CR Cash / Bank
```

Potential debit:

```text
Inventory
Materials
Equipment
Office expense
Owner draw
etc.
```

Classification can use:

```text
merchant
transaction description
business category
onboarding answers
receipt information
historical user classifications
existing chart of accounts
```

Use deterministic rules where confidence is high.

Use AI assistance where ambiguity exists.

Do not let the LLM create arbitrary accounts outside the governed chart of accounts without validation.

---

# 27. AI-ASSISTED CLASSIFICATION

When AI is useful, the AI should return structured output such as:

```json
{
  "suggested_account_id": "...",
  "confidence": 0.82,
  "reason": "...",
  "requires_user_confirmation": true
}
```

The backend must validate the recommendation.

The AI is not the authority.

The accounting service is.

For uncertain classifications, create an unobtrusive user confirmation experience.

When the user corrects classifications, persist that behavior as useful future business context.

Conceptually:

```text
Previous merchant classification
+
Business type
+
Current transaction
+
Receipt data
=
Improved recommendation
```

This supports the product message:

> Capital One Business learns how your business operates.

---

# 28. GENERAL LEDGER

Build a General Ledger derived from journal lines.

The ledger should allow viewing entries by account and should include totals equivalent to:

```text
Account
Total Debits
Total Credits
Balance
```

Balance calculation must respect account normal balance.

The journal remains the primary accounting source of truth.

Avoid maintaining a manually synchronized second accounting truth if a SQL view/query/materialized construct can safely derive the ledger.

If performance or Snowflake architecture favors a persisted derived object, ensure it is reproducible and never independently editable.

---

# 29. TRIAL BALANCE

Generate a trial balance from the ledger/journal.

Support at least:

```text
Account number
Account name
Debit balance
Credit balance
```

Verify:

```text
Total debit balances = Total credit balances
```

Expose imbalances internally as a serious integrity error.

Do not silently continue with broken financial statements.

---

# 30. UNADJUSTED VS ADJUSTED TRIAL BALANCE

Distinguish between:

```text
Unadjusted Trial Balance
        ↓
Adjusting Entries
        ↓
Adjusted Trial Balance
```

Do not pretend bank/card data automatically reveals every adjustment required in formal accrual accounting.

Potential adjustments may include:

```text
depreciation
accrued expenses
prepaid expenses
inventory corrections
accrued revenue
unearned revenue
```

For this hackathon, implement a reasonable adjustment mechanism without overcomplicating the owner workflow.

Adjustments can use the same journal system with a `SOURCE_TYPE` such as:

```text
ADJUSTMENT
```

The adjusted trial balance should incorporate posted adjusting entries.

---

# 31. FINANCIAL STATEMENTS

Using the adjusted accounting data, derive financial statements.

At minimum:

## Income Statement

Support appropriate grouping for:

```text
Revenue
Cost of Goods Sold
Gross Profit
Operating Expenses
Other relevant expenses
Net Income
```

## Balance Sheet / General Balance

Support:

```text
Assets
Liabilities
Equity
```

and verify the accounting equation:

```text
Assets = Liabilities + Equity
```

The frontend should present these statements in a way a non-accountant can understand.

Detailed formal views may exist beneath simplified summary views.

---

# 32. CASH-FLOW AND WORKING-CAPITAL INTELLIGENCE

Because the challenge concerns cash flow and working capital, do not stop at an income statement.

Use available transaction/accounting data to provide useful cash-oriented intelligence.

Examples:

```text
Cash available
Cash movement
Working capital
Short-term obligations
Liquidity trend
Inventory cash tied up
Upcoming financial pressure where data permits
Operating inflows/outflows
```

If sufficient accounting structure exists for a defensible cash-flow statement, implement one.

Do not fabricate unsupported accrual/cash classifications merely for completeness.

Prioritize useful, explainable cash intelligence.

---

# 33. FINANCIAL RATIOS

Create deterministic backend calculations for relevant financial ratios and metrics.

Candidates include:

## Liquidity

```text
Working Capital
Current Ratio
Quick Ratio
Cash Ratio where appropriate
```

## Profitability

```text
Gross Margin
Operating Margin
Net Profit Margin
Return on Assets where meaningful
```

## Leverage

```text
Debt-to-Equity
Debt Ratio
```

## Efficiency

```text
Inventory Turnover
Days Inventory Outstanding
Receivables Turnover if AR exists
Payables metrics if AP exists
Cash Conversion Cycle only if underlying data supports it
```

Do not display meaningless ratios simply because formulas exist.

Handle:

```text
division by zero
missing data
insufficient history
partial periods
negative denominators
non-applicable business types
```

gracefully.

The authoritative value must come from backend/SQL financial logic.

Do not calculate one ratio independently in React and another in Python.

---

# 34. RATIO UX

Do not expose a wall of finance terminology as the primary experience.

Instead of:

```text
Current Ratio: 0.82
```

prefer:

```text
Cash health
Needs attention

You currently have about $0.82 in short-term resources
for every $1.00 due soon.
```

Then offer:

```text
Current Ratio: 0.82
[ Learn what this means ]
```

The user should receive:

```text
status
plain-language explanation
trend
relevant drivers
recommended next action
```

where defensible.

Detailed ratio tables can exist in deeper financial views.

---

# 35. FINANCIAL EDUCATION

Preserve and improve the existing contextual financial-education concept.

Education should be triggered by the user's real situation rather than behaving like a generic course catalog.

Examples:

```text
Low liquidity
→ liquidity explanation

Repeated inventory overbuying
→ inventory working-capital lesson

Low gross margin
→ margin lesson

High debt burden
→ leverage explanation
```

The education system should complement, not duplicate, the financial assistant.

---

# 36. NATURAL-LANGUAGE FINANCIAL ASSISTANT

Create an in-app conversational assistant that lets the owner ask questions about their business naturally.

Examples:

```text
How much inventory do I have?

How many sales did I have last week?

How much money did I make this month?

How is my liquidity doing?

Which product made me the most profit?

How much did I spend on supplies?

How many cakes can I still produce?

Which inventory item is going to run out first?

Why did my profit fall this month?

What were my biggest expenses this week?

What is working capital?

Can you explain my current ratio?
```

This should feel like:

> **Ask your business anything.**

---

# 37. DO NOT IMPLEMENT THE ASSISTANT AS RAG-ONLY

Structured quantitative financial questions should NOT depend purely on vector retrieval.

Use a hybrid architecture.

Conceptually:

```text
User question
       ↓
Intent / tool routing
       ↓
┌─────────────────────────────┐
│                             │
Structured data          Knowledge/context
│                             │
Governed SQL /             RAG/search
semantic layer                 │
│                             │
Snowflake                 trusted content
│                             │
└──────────────┬──────────────┘
               ↓
          AI explanation
               ↓
          Final answer
```

---

# 38. STRUCTURED DATA QUESTIONS

Questions such as:

```text
How many sales did I have last week?

What was my revenue?

How much inventory do I have?

What is my current ratio?

How much did I spend at Costco?

Which product has the highest gross profit?
```

must use authoritative structured data.

The system should translate the business question into a governed query or invoke deterministic domain tools.

Possible implementation strategies include:

```text
semantic layer
controlled text-to-SQL
predefined financial tools
Snowflake semantic views
backend query services
```

Choose what best fits the project and available Snowflake capabilities.

Do not blindly allow unrestricted generated SQL against the entire database.

---

# 39. RAG QUESTIONS

RAG should be used where retrieval of unstructured/contextual information is appropriate.

Examples:

```text
What does liquidity mean?

Why is excess inventory dangerous?

Explain gross margin.

What did I tell you about my normal business week?

Explain why you recommended reducing inventory.

What does working capital mean for a small business?
```

Potential knowledge sources:

```text
financial education material
trusted SMB financial guidance
existing micro-lessons
business profile text
receipt descriptions
owner notes
business-specific contextual documents
```

If vector/RAG infrastructure is implemented, keep its role clear.

It is not the authoritative calculator of sales totals or accounting balances.

---

# 40. ANALYTICAL QUESTIONS

The most valuable assistant questions may require multiple data calls.

Example:

```text
Why did my profit fall this month?
```

The system may need to obtain:

```text
revenue comparison
COGS comparison
expense comparison
product mix
inventory cost changes
sales-volume changes
margin changes
```

Then explain the drivers.

The AI should reason over authoritative retrieved values.

It should not invent financial figures.

---

# 41. ASSISTANT EVIDENCE AND TRUST

Whenever practical, show the evidence behind answers.

Instead of only:

```text
Your revenue was $8,291.
```

prefer something like:

```text
Revenue this month
$8,291

Based on 126 completed sales from Sep 1–12.
11.4% higher than the equivalent period last month.
```

For complex calculations, provide an optional expandable explanation.

The UI should make it obvious that answers originate from the owner's actual business data.

---

# 42. TENANT SECURITY

This is non-negotiable.

Every relevant record must be scoped to the correct business/user.

Do not rely on an LLM prompt saying:

> Only query this user.

Enforce tenant isolation programmatically.

Conceptually:

```text
Authenticated user
      ↓
Resolved BUSINESS_ID / OWNER_ID
      ↓
Mandatory backend/data scope
      ↓
AI/query tools
```

The LLM must not have the authority to arbitrarily remove or substitute the tenant constraint.

A user must never retrieve another user's:

```text
sales
customers
inventory
journal
financial statements
ratios
business profile
transactions
```

through prompt injection or malformed queries.

---

# 43. TARGET SNOWFLAKE DOMAIN MODEL

The existing database currently includes concepts such as:

```text
USERS
BUSINESS_PROFILES
SCHEMA_MIGRATIONS
```

Preserve/migrate these intelligently rather than destroying useful data.

The final schema should support the following domain concepts.

Exact names can adapt to repository conventions.

## Identity / profile

```text
USERS
BUSINESS_PROFILES
```

Establish a clear, consistent tenant/business relationship.

Avoid ambiguous disconnected identifiers.

---

## Accounts

```text
ACCOUNTS
```

Contains the business chart of accounts.

---

## Raw financial observations

```text
CARD_TRANSACTIONS
```

Possible supporting tables:

```text
RECEIPTS
RECEIPT_ITEMS
```

These represent observed source data, not automatically authoritative journal lines.

---

## Products and services

Prefer a unified structure if appropriate:

```text
SELLABLE_ITEMS
```

or coherent:

```text
PRODUCTS
SERVICES
```

Use whichever results in the clearest implementation.

---

## Product/resource relationships

```text
ITEM_COMPONENTS
```

or equivalent bill-of-materials table.

Relationship concept:

```text
Sellable Item
        ↓
Required Inventory Resources
```

---

## Inventory

```text
INVENTORY_ITEMS
INVENTORY_MOVEMENTS
```

---

## Customers

```text
CUSTOMERS
```

---

## Sales

```text
SALES_ORDERS
ORDER_LINES
PAYMENTS
```

Orders and payments must remain distinct concepts.

---

## Accounting

```text
JOURNAL_ENTRIES
JOURNAL_LINES
```

The General Ledger, trial balance, financial statements, and ratios should preferably be derived through:

```text
views
queries
services
semantic models
materialized/dynamic constructs if justified
```

rather than manually editable duplicated truths.

Persist snapshots only if there is a valid use case.

---

# 44. DATA LINEAGE

Preserve traceability.

A user/developer should be able to answer:

> Why did this journal entry exist?

Example:

```text
PAYMENT PAY-1837
      ↓
ORDER ORD-2921
      ↓
SALE_COMPLETED event
      ↓
JOURNAL ENTRY JE-8291
      ↓
JOURNAL LINES
```

Likewise:

```text
CARD TRANSACTION TX-123
      ↓
RECEIPT RCPT-28
      ↓
CLASSIFICATION
      ↓
PURCHASE EVENT
      ↓
JOURNAL ENTRY
```

This lineage is important for trust, debugging, auditability, and AI explanations.

---

# 45. ACCOUNTING INTEGRITY INVARIANTS

Treat these as hard rules.

## Invariant 1

Every posted journal entry must balance:

```text
SUM(debit) = SUM(credit)
```

## Invariant 2

Financial statements derive from posted accounting data.

## Invariant 3

The ledger must reconcile to journal entries.

## Invariant 4

The trial balance must balance.

## Invariant 5

Balance Sheet:

```text
Assets = Liabilities + Equity
```

## Invariant 6

A successfully completed inventory-affecting sale must create corresponding inventory movements.

## Invariant 7

Inventory value used for accounting must reconcile with its costing method.

## Invariant 8

The same authoritative external/business event must not accidentally post twice.

Implement idempotency where necessary, especially for payment events/webhooks.

---

# 46. TRANSACTION ATOMICITY

When one business event produces multiple related changes, do not leave the system half-updated.

A successful sale conceptually requires:

```text
mark order paid
record payment
create inventory movements
create accounting entries
validate accounting balance
```

Treat this as one coherent operation.

If Snowflake's transaction capabilities and backend architecture permit transactional atomicity, use them appropriately.

If exact distributed atomicity is impossible due to external systems, implement idempotent state transitions and compensating/retry-safe logic.

Avoid:

```text
Payment saved        ✓
Inventory updated    ✓
Journal entry        ✗
```

without a recoverable state.

---

# 47. BACKEND ARCHITECTURE

Preserve good separation of concerns.

Business logic should not live in React.

Likewise, FastAPI routers should not become giant domain engines.

Prefer layers conceptually similar to:

```text
routers/
services/
repositories or storage/
models/
providers/
financial domain modules/
```

Potential services could include:

```text
sales_service
inventory_service
accounting_service
financial_statement_service
financial_ratio_service
transaction_classification_service
assistant_service
payment_service
```

Names may differ.

Prioritize maintainability over artificial overengineering.

---

# 48. FRONTEND ↔ BACKEND CONTRACTS

Create explicit typed contracts.

The existing project historically had contract drift between Python/Pydantic and JavaScript/TypeScript.

Reduce this risk.

Do not define subtly different copies of the same domain entity across random React components.

Centralize frontend domain types/API contracts where practical.

Handle:

```text
loading
success
empty state
validation error
network failure
server error
retry
```

gracefully.

Do not make a smooth happy path while leaving obvious failures broken.

---

# 49. API CONFIGURATION

Do not hard-code localhost API URLs in production-facing frontend logic.

Use the project's environment/configuration pattern.

Make local development easy while keeping deployment valid.

Verify CORS and environment configuration.

---

# 50. SNOWFLAKE MIGRATIONS

Add proper schema migrations.

Do not depend on manually editing the production Snowflake database without repository-tracked migration definitions.

Migrations should be:

```text
reproducible
ordered
safe enough for the hackathon
documented
compatible with existing data where practical
```

Update schema/export documentation if the project uses it.

---

# 51. SNOWFLAKE AS AUTHORITATIVE DATA SOURCE

Avoid maintaining financial truth independently in React state or static frontend mocks.

For core new financial functionality:

```text
Snowflake / backend domain engine
        ↓
authoritative values
        ↓
API
        ↓
frontend
        ↓
AI explanation
```

Frontend state may cache/present data, but it should not become a second financial ledger.

---

# 52. EXISTING FRONTEND MOCK DATA

The project historically used substantial static frontend mock data.

Replace or reduce mocks specifically where they interfere with the new real end-to-end functionality.

Do not mechanically delete every mock if some are still useful for unrelated demo presentation.

The financial core, however, must be based on the actual backend/database flow.

---

# 53. FINANCIAL ENGINE VS AI RESPONSIBILITIES

Maintain this separation:

```text
ACCOUNTING ENGINE
What happened financially?

ANALYTICS ENGINE
What do the numbers mathematically indicate?

AI ADVISOR
What does this mean for this owner?
What should they investigate or consider doing?
```

Examples:

The accounting engine calculates:

```text
Cash = $3,200
Current Assets = $8,400
Current Liabilities = $10,500
```

The financial engine calculates:

```text
Working Capital = -$2,100
Current Ratio = 0.80
```

The AI explains:

```text
Your short-term liquidity is tight.

You currently have approximately $0.80 in current
assets for every $1.00 of short-term obligations.
```

Never let the AI become the authoritative source of the underlying numbers.

---

# 54. AI GUARDRAILS FOR FINANCIAL ADVICE

The assistant may provide business-oriented explanations and suggestions.

It should avoid pretending that uncertain projections are guaranteed.

Distinguish:

```text
fact
calculation
inference
forecast
recommendation
```

Use language appropriate for a small-business owner.

For example:

```text
Your historical data shows...
```

is preferable to:

```text
You will definitely...
```

Recommendations should identify their reasoning when appropriate.

---

# 55. APP EXPERIENCE AFTER IMPLEMENTATION

A coherent ideal flow could look like this.

## Onboarding

Owner tells the app:

```text
business type
inventory habits
operating pattern
employee size
location/context
normal business week
```

The application initializes relevant business structures.

---

## Purchasing

Owner uses business card.

```text
Card purchase detected
      ↓
Transaction normalized
      ↓
Classification / receipt enrichment
      ↓
Inventory impact if applicable
      ↓
Journal posting
```

The user should usually not manually enter bookkeeping.

---

## Selling

Owner creates:

```text
Chocolate Cake
$25

Resources:
0.5 kg flour
4 eggs
0.25 kg chocolate
...
```

Later:

```text
Sell
Chocolate Cake × 2
Generate QR
```

Customer scans and pays.

Immediately:

```text
Payment received
$50
```

Behind the scenes:

```text
Revenue updated
Inventory consumed
COGS recognized
Journal posted
Ledger changed
Statements changed
Ratios changed
Analytics changed
```

---

## Analysis

Owner opens Analysis.

Instead of a finance textbook, they see useful business information:

```text
Revenue
Profit
Cash health
Inventory health
Working capital
Recent trends
Important changes
Recommended attention areas
```

They can inspect deeper accounting information when desired.

---

## Ask

Owner asks:

```text
Why did my profit go down this month?
```

The system obtains actual business data, analyzes drivers, and provides an understandable answer.

---

# 56. DEMO FLOW

Optimize the implementation so HackMTY judges can experience a compelling story quickly.

A strong demo should be able to demonstrate:

```text
1. Existing onboarding/business context.

2. A business purchase enters the system.

3. Optionally enrich the purchase with receipt/inventory information.

4. Owner creates or selects a product.

5. Product has inventory components.

6. Owner generates a QR sale.

7. Customer/judge scans and pays in demo/test mode.

8. Sale appears immediately.

9. Inventory decreases.

10. Journal automatically updates.

11. Financial statements/ratios update.

12. Ask the financial assistant:
    "How were my sales this week?"
    or
    "How is my liquidity doing?"

13. Assistant answers using the actual updated data.
```

The demo should not require unreliable third-party services to be online.

Where necessary, use swappable real/demo providers.

---

# 57. DEMO DATA

Provide realistic seed/demo data.

It should be financially coherent.

Avoid random values that cause nonsensical statements.

Create enough history for:

```text
weekly comparison
monthly comparison
inventory analysis
profit analysis
liquidity ratios
customer history
assistant questions
```

A demo business should have an understandable narrative.

Example:

```text
small bakery
products
ingredients
supplier purchases
sales
expenses
customers
inventory
cash
liabilities
```

The judge should be able to understand why the financial results changed.

---

# 58. TESTING REQUIREMENTS

Testing must focus on financial correctness and integration, not only code coverage.

At minimum, test important invariants and flows.

Examples:

```text
journal entries balance

duplicate payment events do not double-post

successful sale decrements expected BOM quantities

sale creates correct revenue entry

inventory consumption creates COGS/inventory entry

weighted-average cost updates correctly

ledger totals match journal

trial balance balances

balance sheet balances

ratio calculations handle edge cases

business A cannot query business B

assistant structured queries remain tenant-scoped

frontend can complete primary sale workflow
```

Preserve existing tests unless they are legitimately obsolete due to architectural changes.

Update affected tests deliberately.

---

# 59. END-TO-END VERIFICATION

Do not trust unit tests alone.

Run the application if tooling permits.

Verify real flows.

Trace actual records.

For an example sale:

```text
Frontend order
      ↓
Backend order
      ↓
Snowflake order row
      ↓
Payment row
      ↓
Inventory movement rows
      ↓
Journal entry
      ↓
Journal lines
      ↓
Ledger query
      ↓
Statement query
      ↓
Ratio endpoint
      ↓
Frontend rendering
      ↓
Assistant answer
```

If you cannot verify one layer due to unavailable external credentials, test it through the project's demo provider and clearly preserve the production provider boundary.

---

# 60. IMPLEMENTATION ORDER

Implement in dependency order rather than creating every UI page first.

Recommended order:

```text
A. Repository inspection and baseline

B. Core tenant/business identifiers

C. Snowflake migrations/domain tables

D. Chart of accounts + accounting engine

E. Inventory domain and costing

F. Product/service + BOM configuration

G. Sales orders + QR + payment abstraction

H. Successful-sale event pipeline

I. Purchase/card transaction normalization

J. Receipt enrichment/classification

K. Ledger + trial balance

L. Financial statements

M. Financial ratios / cash-flow intelligence

N. Frontend financial UX integration

O. Hybrid financial assistant

P. End-to-end tests and demo stabilization
```

You may adjust this order if the live architecture makes another sequence safer.

Do not implement downstream calculations against temporary fake structures that will immediately be replaced by the upstream architecture.

---

# 61. WORKING STYLE

Work autonomously.

Do not repeatedly ask the user to confirm routine implementation decisions.

When a detail is underspecified:

1. infer the simplest solution consistent with this product vision;
2. prefer correctness;
3. prefer low friction;
4. prefer demo reliability;
5. document meaningful assumptions.

Ask only when you are genuinely blocked by something that cannot reasonably be inferred, such as an unavailable credential or a consequential product decision with multiple incompatible interpretations.

If credentials are unavailable, do not stop the entire project.

Implement a clean provider abstraction and functional demo mode.

---

# 62. PROGRESS UPDATES

As you work, periodically communicate concise progress updates.

Useful updates include:

```text
what was inspected
what architecture decision was made
what was implemented
what was verified
what remains
what blocker, if any, exists
```

Do not fill updates with low-level narration of every file opened.

---

# 63. DO NOT DECLARE SUCCESS PREMATURELY

Before claiming completion, explicitly verify the major requirements.

Do not say:

> Implemented accounting.

if only tables and services exist.

Do not say:

> Implemented QR sales.

if customer payment does not trigger downstream effects.

Do not say:

> Implemented RAG assistant.

if it cannot correctly answer structured financial questions from the owner's actual database.

Do not say:

> Snowflake connected.

if only local-memory fallback was tested.

Be precise about what works.

---

# 64. FINAL ACCEPTANCE CHECKLIST

Before finishing the task, verify all applicable items below.

## Product / UX

- New functionality fits naturally into the existing navigation.
- Main workflows remain understandable to a non-financial user.
- Important financial information is translated into plain language.
- Detailed financial/accounting views remain available.
- Loading, error, empty and success states are handled.
- Customer-facing experience is consistently appropriate for the intended US market.

## Data

- Snowflake migrations exist.
- Tenant/business relationships are coherent.
- Raw transactions remain distinguishable from interpreted accounting events.
- Products/services persist.
- BOM/component relationships persist.
- Inventory persists.
- Inventory movements persist.
- Orders persist.
- Payments persist.
- Customers persist when available.
- Journal entries and journal lines persist.

## Accounting

- Account numbering follows the agreed high-level scheme.
- Accounts have type, normal balance and statement exposure.
- Every posted journal entry balances.
- Sales create correct accounting effects.
- Inventory-consuming sales create COGS/inventory effects.
- Taxes are not incorrectly counted entirely as revenue.
- Ledger derives correctly.
- Trial balance balances.
- Adjustments are supported coherently.
- Adjusted trial balance derives correctly.
- Income statement derives from authoritative accounting data.
- Balance sheet derives correctly.
- Assets = Liabilities + Equity.

## Inventory

- Products can consume inventory resources.
- Sale completion decrements resources automatically.
- Inventory value is tracked.
- Weighted-average cost functions correctly.
- Inventory movement history is maintained.

## Sales

- Owner can configure products/services.
- Owner can initiate a sale without reconfiguring products.
- Order is created before payment.
- QR identifies the specific order.
- Customer does not need to manually enter what they are buying.
- Payment success is authoritative.
- Sale pipeline is idempotent.
- Demo/test payment mode exists when needed.

## Purchases

- Card transaction source is abstracted.
- Nessie is not an architectural bottleneck.
- Purchases can be normalized into internal transactions.
- Classification exists.
- Receipt enrichment has a viable path.
- Ambiguous transactions can be reviewed simply.

## Analytics

- Relevant ratios calculate correctly.
- Ratios come from backend/SQL, not duplicated frontend math.
- Working-capital/liquidity information is surfaced.
- Trends are understandable.
- Insufficient-data scenarios do not produce misleading numbers.

## AI Assistant

- Structured financial questions query authoritative structured data.
- RAG is used for appropriate unstructured/educational context.
- Analytical questions can combine multiple tools/data calls.
- Deterministic financial values are not hallucinated by the LLM.
- User/business isolation is enforced programmatically.
- Answers show evidence/context where useful.
- Assistant can answer questions about data generated during the live demo.

## Integration

- Frontend calls the real backend for core functionality.
- Backend reads/writes intended Snowflake tables.
- API configuration works outside localhost.
- CORS/environment setup works.
- Existing important flows still work.
- Main build/tests pass or remaining failures are explicitly explained.
- Primary end-to-end demo flow has been executed successfully.

---

# 65. CORE PRODUCT PRINCIPLE TO PRESERVE

When making trade-offs, return to this:

> **Financially rigorous underneath. Effortless on top.**

Do not expose complexity simply because the implementation is complex.

Do not simplify the backend by making the financial calculations unreliable.

The purpose of the application is to allow someone with little financial knowledge to benefit from professional accounting and business intelligence automatically.

---

# 66. CORE TECHNICAL PRINCIPLE TO PRESERVE

There must be one coherent flow of financial truth:

```text
REAL BUSINESS EVENT
        ↓
NORMALIZED DOMAIN EVENT
        ↓
INVENTORY / ACCOUNTING ENGINE
        ↓
SNOWFLAKE AUTHORITATIVE RECORDS
        ↓
DERIVED FINANCIAL INFORMATION
        ↓
API
        ↓
FRONTEND
        ↓
AI EXPLANATION / CONVERSATION
```

Avoid parallel truths.

Avoid hidden frontend-only calculations.

Avoid disconnected demo components.

Avoid LLM-generated authoritative accounting numbers.

---

# 67. SCOPE PRIORITY

If time becomes constrained, prioritize in this order:

```text
1. Correct end-to-end data architecture
2. QR sale working end-to-end
3. Inventory + BOM effects
4. Balanced journal generation
5. Ledger / trial balance
6. Income statement / balance sheet
7. Ratios and cash-flow intelligence
8. Financial assistant over real data
9. Receipt enrichment
10. Additional polish / secondary features
```

However, do not interpret this as permission to leave the app in a visibly fragmented state.

A smaller number of deeply connected features is preferable to a larger number of disconnected ones.

---

# 68. HACKATHON STANDARD

This application must be **demo-ready**.

Optimize simultaneously for:

```text
real-world usefulness
technical depth
financial credibility
clear product narrative
reliable live demonstration
polished user experience
```

The strongest demonstration is not that many technologies were used.

The strongest demonstration is:

> A real-looking business event occurs, the system automatically understands its operational and financial consequences, and the owner immediately receives useful financial intelligence without doing accounting.

---

# 69. YOUR FIRST ACTIONS

Begin by inspecting the repository and establishing the current state.

Then produce a short implementation plan grounded in the actual codebase.

Immediately proceed into implementation.

Do not stop and wait for approval of the plan unless you encounter a genuinely blocking ambiguity.

As you implement:

```text
inspect
→ modify
→ migrate
→ connect
→ run
→ test
→ inspect resulting data
→ fix
→ continue
```

Keep going through the requested scope.

---

# 70. FINAL DELIVERABLE

At the end, provide a concise implementation report containing:

### What was implemented

Describe completed user-facing capabilities.

### Architecture

Explain major new backend/database/frontend modules and their relationships.

### Snowflake changes

List migrations/tables/views/semantic structures created or modified.

### Accounting validation

State how double-entry integrity, ledger reconciliation, trial balance, statements and ratios were validated.

### End-to-end verification

Describe the exact primary flows that were executed successfully.

### AI assistant

Explain how structured queries, RAG/context retrieval and tenant security operate.

### Demo instructions

Give the shortest reproducible sequence for showing judges:

```text
business context
→ purchase/sale
→ inventory/accounting
→ financial analysis
→ natural-language question
```

### Remaining limitations

Only list genuine remaining limitations, especially those caused by unavailable external credentials/services.

Do not hide unfinished integrations behind optimistic wording.

---

# EXECUTE

You now own implementation of this specification.

Inspect the existing Capital One Business repository, preserve what is useful, refactor what is necessary, implement the architecture above into the actual project, and verify that the result works coherently from database to backend to frontend to financial assistant.

Do not merely tell me how to build it.

**Build it.**