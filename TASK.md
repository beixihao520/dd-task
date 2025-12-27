# Overview

Your task is to take a partially implemented “Due Diligence (DD) Survey Analytics Agent” skeleton and improve it so it can run **end-to-end** in a realistic way by fixing at least **one** of the agent tools and integrating **segments into the Pandas analysis engine**.

This skeleton mirrors how a production-grade agent would be structured:

* The LLM is used to produce **structured, validated analysis specifications** (plans, cuts, segments).
* All numerical outputs are computed **deterministically** in Python (Pandas), not by the LLM.
* The system is designed to be **strict** (refuse invalid requests) and **traceable** (save artifacts that show how decisions were made).

**Important:** We do **not** expect a 100% pass rate across all validation suites. The validators are provided as a **guide** to help you understand intended behavior and measure progress. A strong submission may implement a subset well, with clear reasoning and trade-offs.

**Also important:** the codebase is intentionally **littered with bugs and rough edges** (logic bugs, incomplete wiring, inconsistent assumptions, etc.). Part of the task is to spot and fix issues as you go—treat this like taking over a real internal prototype rather than a polished library.

---

# Conceptual summary

## What problem are we solving?

In real DD work, consultants ask questions like:

* “Show NPS by country”
* “Create an Enterprise segment (org size ≥ 1000) and compare NPS”
* “Show top-2-box satisfaction by industry”

A production agent needs to:

1. Interpret those requests,
2. Convert them into **domain objects** (cuts + segments),
3. Validate them sensibly,
4. Execute them deterministically,
5. Produce auditable results.

This task focuses on the “agent skeleton” part: tool orchestration, structured outputs, and correct integration between planning and execution.

## Design patterns you should follow

* **Tool-based architecture:** The agent consists of discrete tools (planner, cut planner, segment builder, executor).
* **Schema-first outputs:** Tools that use the LLM should return structured objects matching the provided schemas.
* **Deterministic execution:** The LLM proposes specs; Pandas computes numbers.
* **Traceability:** Runs should emit artifacts so a reviewer can understand what the agent did and why.

## What “working” means (high level)

At minimum, a submission should:

1. Run end-to-end on the provided demo data (`questions.json`, `responses.csv`).
2. Use AzureOpenAI for LLM-backed tools.
3. Fix **at least one tool** so it can produce valid, useful structured outputs.
4. Integrate segments into the Pandas analysis engine (segment masks + applying them as dimensions/filters).
5. Use validation suites as guidance—passing some is great, passing all is not required.

## Repo structure expectations

You may keep the structure we provide. We expect something broadly like:

* `src/` Python package containing:

  * tool implementations
  * AzureOpenAI client wrapper
  * orchestration pipeline
  * executor integration (Pandas)
* `data/` demo dataset
* validators / tests (provided)
* `README.md`, `explanation.md`

---

# Requirements

## Necessary

### 1) Fix at least one tool (baseline)

You do **not** need to fix all tools before working on execution. The baseline expectation is:

* Implement/fix **at least one** of the LLM-backed tools so it runs and produces grounded structured objects.

Choose one:

#### Option A: Cut-level planning tool (recommended baseline)

* Input: natural language request (e.g., “Show NPS by country”)
* Output: valid `CutSpec`
* Should implement “second-order inference” when applicable:

  * NPS only for `nps_0_10`
  * top-2-box only for Likert
* Should avoid guessing on incompatible requests (fail clearly or ask for disambiguation if you implement the extension flow)

#### Option B: Segment definition tool

* Input: segment name + NL definition
* Output: valid `SegmentSpec` (filter AST)
* Must ground to existing question IDs and valid option codes / numeric thresholds

#### Option C: High-level planning tool

* Input: question dictionary + optional scope
* Output: analysis intents (structured)
* Must stay grounded to the provided question catalog

Anything beyond the first working tool is considered an **extension**.

### 2) Integrate segments into the Pandas analysis engine (core)

The analysis engine is provided and works for non-segmented cuts, but **segments are not yet integrated**.

You must:

* Compile segment definitions (filter AST) into boolean masks
* Allow segments to be used as:

  * **dimensions** (Enterprise vs Non-Enterprise)
  * **filters** (e.g., “NPS for Enterprise only”)
* Ensure outputs include base sizes and stable dimension columns

This can be tested with `validate_engine`. Again: passing everything is not required, but you should aim to make meaningful progress and explain what remains.

### 3) Run artifacts and traceability (core expectation)

A run should emit:

* validated specs (cuts/segments/plans you produced)
* resolution/mapping traces (how NL mapped to IDs/codes, where applicable)
* output tables (CSV/Parquet acceptable)
* a short human-readable summary (`report.md` or similar)

### 4) AzureOpenAI integration (required for LLM tools)

Your implemented tool(s) must use AzureOpenAI for LLM calls. We recommend schema-first / structured outputs.

---

## Optional extensions (high-value)

These are **not required**, but strengthen a submission significantly.

### 1) Interactive ambiguity resolution (ideal extension)

Modify the agent flow so that when ambiguity occurs (e.g., two question IDs match “Geography”), the system:

1. pauses and asks the user to choose from candidate options
2. resumes planning/execution using the selected ID

This can be implemented via:

* CLI prompt interaction
* a simple TUI
* or a lightweight UI (see below)

### 2) Additional tools

Fixing more than one tool (e.g., Cut Planner + Segment Builder + High-Level Planner) beyond your baseline.

### 3) Improved grounding

Better matching of user phrasing to question labels/options (with clear error messages when uncertain).

### 4) Weights / significance testing

Optional metrics or statistical extensions (only if requested / time permits).

### 5) Full-stack demonstration (optional)

You may build a UI to show off full-stack skills (e.g., minimal web app to run queries, resolve ambiguity interactively, and view tables). This is **absolutely not required** and will not be penalized if omitted.

---

# Deliverables

A GitHub repository or zipfile containing:

1. **Python source code** (`src/`)
2. `README.md`

   * setup instructions
   * required environment variables for AzureOpenAI
   * how to run validators / tests (including `validate_engine`)
   * how to run an end-to-end demo
3. `explanation.md`

   * what you implemented and why
   * key trade-offs and known limitations
   * **what you would do with more time** (production hardening, eval improvements, better UX, etc.)
   * any notable bugs you found/fixed and how you approached debugging
4. Example output artifacts from at least one end-to-end run:

   * `runs/<timestamp>/...` folder OR equivalent
   * tool outputs (JSON)
   * output tables (CSV/Parquet)
   * report (`md`/`txt`)

---

# Assessment Criteria

| Area                         | Criteria                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| Baseline tool implementation | Did you get at least one tool working end-to-end with grounded structured outputs?           |
| Segment integration          | Can the executor apply segments as dimensions/filters? Is the approach correct and testable? |
| Accuracy & determinism       | Are NPS/top-2-box/base sizes computed correctly and reproducibly?                            |
| Engineering quality          | Clean structure, readable code, sensible abstractions, error handling                        |
| Traceability                 | Can we follow the agent’s decisions via artifacts/logs?                                      |
| Debugging ability            | Did you identify and fix meaningful bugs? Are fixes well-scoped and explained?               |
| Use of validators            | Do you use validators effectively as a guide and describe gaps where not fully passing?      |
| Explanation & roadmap        | Do you clearly explain what you did and what you’d improve with more time?                   |
| Extensions                   | Ambiguity resolution flow, additional tools, better grounding, optional UI, etc.             |

---

# Appendix

## Provided data

You will be given:

* `questions.json` — question catalog (IDs, labels, types, options)
* `responses.csv` — response-level survey data
* Validation suites:

  * one per tool (planner / cut planner / segment builder)
  * `validate_engine` for execution correctness and segment integration

## Suggested scenarios (guideposts, not strict requirements)

These are typical “happy paths” you can aim for:

1. **NPS by country**

* Cut planner produces `CutSpec` with metric `nps` and dimension `country`
* Executor outputs NPS per country with base sizes

2. **Enterprise segment then NPS**

* Segment tool produces `SegmentSpec` for Enterprise (org size ≥ 1000)
* Cut planner produces a cut comparing NPS for Enterprise vs Non-Enterprise
* Executor outputs both rows with correct bases

3. **Top-2-box satisfaction by country**

* Cut planner produces `top2box` metric for satisfaction Likert question
* Executor outputs correct % and base sizes

## What you are not expected to do

* No deep DD expertise required.
* You do not need to redesign the schemas.
* You do not need to build a UI (optional only).
* You do not need to productionize—but you should describe what you would do next.
