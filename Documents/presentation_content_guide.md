# AETERNA-QA Project Presentation — Content Guide

## Project Name & Inspiration
**AETERNA-QA** — "Aeterna" (Latin: eternal/enduring) combines with "QA" (Quality Assurance)
- **Genshin Impact Connection**: Inspired by the eternal nature of the Abyss and the systematic, methodical approach of Void entities in data observation
- **Meaning**: A system that endures and improves data quality autonomously

---

## Slide-by-Slide Breakdown

### **Slide 1: Title Slide**
- **Project Name**: AETERNA-QA
- **Subtitle**: Autonomous Entity-Driven Verification & Reasoning for Data Quality Assessment
- **Context**: Capstone Project Proposal & Implementation Roadmap

---

### **Slide 2: Abstract Project Overview & Objectives**

**Overview:**
AETERNA-QA is an autonomous agent-based system for data quality assessment and cleaning. It combines LLM-powered planning, iterative verification loops, and downstream model feedback to autonomously detect, diagnose, and repair data quality issues while proving the effectiveness of each cleaning operation.

**Primary Objectives:**
1. Reduce manual data cleaning by 80%
2. Achieve verification-driven cleaning with 80%± improvement confidence
3. Provide audit trails for compliance and interpretability
4. Support multi-table schema-aware data governance

**Key Metric**: If a cleaning operation doesn't improve downstream model F1 by ≥1%, it's rejected and rolled back.

---

### **Slide 3: Problem Scenario Motivation & Need For Solution**

**Current Bottleneck / Existing System:**
- Data scientists spend **60-80% of time** on data preparation
- Static rule engines break when data distributions shift (drift)
- No feedback loop to validate if cleaning improves downstream models
- Enterprise data lakes lack autonomous quality governance
- Cleaning decisions are opaque and non-auditable

**Why This Matters:**
- Manual cleaning = scalability bottleneck
- Rule-based systems are rigid and inflexible
- No verification means wasted effort on ineffective cleaning
- Regulatory requirements (GDPR, HIPAA) demand audit trails

**Proposed Motivation:**
1. LLM-based autonomous diagnosis replaces static rules
2. Downstream model performance delta as reward signal
3. Iterative detect-verify-repair with automatic rollback
4. Causal hypothesis generation for interpretability
5. Schema graphs enable multi-table data governance

---

### **Slide 4: Core System Functionalities, Key Features & Modules**

#### **1. Data Profiling Engine**
- Statistical profiling (nulls, outliers, distributions)
- Anomaly detection via ML (PyOD, Isolation Forest)
- Temporal drift monitoring

#### **2. LLM Planner Module**
- Chain-of-thought diagnosis of data issues
- Ranked strategy generation with confidence scores
- Multi-hypothesis exploration

#### **3. Autonomous Execution**
- Tool-use API (Pandas, imputation, standardization)
- Great Expectations constraint validation
- Semantic string cleaning via regex & fuzzy matching

#### **4. Verification Loop** (Novel Contribution)
- Lightweight model trainer (sklearn RandomForest)
- Performance delta measurement (ΔF1, ΔAUC)
- Automatic rollback on negative delta

#### **5. Audit & Explainability**
- Provenance tracking for every operation
- Causal hypothesis templates
- Natural language explanations

---

### **Slide 5: Tools & Technologies - Technology Stack Matrix**

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Streamlit / Gradio | Interactive UI for data upload & visualization |
| **Backend** | FastAPI / LangChain | Agent orchestration & API layer |
| **LLM/AI** | GPT-3.5 Turbo / Llama 2 | Planning, diagnosis, explanation |
| **Data Tools** | Pandas / Polars / Great Expectations | Profiling, transformation, validation |
| **Anomaly Detection** | PyOD / Isolation Forest | Outlier & drift detection |
| **ML Models** | sklearn (RandomForest, XGBoost) | Lightweight downstream validators |
| **Database** | PostgreSQL / DuckDB | Dataset storage & schema management |
| **DevOps** | Docker / Kaggle Notebooks | Containerization & reproducibility |
| **Benchmarking** | TFDV / UCI Datasets | Adult Census, Hospital, Flights |

---

### **Slide 6: Project Work Status - Week-Wise Timeline Plan**

#### **Month 1: Foundation (Weeks 1–4)**
**Deliverable**: End-to-end pipeline working (no verification yet)
- Week 1: Profiling engine + anomaly detection setup
- Week 2: LLM planner with prompt engineering
- Week 3: Pandas tool-use layer + validation
- Week 4: First demo on dirty CSV

**Output**: Agent can detect issues and propose cleaning

---

#### **Month 2: Core Verification (Weeks 5–8)**
**Deliverable**: Verification loop + first benchmark results
- Week 5: Lightweight model trainer (sklearn RandomForest)
- Week 6: Delta measurement + rollback logic
- Week 7: Benchmark on Adult Census dataset
- Week 8: Second dataset (Hospital) + bug fixes

**Output**: Real numbers showing cleaning effectiveness
- Example: "Agent improved F1 by 14% over baseline"

---

#### **Month 3: Scale & Evaluation (Weeks 9–12)**
**Deliverable**: 80% complete research work
- Week 9: Multi-table schema graph support
- Week 10: Causal hypothesis templates + audit trails
- Week 11: Third dataset benchmark (Flights)
- Week 12: Ablation study (verification ON vs OFF)

**Output**: Publishable benchmark results

---

#### **Month 4: Polish & Depth (Weeks 13–16)**
**Deliverable**: 100% complete, conference-ready work
- Week 13: RL learning convergence analysis
- Week 14: Human-in-the-loop interactive layer
- Week 15: Statistical significance testing
- Week 16: Beautiful demo + paper write-up

**Output**: Presentation-ready, interview-ready

---

### **Slide 7: Thank You**
Thank you for your time and consideration.

---

## Key Talking Points for Your Guide

### **Why This Project Stands Out**

1. **Novel Contribution**: Unlike existing data cleaning agents (DeepPrep, CleanAgent), AETERNA-QA closes the feedback loop by measuring whether cleaning actually improved downstream models. This is the verification-first approach.

2. **Realistic Timeline**: 4 months total (3 months for 80%, 1 for polish) is ambitious but achievable with Kaggle resources and lightweight tools.

3. **Benchmarking**: Will compare against:
   - No cleaning (baseline)
   - Manual rule-based cleaning
   - Other LLM agents (if available)
   - Your agent with verification ON vs OFF (ablation)

4. **Practical Impact**: Every organization with data pipelines needs this. Direct industry relevance.

5. **Research Quality**: Multiple published papers have covered pieces (DeepPrep, IterClean, ActiveClean). Your contribution is tying them together with a verification loop + downstream feedback. This is publishable at VLDB workshops or arXiv.

---

## Project Name Inspiration Explained

**AETERNA-QA** draws from *Genshin Impact's* lore in subtle ways:

- **Aeterna (Eternal)**: The world of Teyvat exists in eternal cycles—data quality is a continuous, cyclical process, not a one-time fix.
- **Entity-Driven**: The Abyss Order in Genshin moves with precise methodology and observation. Your agent systematically observes, diagnoses, and acts.
- **Verification & Reasoning**: The Abyss's principles involve understanding cause-and-effect (causal reasoning). Your agent does the same with data.
- **Quality Assessment**: The final quality is proven, not assumed—just as in Teyvat, reality is determined by verification.

---

## What To Highlight During Presentation

1. **Problem**: Data cleaning is 60-80% of a data scientist's job. Current tools are static and don't adapt.

2. **Solution**: An agent that learns, verifies, and proves its work.

3. **Novel Angle**: Unlike papers that just propose cleaning operations, you *verify* every operation's downstream impact.

4. **Evaluation**: Rigorous benchmarking on 3 datasets with ablation studies.

5. **Timeline**: Realistic 4-month plan with clear milestones.

6. **Impact**: Publishable research + industry-ready prototype.

---

## Expected Results (Based on Literature)

By end of Month 3, you should be able to show:

- **Baseline**: Manual cleaning takes 10 hours/dataset, improves F1 by 8%
- **AETERNA-QA**: Autonomous cleaning takes 30 minutes, improves F1 by 14%
- **Verification Loop Impact**: Removes 5 "bad" cleaning operations that would have hurt F1
- **Multi-dataset generalization**: Improvements consistent across Adult Census, Hospital, and Flights datasets

These are realistic targets based on papers like IterClean (3x better F1) and Exploring LLM Agents for Cleaning (downstream model correlation).

---

## Files Included

1. **AETERNA_QA_Project_Proposal.pptx** — Your presentation (7 slides, fully formatted)
2. **presentation_content_guide.md** — This document (detailed talking points)
3. **autonomous_data_quality_agent_research_papers.md** — Research references (25+ papers)

All files are ready to download from `/mnt/user-data/outputs/`.

Good luck with your presentation! 🚀
