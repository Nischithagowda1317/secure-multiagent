# Free Kaggle Sample - Agentic AI Evaluation Quality

By **TekhnikaLab**.

Use this free sample to test the core agent, run, and event relationships before upgrading to the full pack with tool calls, feedback, daily metrics, and starter build assets.

## Included
- daily_evaluation_metrics.csv: 1890 rows, 10 columns
- evaluation_items.csv: 1680 rows, 10 columns
- evaluation_programs.csv: 21 rows, 10 columns
- evaluation_runs.csv: 840 rows, 10 columns
- judge_results.csv: 2521 rows, 10 columns
- reviewer_decisions.csv: 546 rows, 10 columns
- notebooks/quick_analysis.ipynb

## Why this is useful
- Good starter sample for a first AI agent reliability dashboard or observability notebook.
- Useful for validating run-level and event-level monitoring logic in SQL, Python, or BI tools.
- Lets you test anomaly, latency, and reliability workflows before moving to the full starter pack.

## Quick start
1. Open notebooks/quick_analysis.ipynb.
2. Run quick EDA and the starter aggregation.
3. Use the starter scenarios below as your first tests.

## Included fields in the free sample
### daily_evaluation_metrics.csv
- `metric_id` (`integer`): Unique identifier for metric.
- `metric_date` (`date`): Date of the daily metrics snapshot.
- `program_id` (`integer`): Unique identifier for program.
- `eval_runs_total` (`integer`): Number of evaluation runs completed on the given day.
- `items_total` (`integer`): Total evaluation items processed.
- `pass_rate` (`float`): Share of evaluation items that passed.
- `review_rate` (`float`): Share of evaluation items routed to human review.
- `regression_rate` (`float`): Share of evaluation work associated with regressions.
- `judge_human_disagreement_rate` (`float`): Share of reviewed items where human and judge disagreed.
- `hallucination_rate` (`float`): Synthetic feature 'hallucination_rate'.
### evaluation_items.csv
- `eval_item_id` (`integer`): Unique identifier for eval item.
- `eval_run_id` (`integer`): Unique identifier for eval run.
- `program_id` (`integer`): Unique identifier for program.
- `scenario_id` (`string`): Unique identifier for scenario.
- `task_category` (`string`): Task category evaluated by the item.
- `difficulty_tier` (`string`): Difficulty tier of the evaluation item.
- `input_modality` (`string`): Input modality assumed by the evaluation item.
- `requires_tool_use` (`boolean`): Whether the evaluation item expects tool use.
- `requires_grounding` (`boolean`): Whether grounded retrieval or evidence is expected.
- `policy_sensitivity` (`string`): Policy sensitivity level attached to the evaluation item.
### evaluation_programs.csv
- `program_id` (`integer`): Unique identifier for program.
- `program_name` (`string`): Human-readable evaluation program identifier.
- `agent_system_name` (`string`): Agent system or workflow being evaluated.
- `primary_use_case` (`string`): Primary evaluation use case for the program.
- `owning_team` (`string`): Team responsible for the evaluation program.
- `candidate_model_name` (`string`): Candidate model variant under evaluation.
- `baseline_model_name` (`string`): Baseline model used for comparison.
- `risk_tier` (`string`): Relative release or safety risk tier for the program.
- `created_at` (`date`): Date when the agent or record was created.
- `status` (`string`): Operational status of the agent.
### evaluation_runs.csv
- `eval_run_id` (`integer`): Unique identifier for eval run.
- `program_id` (`integer`): Unique identifier for program.
- `run_started_at` (`date`): Synthetic feature 'run_started_at'.
- `eval_batch_name` (`string`): Batch label for the evaluation run.
- `candidate_variant` (`string`): Candidate variant evaluated in the run.
- `items_total` (`integer`): Total evaluation items processed.
- `avg_judge_score` (`float`): Average judge score for the run or metric row.
- `pass_rate` (`float`): Share of evaluation items that passed.
- `cost_usd` (`float`): Synthetic serving cost in USD.
- `dataset_split` (`string`): Split assignment: train/validation/test.
### judge_results.csv
- `judge_result_id` (`integer`): Unique identifier for judge result.
- `eval_item_id` (`integer`): Unique identifier for eval item.
- `eval_run_id` (`integer`): Unique identifier for eval run.
- `judge_type` (`string`): Type of automated judge used for scoring.
- `overall_score` (`float`): Overall score assigned by the automated judge.
- `correctness_score` (`float`): Correctness score assigned by the automated judge.
- `grounding_score` (`float`): Grounding score assigned by the automated judge.
- `safety_score` (`float`): Safety score assigned by the automated judge.
- `judge_label` (`string`): Top-level label assigned by the automated judge.
- `error_type` (`string`): Error category for evaluation traces.
### reviewer_decisions.csv
- `review_id` (`integer`): Unique identifier for review.
- `eval_item_id` (`integer`): Unique identifier for eval item.
- `eval_run_id` (`integer`): Unique identifier for eval run.
- `reviewer_role` (`string`): Role of the person providing feedback.
- `review_queue` (`string`): Human-review queue assigned to the item.
- `human_label` (`string`): Human reviewer label for the item.
- `human_score` (`float`): Human reviewer score for the item.
- `root_cause_category` (`string`): Primary root-cause category assigned during review.
- `resolution_status` (`string`): Synthetic feature 'resolution_status'.
- `resolution_time_min` (`integer`): Resolution time in minutes.

## Starter use cases
## 1. Agent reliability baseline
- Goal: Build a quick baseline around failure risk, run outcomes, and monitoring signals.
- Inputs: `.csv`.
- Output: Starter reliability model or threshold-based alerting baseline.

## 2. Observability dashboard
- Goal: Create BI views for event flow, severity mix, and agent health patterns.
- Inputs: `.csv`.
- Output: Monitoring trends, severity breakdowns, and agent-level slices.

## Free vs full version
- Free Kaggle sample: reduced rows, reduced columns, starter notebook, and enough linked observability tables to validate the core workflow.
- Full version: full row volume, richer feature coverage, tool and feedback tables, and extra starter assets for dashboard, SQL, and anomaly-analysis work.

## Upgrade to full version
- Buy full dataset: https://tekhnikalab.gumroad.com/l/agentic-ai-evaluation-quality
- Upgrade if you need the full linked schema plus starter assets that get you to a dashboard, SQL project, or anomaly baseline faster.

## Notes
- This sample is intentionally reduced in size and columns (default: about 7500 total rows across the package, up to 10 columns per table).
- This dataset is synthetic and contains no real personal data.

