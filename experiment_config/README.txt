experiment_config/
  prompt_baseline.txt   — reference Mistral prompt (placeholders below)
  prompt_trial.txt      — experiments; same placeholders
  rubric_baseline.json  — reference judge rubric (must match trial keys)
  rubric_trial.json     — experiments

Placeholders in prompt files (literal):
  __PREMISE__  __THEME__  __NEGATIVES__  __REFS__

Copy this folder next to the notebook or into REPO_ROOT so Colab finds it after git clone.
