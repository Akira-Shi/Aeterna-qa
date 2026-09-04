# Autonomous Data Quality & Cleaning Agent — Research Papers Reference Guide

## Overview
This is a curated collection of research papers directly relevant to building an **autonomous agent for data quality and cleaning with feedback verification**. Papers are organized by topic: core agent systems, data preparation, iterative cleaning, verification loops, and benchmarks.

---

## 🎯 Core Agent Systems for Data Preparation

### **1. DeepPrep: An LLM-Powered Agentic System for Autonomous Data Preparation**
- **Paper**: https://arxiv.org/abs/2602.07371
- **Venue**: PVLDB (Top-tier)
- **Date**: February 2026
- **Why Read**: 
  - Directly addresses autonomous data preparation via LLM agents
  - Uses **tree-based agentic reasoning** with execution-grounded feedback
  - Constructs pipelines iteratively with intermediate table state materialization
  - 15x lower inference cost than GPT-5 with comparable accuracy
- **Key Contribution**: Shows how to move beyond linear decision-making to structured exploration with non-local revision

---

### **2. CleanAgent: Automating Data Standardization with LLM-based Agents**
- **Paper**: https://arxiv.org/abs/2403.08291
- **Venue**: VLDB 2025 Workshop (DATAI)
- **Date**: March 2024 / 2025 Workshop
- **Why Read**:
  - Focuses on autonomous planning + execution for data standardization
  - LLM agents generate and execute cleaning Python code
  - Handles format inconsistencies without manual rule specification
- **Key Contribution**: Demonstrates how LLMs can autonomously propose AND execute cleaning strategies

---

### **3. ProfiliTable: Profiling-Driven Tabular Data Processing via Agentic Workflows**
- **Paper**: https://arxiv.org/abs/2605.12376
- **Venue**: Top-tier (May 2026)
- **Date**: May 2026
- **Why Read**:
  - Multi-agent framework with **dynamic profiling** at its core
  - Covers cleaning, transformation, augmentation, and matching
  - Iterative refinement with feedback-driven loops
  - Addresses ambiguous instructions and complex task structures
- **Key Contribution**: Shows how profiling drives accurate agent reasoning; includes feedback-driven refinement

---

## 🔍 Iterative Cleaning with Verification Loops

### **4. IterClean: An Iterative Data Cleaning Framework with Large Language Models**
- **Paper**: https://dl.acm.org/doi/10.1145/3674399.3674436
- **Venue**: ACM Turing Award Celebration Conference - China 2024
- **Date**: November 2024
- **Why Read**:
  - **Three-step iterative loop**: error detector → verifier → repairer
  - LLM acts as self-verifier (critical for your verification step)
  - Achieves 3x higher F1 than prior baselines with only 5 labeled tuples
  - Addresses over half of errors that sequential detect-repair pipelines miss
- **Key Contribution**: Integrated prompting framework where LLM continuously verifies its own repairs

---

### **5. Exploring LLM Agents for Cleaning Tabular Machine Learning Datasets**
- **Paper**: https://arxiv.org/abs/2503.06664
- **Venue**: arXiv (April 2025)
- **Date**: April 2025
- **Why Read**:
  - LLM has **programmatic access to IPython** to modify datasets
  - Feedback based on **downstream ML model performance** (your verification signal!)
  - Shows how LLMs iteratively explore, detect, and correct errors
  - Receives performance feedback from model trained on modified dataset
- **Key Contribution**: Closes the loop — cleaning → model training → feedback → refinement

---

### **6. AutoDCWorkflow: LLM-based Data Cleaning Workflow Auto-Generation and Benchmark**
- **Paper**: https://arxiv.org/abs/2412.06724
- **Venue**: arXiv (December 2024)
- **Date**: December 2024
- **Why Read**:
  - Auto-generates cleaning workflows from natural language descriptions
  - Iterative components: select columns → inspect quality → generate operations → repeat
  - Shows data quality inspection as a core feedback loop
- **Key Contribution**: Demonstrates how agents decide *which* operations to apply iteratively

---

## 📊 Data Profiling & Anomaly Detection

### **7. LLMDap: LLM-based Data Profiling and Sharing**
- **Paper**: https://www.vldb.org/2025/Workshops/VLDB-Workshops-2025/DEC/DEC25_5.pdf
- **Venue**: VLDB 2025 Workshop (DEC)
- **Date**: 2025
- **Why Read**:
  - Addresses automated data profiling using LLMs
  - Generates standardized metadata for diverse datasets
  - Uses RAG for precision in metadata extraction
- **Key Contribution**: Data profiling as a foundation for downstream cleaning decisions

---

### **8. Can LLMs Clean Up Your Mess? A Survey of Application-Ready Data Preparation with LLMs**
- **Paper**: https://arxiv.org/abs/2601.17058
- **Venue**: Comprehensive Survey (January 2026)
- **Date**: January 2026
- **Why Read**:
  - **Most comprehensive recent survey** on LLM-based data cleaning
  - Covers imputation, standardization, entity resolution, schema matching
  - Analyzes iterative vs. sequential approaches
  - Discusses IterClean, Cocoon, LLMClean, and 15+ other systems
  - Excellent taxonomy of approaches
- **Key Contribution**: State-of-the-art landscape; identifies gaps your project can address

---

### **9. Data Science in the Big Data Era**
- **Paper**: https://premierscience.com/pjds-26-1687/
- **Venue**: Premier Science (2026)
- **Date**: 2026
- **Why Read**:
  - Addresses real-world data quality challenges
  - Context for why data cleaning is 60-80% of a data scientist's time
- **Key Contribution**: Problem motivation and statistics

---

## 🎓 Feedback Loops & Reinforcement Learning with Verification

### **10. Inference-Time Scaling of Verification: Self-Evolving Deep Research Agents via Test-Time Rubric-Guided Verification**
- **Paper**: https://arxiv.org/abs/2601.15808
- **Venue**: arXiv (April 2026)
- **Date**: April 2026
- **Why Read**:
  - **DeepVerifier**: rubrics-based outcome reward verifier
  - Demonstrates inference-time scaling through iterative verification
  - Self-improvement without additional training
  - 8%-11% accuracy gains through verification feedback
- **Key Contribution**: Verification as a feedback signal for agent self-improvement (directly applicable to your data cleaning!)

---

### **11. Reinforcement Learning for Computer-Use Agents with Autonomous Evaluation**
- **Paper**: https://arxiv.org/abs/2606.24515
- **Venue**: arXiv (2026)
- **Date**: 2026
- **Why Read**:
  - Shows how agents can be trained with verifiable rewards
  - Addresses autonomous evaluation of agent actions
  - Discusses imperfect verifiers
- **Key Contribution**: Establishing reward signals for agentic behavior in real-world tasks

---

### **12. Agentic Reinforced Policy Optimization**
- **Paper**: https://arxiv.org/abs/2507.19849
- **Venue**: arXiv (2025)
- **Date**: 2025
- **Why Read**:
  - RLVR (Reinforcement Learning with Verifiable Rewards) approaches
  - Connects to how agents learn better policies through verification
- **Key Contribution**: RL paradigm for improving agent behavior

---

### **13. VerIF: Verification Engineering for Reinforcement Learning in Instruction Following**
- **Paper**: https://arxiv.org/abs/2506.09942
- **Venue**: arXiv (June 2025)
- **Date**: June 2025
- **Why Read**:
  - Verification engineering for RL-based agents
  - Shows how to design verifiers for agent outputs
- **Key Contribution**: Practical verification design patterns

---

## 📈 Data-Centric AI & Benchmarks

### **14. DeepAnalyze: Agentic Large Language Models for Autonomous Data Science**
- **Paper**: https://arxiv.org/abs/2510.16872
- **Venue**: GitHub (Fully Open-Source)
- **Date**: October 2025
- **Why Read**:
  - Full data science pipeline: preparation → analysis → modeling → visualization
  - Open-source LLM agent for data science
  - Companion system: **DeepPrep** for data preparation
- **Key Contribution**: Production-grade agent system reference

---

### **15. DataGovBench: Benchmarking LLM Agents for Real-World Data Governance Workflows**
- **Paper**: https://arxiv.org/abs/2512.04416
- **Venue**: arXiv (December 2025)
- **Date**: December 2025
- **Why Read**:
  - Benchmark for evaluating data agents
  - Hierarchical evaluation with rigorous metrics
  - Covers multiple data governance tasks
- **Key Contribution**: Evaluation framework and benchmarks for data agents

---

### **16. The Dirty Secret of AI in 2026: Data Cleaning Job is still a priority**
- **Paper**: https://medium.com/@ujjwalgupta893/the-dirty-secret-of-ai-in-2026-data-cleaning-job-is-still-a-priority-ecacf4e05dff
- **Venue**: Medium (January 2026)
- **Date**: January 2026
- **Why Read**:
  - Recent industry perspective on data quality importance
  - "Data-Centric AI" paradigm
  - Real-world evidence that data cleaning remains unsolved
- **Key Contribution**: Motivation and market validation

---

### **17. EvoDS: Self-Evolving Autonomous Data Science Agent with Skill Learning and Context Management**
- **Paper**: https://arxiv.org/abs/2606.03841
- **Venue**: arXiv (2026)
- **Date**: 2026
- **Why Read**:
  - Self-evolving agents with skill learning
  - Context management for long-running agents
- **Key Contribution**: Agent architecture patterns

---

## 🔧 Foundational & Related Work

### **18. ActiveClean: Interactive Data Cleaning While Learning Convex Loss Models**
- **Paper**: https://arxiv.org/abs/1601.03797
- **Venue**: UC Berkeley (2016, but still relevant)
- **Date**: 2016
- **Why Read**:
  - Progressive data cleaning with model updates
  - Shows how to maintain accuracy guarantees during iterative cleaning
  - Older but foundational work on feedback-driven cleaning
- **Key Contribution**: Early work on connecting data cleaning to downstream model performance

---

### **19. A Survey of Data Agents: Emerging Paradigm or Overstated Hype?**
- **Paper**: https://arxiv.org/abs/2510.23587
- **Venue**: arXiv (October 2025)
- **Date**: October 2025
- **Why Read**:
  - Comprehensive taxonomy of data agents
  - Covers 100+ papers in the space
  - Identifies open problems and research gaps
  - Perfect starting point for literature review
- **Key Contribution**: Highest-level survey; situates your project in the broader landscape

---

### **20. Large Language Model-based Data Science Agent: A Survey**
- **Paper**: https://arxiv.org/abs/2508.02744
- **Venue**: arXiv (August 2025)
- **Date**: August 2025
- **Why Read**:
  - Focuses on LLM agents for data science
  - Covers full lifecycle from problem formulation to deployment
- **Key Contribution**: LLM-agent-specific taxonomy

---

### **21. Data Agents: Levels, State of the Art, and Open Problems**
- **Paper**: https://arxiv.org/abs/2602.04261
- **Venue**: arXiv (February 2026)
- **Date**: February 2026
- **Why Read**:
  - Defines levels of data agent autonomy
  - Open problems in agent design
  - Comprehensive reference for current SOTA
- **Key Contribution**: Frameworks for thinking about agent maturity

---

### **22. LLM-Based Data Science Agents: A Survey of Capabilities, Challenges, and Future Directions**
- **Paper**: https://arxiv.org/abs/2510.04023
- **Venue**: arXiv (October 2025)
- **Date**: October 2025
- **Why Read**:
  - Capabilities and limitations of LLM agents
  - Challenges: hallucination, reasoning, tool use reliability
  - Future research directions
- **Key Contribution**: Critical analysis of current systems

---

## 💾 SQL/Database-Focused Agents (Complementary)

### **23. ProSPy: A Profiling-Driven SQL-Python Agentic Framework for Enterprise Text-to-SQL**
- **Paper**: https://arxiv.org/abs/2606.05836
- **Venue**: arXiv (2026)
- **Date**: 2026
- **Why Read**:
  - Data profiling as a substitute for adhoc exploration
  - Templated profiling queries
  - Applicable to database-backed data cleaning
- **Key Contribution**: Efficient profiling patterns

---

### **24. BranchBench: Aligning Database Branching with Agentic Demands**
- **Paper**: https://arxiv.org/abs/2604.17180
- **Venue**: arXiv (2026)
- **Date**: 2026
- **Why Read**:
  - Infrastructure for agentic workflows on databases
  - Sandboxed experimentation for agents
  - Relevant for multi-table scenarios
- **Key Contribution**: System design patterns for agent-friendly data systems

---

### **25. Data Intelligence Agents: Interpreting, Modeling, and Querying Enterprise Data via Autonomous Coding Agents**
- **Paper**: https://arxiv.org/abs/2606.19319
- **Venue**: arXiv (June 2026)
- **Date**: June 2026
- **Why Read**:
  - Enterprise-scale data exploration with agents
  - Multi-modal reasoning (SQL + Python)
- **Key Contribution**: Real-world enterprise patterns

---

## 🎯 Recommended Reading Order for Your Project

### **Phase 1: Understand the Problem (Week 1-2)**
1. **Can LLMs Clean Up Your Mess?** (Survey — establish baseline knowledge)
2. **The Dirty Secret of AI in 2026** (Industry context)
3. **A Survey of Data Agents** (Situate your work in the landscape)

### **Phase 2: Learn Core Agent Architectures (Week 3-4)**
4. **DeepPrep** (Tree-based reasoning with execution feedback)
5. **ProfiliTable** (Multi-agent + profiling-driven approach)
6. **CleanAgent** (Autonomous execution of cleaning code)

### **Phase 3: Understand Verification Loops (Week 5-6)**
7. **IterClean** (Error detector-verifier-repairer loop)
8. **Inference-Time Scaling of Verification** (DeepVerifier — rubric-guided verification)
9. **Exploring LLM Agents for Cleaning...** (Downstream model feedback)

### **Phase 4: Implementation Specifics (Week 7-8)**
10. **AutoDCWorkflow** (Iterative workflow generation)
11. **LLMDap** (Profiling implementation details)
12. **ProSPy** (Profiling patterns, if handling databases)

### **Phase 5: Benchmarking & Evaluation (Week 9+)**
13. **DataGovBench** (Evaluation framework)
14. **RL with Verifiable Rewards** (If implementing RL loop)

---

## 📋 Quick Reference Table

| Paper Title | Arxiv/URL | Date | Key Contribution | Relevance |
|---|---|---|---|---|
| DeepPrep | https://arxiv.org/abs/2602.07371 | Feb 2026 | Tree-based agentic reasoning + execution feedback | ⭐⭐⭐⭐⭐ |
| IterClean | https://dl.acm.org/doi/10.1145/3674399.3674436 | Nov 2024 | Detect-verify-repair loop with self-verification | ⭐⭐⭐⭐⭐ |
| ProfiliTable | https://arxiv.org/abs/2605.12376 | May 2026 | Profiling-driven multi-agent with feedback | ⭐⭐⭐⭐⭐ |
| Can LLMs Clean Up Your Mess? | https://arxiv.org/abs/2601.17058 | Jan 2026 | Comprehensive survey of LLM-based cleaning | ⭐⭐⭐⭐⭐ |
| CleanAgent | https://arxiv.org/abs/2403.08291 | Mar 2024 | Autonomous standardization + code generation | ⭐⭐⭐⭐ |
| Exploring LLM Agents for Cleaning... | https://arxiv.org/abs/2503.06664 | Apr 2025 | Downstream model performance as reward signal | ⭐⭐⭐⭐ |
| DeepVerifier | https://arxiv.org/abs/2601.15808 | Apr 2026 | Rubric-guided verification for agents | ⭐⭐⭐⭐ |
| AutoDCWorkflow | https://arxiv.org/abs/2412.06724 | Dec 2024 | Iterative workflow auto-generation | ⭐⭐⭐⭐ |
| A Survey of Data Agents | https://arxiv.org/abs/2510.23587 | Oct 2025 | Taxonomy of 100+ data agents | ⭐⭐⭐⭐⭐ |
| DataGovBench | https://arxiv.org/abs/2512.04416 | Dec 2025 | Benchmark + evaluation framework | ⭐⭐⭐⭐ |
| ActiveClean | https://arxiv.org/abs/1601.03797 | 2016 | Progressive cleaning + model updates | ⭐⭐⭐ |
| LLMDap | https://www.vldb.org/2025/Workshops/VLDB-Workshops-2025/DEC/DEC25_5.pdf | 2025 | LLM-based data profiling | ⭐⭐⭐ |

---

## 🚀 Key Insights Across Papers

### **Consensus on Architecture**
- **Perception**: Data profiling + anomaly detection (statistical + ML-based)
- **Planning**: LLM as planner with chain-of-thought reasoning
- **Execution**: Tool-use (Pandas, SQL, regex, imputation)
- **Verification**: Critical missing piece in most systems — your differentiator!

### **Verification Patterns**
- **IterClean**: LLM as self-verifier in prompt
- **DeepVerifier**: Rubric-based outcome verification
- **Exploring LLM Agents**: Downstream model performance as signal
- **Your innovation**: Combine all three (self-verification + rubrics + downstream metrics)

### **Open Problems**
1. **Causal cleaning**: Why did an error occur? (Root cause analysis)
2. **Multi-table dependencies**: Foreign keys, schema graphs
3. **Production reliability**: Hallucination-resistant verification
4. **Human-in-the-loop**: When to ask a human vs. act autonomously
5. **Explainability**: Audit trails for regulated domains

---

## 📝 Citation Format (BibTeX)

If you use these papers, cite them! Here are a few key ones:

```bibtex
@article{fan2026deepprep,
  title={DeepPrep: An LLM-Powered Agentic System for Autonomous Data Preparation},
  author={Fan, Meihao and Fan, Ju and Zhang, Yuxin and Zhang, Shaolei and Du, Xiaoyong},
  journal={arXiv preprint arXiv:2602.07371},
  year={2026}
}

@inproceedings{ni2024iterclean,
  title={IterClean: An Iterative Data Cleaning Framework with Large Language Models},
  booktitle={ACM Turing Award Celebration Conference},
  author={Ni, Wei and Miao, Xiaoye and Zhang, Keting and others},
  year={2024}
}

@article{xu2026profiletable,
  title={ProfiliTable: Profiling-Driven Tabular Data Processing via Agentic Workflows},
  author={Xu, Beicheng and Liu, Wei and others},
  journal={arXiv preprint arXiv:2605.12376},
  year={2026}
}
```

---

## 💡 Final Note

These papers represent the **cutting edge (2024-2026)** of the field. Most are either:
- From top-tier venues (VLDB, SIGMOD, EMNLP)
- Recent arXiv preprints (within 1-2 months of publication)
- Production systems deployed by major companies (ByteDance DeepPrep, others)

**Your project sits at the intersection of 3-4 of these papers' key ideas:**
1. DeepPrep's tree-based reasoning
2. IterClean's verification loop
3. Downstream model performance feedback
4. Multi-agent profiling architectures

This is genuinely novel territory. Build carefully, evaluate rigorously, and you'll have something publication-worthy. 🚀

