# Overview

**RevealVLLMSafetyEval** is a comprehensive pipeline for evaluating Vision-Language Models (VLMs) on their compliance with harm-related policies. It automates the creation of adversarial multi-turn datasets and the evaluation of model responses, supporting responsible AI development and red-teaming efforts.

---

# Directory Structure

```
RevealVLLMSafetyEval/
│
├── README.md                # Project documentation
├── LICENSE                  # Apache 2.0 License
├── requirements.txt         # Python dependencies
├── generate_sets.ps1        # Script to run the full set creation pipeline
│
├── Common/
│   └── Policy/
│       └── SubPolicySegments.py   # Harm policy definitions
│
├── SetCreationPipeline/
│   ├── search_query_gen.py       # Search query generation
│   ├── image_mining.py           # Image mining from Bing
│   ├── seed_gen.py               # Seed and metadata generation
│   ├── conv_gen.py               # Conversational expansion
│   ├── Data/
│   │   ├── ImageSearchQueries/   # Generated search queries
│   │   ├── MinedImages/          # Downloaded images and metadata
│   │   ├── SeedGen/              # Generated seeds
│   │   ├── ConvGen/              # User-turn sets
│   │   └── ConvGenTextPorted/    # Text-only dialogues
│   └── Prompts/                  # Prompt templates for each stage
│
├── VLMEvalPipeline/
│   ├── main-gpt4o.py             # Multi-turn eval (GPT-4o)
│   ├── main-opensource.py        # Multi-turn eval (open-source)
│   ├── main-seeds-gpt4o.py       # Single-turn eval (GPT-4o)
│   ├── main-seeds-opensource.py  # Single-turn eval (open-source)
│   ├── main-gpt4o-text.py        # Text-only eval (GPT-4o)
│   ├── eval.py                   # Evaluation logic
│   ├── models.py                 # Model loading utilities
│   ├── utils_lang.py             # Conversation/image utilities
│   └── EvalChains/               # Harm-specific evaluation chains
│
└── ...
```

---

# Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd RevealVLLMSafetyEval
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure credentials:**
   - Ensure you have access to Azure OpenAI and Bing Image Search API keys as required by the pipeline scripts.
   - Set up any necessary environment variables for authentication.

4. **Run the pipeline:**
   - To generate datasets for all harm categories:
     ```powershell
     ./generate_sets.ps1
     ```
   - To run evaluation, use the scripts in `VLMEvalPipeline/` as needed (see script docstrings for details).

---

# Harm Policy Definition

All harm policies are defined in the `Common/Policy/SubPolicySegments.py` file. This file contains the rules and segments for each harm category (e.g., Misinformation, Sexual Harm, Violence, Refusal) that guide the dataset generation and evaluation processes.

# Project Overview

This repository provides a pipeline for evaluating Vision-Language Models (VLMs) on their ability to comply with harm-related policies. The workflow is divided into two main parts:

- **Set Creation Pipeline**: Automates the generation of datasets for harm policy evaluation.
- **VLM Eval Pipeline**: Runs evaluations of target LMs using the generated datasets.

# Set Creation Pipeline

Located in `SetCreationPipeline/`, this pipeline consists of several stages:

1. **Search Query Generation:**  
   Generates image search queries using the GPT-4o model tailored to each harm policy. Prompt file: `SetCreationPipeline\Prompts\search_query_gen.md`

2. **Image Mining:**  
   Mines images using the Bing Image Search API based on the generated queries.

3. **Seed Generation:**  
   Utilizes the GPT-4o model to create image seeds and associated metadata from mined images. Prompt file: `SetCreationPipeline\Prompts\seed_gen.md`, `SetCreationPipeline\Prompts\seed_gen_user.md` 

4. **Conversational Expansion:**  
   Produces policy-specific dialogues by setting up a conversation generation pipeline with the Azure OpenAI client. Prompt file: `SetCreationPipeline\Prompts\conv_gen_system.md`, `SetCreationPipeline\Prompts\conv_gen_user.md`

5. **Porting to text-only format for evaluation:**  
   Converts the generated dialogues to text-only format for evaluation experiment. Prompt file: `SetCreationPipeline\Prompts\port_to_text_only.md`

The `SetCreationPipeline\` directory contains the outputs for each step where `ImageSearchQueries` corresponds to the search queries generated, `MinedImages` contains the mined images, `SeedGen` contains the generated seeds, `ConvGen` contains the generated user-turn sets, and `ConvGenTextPorted` contains the text-only port of the generated dialogues.

## Execution

To run the complete set creation pipeline for all harm categories, use the provided PowerShell script:

```powershell
./generate_sets.ps1
```

You can also run each stage individually by executing the corresponding Python scripts in the `SetCreationPipeline/` directory.

# VLM Eval Pipeline

This section is responsible to run the actual evaluation for the target LMs using the generated datasets. The pipeline involves the following components:

1. **Conversation Generation**:  
   - Single-turn: `main-seeds-gpt4o.py`, `main-seeds-opensource.py`
   - Multi-turn: `main-gpt4o.py`, `main-opensource.py`
   - Text-only: `main-gpt4o-text.py`
   - All use evaluation chains in `EvalChains/` (Misinformation, SexualHarm, Violence, Refusal).

2. **Evaluation** (`eval.py`):  
   Runs the evaluation logic, interfacing with Azure OpenAI and applying harm-specific evaluation chains.

3. **Utilities**:  
   - `models.py`: Loads and configures VLMs and tokenizers.  
   - `utils_lang.py`: Provides conversation and image handling utilities.

**Evaluation Results**:  
- Single-turn: `EvalsSeeds/`  
- Multi-turn: `Evals/`  
- Text-only: `EvalsTextPorted/`

# Additional Notes

- **Requirements**: All dependencies are listed in `requirements.txt`.
- **License**: The project uses the Apache 2.0 License (`LICENSE`).
- **Prompts**: All prompt templates for generation and evaluation are in `SetCreationPipeline/Prompts/`.
