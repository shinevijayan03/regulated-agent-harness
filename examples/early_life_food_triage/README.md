# Early Life Food Supply Chain Triage (Reference Implementation)

**Domain:** Infant Nutrition & Baby Food Supply Chain Governance  
**Regulatory Standards:** FDA Infant Formula Act (21 CFR Part 106 & 107), FSMA (21 CFR Part 117), FDA 21 CFR Part 11, GxP  
**Powered by:** `enterprise-agent-harness`  

---

## 1. Domain Problem & Regulatory Mandate

Under the **FDA Infant Formula Act (21 CFR Part 106.100)**, infant nutrition products carry **zero tolerance** for critical foodborne pathogens (*Cronobacter sakazakii* and *Salmonella*). Any presumptive positive result or thermal pasteurization excursion requires immediate product quarantine and root-cause containment.

However, executing high-consequence operations (such as applying an ERP inventory lockdown across warehouse distribution centers) must **never occur autonomously without human authorization**. 

The **Enterprise Agent Harness** solves this:
1. **Autonomous Investigation:** Rapidly pulls LIMS pathogen reports and SCADA thermal dataloggers using `READ_ONLY` tools.
2. **Deterministic Risk Gating:** Detects the contamination breach and attempts to call `quarantine_infant_formula_lot`.
3. **Governed HITL Interrupt:** Recognizes `RiskTier.MUTATING_HIGH_RISK`, halts execution, saves a persistent state checkpoint, and generates an approval ticket.
4. **Digitally Signed Resumption:** Resumes only upon receiving a cryptographically signed approval from the QA Director.
5. **Tamper-Evident Merkle Chain:** Records every interaction, tool execution, and human decision into an append-only SHA-256 hash chain conforming to **FDA 21 CFR Part 11**.

---

## 2. Architecture & Execution Flow

```
[Operator Prompt] 
       |
       v
[InputGuardInterceptor] (PII Redacted & Injection Guard)
       |
       v
[LangGraph State Orchestrator] 
       |
       +--> Tool: get_batch_pathogen_screening (READ_ONLY)
       |          `--> Presumptive Positive Cronobacter Detected!
       |
       +--> Tool: quarantine_infant_formula_lot (MUTATING_HIGH_RISK)
                  |
                  v
         [HITL Gate Interrupt]
         Status: REQUIRES_APPROVAL (Ticket: appr-05069178)
                  |
                  v
         [QA Director Electronic Signature] (FDA 21 CFR Part 11)
                  |
                  v
         [Deterministic Resumption]
         SAP ERP Lock Applied -> Outbound Shipping Halted
                  |
                  v
         [Cryptographic Merkle Audit Trail] (Validated 100%)
```

---

## 3. Running the Interactive Demonstration

To execute the live multi-agent triage demonstration:

```bash
python examples/early_life_food_triage/demo.py
```

---

## 4. Running Pre-Flight Synthetic Evaluations

To run the automated quality gate against the golden dataset:

```bash
harness eval --dataset examples/early_life_food_triage/eval_dataset.json --min-fidelity 0.90 --min-faithfulness 0.80
```
