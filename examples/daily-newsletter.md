# Daily Newsletter - 2025-12-27

*Generated on 2025-12-28 07:19:26 UTC*

## Table of Contents

**Total items: 7**

- [Article](#article) (1 items)
- [Arxiv](#arxiv) (2 items)
- [Huggingface](#huggingface) (2 items)
- [Youtube](#youtube) (2 items)

---

## Arxiv

*2 item(s)*

### 1. [2512.12967] QwenLong-L1.5: Post-Training Recipe for Long-Context Reasoning and Memory Management

**Source:** [https://arxiv.org/html/2512.12967](https://arxiv.org/html/2512.12967)

## What did the author accomplish ?

- **What**  
  Introduced **QwenLong‑L1.5**, a 30‑B parameter LLM that attains state‑of‑the‑art long‑context reasoning (up to 4 M tokens) through a **complete post‑training recipe**.  

- **Why**  
  Existing work focuses on pre‑training or architectural tricks, leaving a gap in **post‑training methods** that can (i) generate high‑quality long‑context data, (ii) train stably on extremely long sequences, and (iii) enable reasoning beyond the physical context window. QwenLong‑L1.5 fills this gap, delivering performance comparable to proprietary flagship models (GPT‑5, Gemini‑2.5‑Pro) while remaining fully open‑source.


### Visual Summary  

![Overall results of QwenLong‑L1.5 across six long‑context benchmarks (Figure 1 from the paper)](https://arxiv.org/html/2512.12967v1/x1.png){width=600px}


## Training compute

The paper does **not disclose exact GPU hours or cluster size**. Training is performed on the 30 B base model with on‑policy RL, which typically requires high‑memory GPUs (e.g., 8 × A100 40 GB or similar) to handle 256 K‑token windows and the multi‑stage schedule. Users should provision sufficient GPU memory to fit the model + KV cache for the longest stage (≈ 120 K tokens).

---

### 2. [2509.25123] From $f(x)$ and $g(x)$ to $f(g(x))$: LLMs Learn New Skills in RL by Composing Old Ones

**Source:** [https://arxiv.org/html/2509.25123](https://arxiv.org/html/2509.25123)

## What did the authors accomplish?  

- **What** – Demonstrated that reinforcement‑learning (RL) post‑training can *teach* large language models (LLMs) genuinely new reasoning skills, not just re‑weight existing ones.  
- **Why** – This settles a heated debate: many recent works claim RL only “reranks” the base model’s outputs, but the authors provide concrete, controlled evidence that RL can *compose* previously learned atomic abilities into higher‑order capabilities that generalize to unseen compositions, deeper nesting, and even to a different task (Countdown).  


## What can you use yourself?  

| Resource / Tool | Description / Link |
|-----------------|--------------------|
| **Model** | Llama‑3.1‑8B‑Instruct (used as the base LLM). |
| **RL optimizer** | DAPO (Distributed Actor‑Critic with Preference Optimization) – used with GRPO rewards. |
| **Fine‑tuning method** | Rejection Fine‑Tuning (RFT) – open‑source implementations available in the `verL` repo. |
| **Dataset** | Synthetic string‑transformation suite (25 functions, 50 k Level‑1 & Level‑2 examples). Code for all functions is in Appendix D of the paper. |
| **Evaluation scripts** | Pass@k, Avg@32 for Countdown, and failure‑mode classifier (based on Gemini‑2.5‑Pro). |
| **Training hyper‑parameters** (the ones that worked best) | • Stage 1 RFT: 2 epochs, lr = 2e‑5, batch = 128. <br>• Stage 2 RL: DAPO, lr = 1e‑6, on‑policy batch = 16, rollout size = 16, KL = 0, entropy = 0. <br>• RFT baseline (iterative): same lr as Stage 1, 128‑batch, repeat until convergence. |
| **Methodology you can adopt** | 1️⃣ Pre‑train (or start from a strong base LLM).  <br>2️⃣ Use RFT on *atomic* tasks to embed low‑level skills.  <br>3️⃣ Construct a *compositional* RL dataset where the reward only signals overall correctness.  <br>4️⃣ Train with GRPO/DAPO – the binary reward forces the model to discover the composition rule.  <br>5️⃣ Validate on held‑out deeper compositions and on a downstream task that shares the same atomic primitives. |
| **Potential extensions** | • Replace synthetic strings with real‑world functions (e.g., code APIs, math operators). <br>• Scale to larger models (13B, 70B) to test whether the same RL incentive yields bigger gains. <br>• Combine RL with curriculum learning: start from Level‑1, gradually increase nesting depth. |


## References to further follow / read  

- **Core RL papers** – DAPO: *“Distributed Actor‑Critic with Preference Optimization”* (2024). <br>GRPO: *“Group Relative Preference Optimization”* (2024).  
- **Human skill‑composition theory** – Anderson, J. R. (1982). *Acquisition of Cognitive Skills*.  
- **Contrasting viewpoints** – Yue et al. (2025) *“Does RL really improve LLMs?”*; Gandhi et al. (2025) *“Cognitive Behavior Transfer”*.  
- **Related compositional work** – Yin et al. (2025) *Learning Compositionality via In‑Context Learning*; Sun et al. (2025) *OMEGACL* (shows RL without explicit compositional incentive fails).  
- **Open‑source code** – The authors release the synthetic dataset, function definitions, and training scripts (GitHub link in the paper’s supplementary material).

---

## Huggingface

*2 item(s)*

### 1. Paper page - GTR-Turbo: Merged Checkpoint is Secretly a Free Teacher for Agentic VLM Training

**Source:** [https://arxiv.org/html/2512.13043](https://arxiv.org/html/2512.13043)

## What did the author accomplish ?

- **What**  
  Introduced **GTR‑Turbo**, a lightweight upgrade to Guided Thought Reinforcement (GTR) that eliminates the need for an external, expensive teacher model when training multi‑turn vision‑language agents. By merging historical RL checkpoints into a “free” teacher, GTR‑Turbo provides dense, step‑level guidance via supervised fine‑tuning (SFT) or KL‑based logit distillation.

- **Why**  
  Multi‑turn RL for VLM agents suffers from sparse rewards, long‑horizon credit assignment, and “thought/entropy collapse”. Prior solutions (e.g., GTR, On‑Policy Distillation) rely on costly privileged models (GPT‑4o, Gemini), limiting scalability, reproducibility, and increasing training time and monetary cost. GTR‑Turbo offers a self‑contained, cheaper, and faster alternative while achieving equal or superior performance.


## What can you use yourself?

- **Tools & Resources**  
  - **Base model**: `Qwen2.5‑VL‑7B‑Instruct` (and later `Qwen3‑VL‑8B‑Instruct`).  
  - **Merging method**: **TIES** (Trim‑Elect‑Sign) – see Yadav et al., 2023.  
  - **RL algorithm**: PPO (Schulman et al., 2017) with standard hyper‑parameters (clip = 0.1, entropy = 0.01, etc.).  
  - **LoRA** fine‑tuning (Hu et al., 2022) to keep GPU memory low.  

- **Recipes / Methodologies**  
  1. **Checkpoint Buffer & Merging** – Store every PPO checkpoint; merge after each epoch using TIES (density = 0.8).  
  2. **Thought Guidance** – Choose between:  
     - **SFT**: Collect teacher‑generated thoughts in a dataset `𝒟` and add an SFT loss.  
     - **KL‑Distillation**: Compute reverse KL on the fly and subtract it (scaled by β = 1) from the environment reward.  
  3. **Weight Averaging** – SMA works out‑of‑the‑box; EMA with α ≈ 0.5 gives a good trade‑off.  

- **Hyper‑parameters / Best Practices** (taken from Appendix B)

| Category | Parameter | Value |
|----------|-----------|-------|
| Learning rate schedule | CosineAnnealingLR | 1e‑5 → 1e‑9 (25 steps) |
| Discount factor (γ) | 0.9 |
| GAE λ | 0.95 |
| PPO clip ε | 0.1 |
| Entropy coeff. | 0.01 |
| Value loss coeff. | 0.5 |
| LoRA rank (r) | 128 |
| LoRA α | 256 |
| LoRA dropout | 0.05 |
| KL loss coeff. (β) | 1 (KL variant) |
| Thought probability | 0.5 (Points24), 0.2 (ALFWorld) |
| TIES density | 0.8 |
| Generation temperature (agent) | 0.2 |
| Teacher temperature (SFT) | 0.2 – 0.9 (ramp) |

- **Datasets**  
  - **Points24** (card‑game with arithmetic reasoning) – labels from a task solver.  
  - **ALFWorld** (embodied household tasks) – image‑only observations; sub‑goal/reward definitions as in the paper.  

- **Potential Integration**  
  - Apply GTR‑Turbo to any VLM‑based agent where a strong external teacher is unavailable (e.g., robotics, video‑game bots).  
  - Combine with other RL tricks (GRPO, DAPO) for further stability.  
  - Use the merged‑checkpoint teacher to generate synthetic “process” data for downstream fine‑tuning.


## References to further follow / read ?

- **Guided Thought Reinforcement (GTR)** – Wei et al., 2025.  
- **On‑Policy Distillation** – Lu et al., 2025.  
- **TIES merging** – Yadav et al., “Trim‑Elect‑Sign for Model Merging”, 2023.  
- **Model merging literature** – Ilharco et al., 2022; Yu et al., 2024; Li et al., 2025.  
- **RL4VLM framework** – Zhai et al., 2025.  
- **ALFWorld benchmark** – Sridhar et al., 2020.  
- **Points24 benchmark** – Zhai et al., 2025.  
- **LoRA** – Hu et al., 2022.  

**Paper & Code**: https://arxiv.org/html/2512.13043 (full PDF, figures, and pseudocode).  
**Model checkpoints** (Qwen2.5‑VL‑7B, Qwen3‑VL‑8B) are publicly available from the **Tencent AI Lab** model hub.

---

### 2. Paper page - Latent Implicit Visual Reasoning

**Source:** [https://arxiv.org/html/2512.21218](https://arxiv.org/html/2512.21218)

## What did the author accomplish ?

- **What** – Introduced **Latent Implicit Visual Reasoning (LIVR)**, a task‑agnostic method that lets large multimodal models (LMMs) discover and exploit *visual reasoning tokens* without any explicit intermediate supervision.  
- **Why** – Existing LMMs are text‑centric and struggle on vision‑heavy tasks; prior works that inject visual intermediates require costly, task‑specific annotations and embed human bias. LIVR removes these constraints, achieving state‑of‑the‑art performance on a wide suite of perception‑centric benchmarks while also improving multi‑task instruction tuning.


## What can you use yourself?

| Resource | Description |
|---|---|
| **Models** | Qwen2.5‑VL‑3B‑Instruct, Qwen3‑VL‑4B‑Instruct, LLaVA‑OneVision‑1.5‑4B‑Instruct (all open‑source). |
| **Code / Implementation** | The authors fine‑tune using **LoRA** (rank = 16, α = 32, dropout = 0.05) on the language backbone; vision encoder & projector stay frozen. Only the latent‑token embeddings are unfrozen. |
| **Datasets** | Custom 1k‑example VQA‑style training sets derived from COCO, ArtBench‑10, SPair‑71k, HPatches, FunKPoint, MID, NIGHTS, and PixMo‑Count. Evaluation uses the BLINK benchmark (9 perception‑heavy tasks). |
| **Hyper‑parameters (default)** | <ul><li>K = 16 latent tokens (placed *after* the prompt).</li><li>Stage 1 = 4 epochs, Stage 2 = 6 epochs (total 10) for single‑task.</li><li>Learning rate = 1e‑4 (AdamW), weight decay = 0.01.</li><li>Batch size = 1 per GPU, 8‑step gradient accumulation → effective batch = 8.</li></ul> |
| **Best practices** | • Use the *both‑sides* bottleneck (answer ↛ image, prompt ↛ image). <br>• Keep latent embeddings *unshared* (each token learns its own vector). <br>• Position latents *after* the textual prompt for better conditioning. |
| **Potential integrations** | • Plug LIVR into any LMM that follows the vision‑encoder → projector → LLM pipeline. <br>• Combine with instruction‑tuning or chain‑of‑thought prompting for richer multimodal reasoning. |


## References to further follow / read ?

- **Paper** – *Latent Implicit Visual Reasoning* (arXiv 2512.21218) – https://arxiv.org/abs/2512.21218  
- **Related works**  
  - LLaVA‑CoT, Visual‑CoT, UV‑CoT (text‑based chain‑of‑thought for vision).  
  - Aurora, Mirage (explicit visual intermediates).  
  - Coconut, “Think Before You Speak” (latent‑space reasoning).  
- **Datasets** (all publicly available)  
  - BLINK benchmark – https://github.com/BLINK-benchmark  <br>
  - PixMo‑Count – https://huggingface.co/datasets/allenai/pixmo-count  <br>
  - COCO – http://cocodataset.org  <br>
  - ArtBench‑10 – https://github.com/ArtBench  <br>
  - SPair‑71k – https://github.com/zhenglinsp/SPair-71k  <br>
  - HPatches – https://github.com/hpatches/hpatches-benchmark  <br>
  - FunKPoint – https://github.com/zhenglinsp/FunKPoint  <br>
  - MID – https://github.com/zhenglinsp/MID  <br>
  - NIGHTS (DreamSim) – https://github.com/zhenglinsp/NIGHTS  

- **Implementation details** – Appendix B (training setup) and Appendix A (dataset construction) in the paper.

---

## Youtube

*2 item(s)*

### 1. (2226) Steering LLM Behavior Without Fine-Tuning - YouTube

**Source:** [https://www.youtube.com/watch?v=F2jd5WuT-zg](https://www.youtube.com/watch?v=F2jd5WuT-zg)

## What did the author accomplish ?

- **What** – Demonstrated a practical method to *steer* the behavior and “personality” of large language models (LLMs) **at inference time** without any fine‑tuning or heavy prompt‑engineering.  
- **Why** – To give researchers and developers a lightweight, reversible way to modulate model outputs (e.g., tone, factuality, ethical bias) while keeping the original weights untouched, opening new avenues for rapid prototyping, safety‑testing, and mechanistic interpretability.


## What can you use yourself?

| Resource | What it provides |
|----------|------------------|
| **Blog post / demo space** | Interactive notebook showing the full pipeline – https://huggingface.co/spaces/dlouapre/eiffel‑tower‑llama |
| **Sparse Auto‑Encoder collection** | Ready‑made SAEs for several LLaMA variants – https://huggingface.co/collections/dlouapre/sparse-auto-encoders-saes-for-mechanistic-interpretability |
| **Neuronpedia** | searchable database of discovered neurons & their semantics – https://www.neuronpedia.org |
| **Python recipe** | Minimal 15‑line script (see snippet above) that can be dropped into any 🤗 Transformers workflow. |
| **Best‑practice tips** | <ul><li>Use middle‑range layers (8‑12) for best trade‑off between interpretability & impact.</li><li>Average hidden states over 10‑20 examples to reduce noise when computing steering vectors.</li><li>Scale the steering vector with a small coefficient (≈ 0.1‑0.3) to avoid destabilising generation.</li></ul> |
| **Hyper‑parameters** | • `layer = 12` (for 70‑B LLaMA)  <br>• `steering_scale = 0.2`  <br>• `batch_size = 4` for collecting example activations. |


## References to further follow / read ?

- **Main blog / demo** – https://huggingface.co/spaces/dlouapre/eiffel‑tower‑llama  
- **Sparse Auto‑Encoder hub** – https://huggingface.co/collections/dlouapre/sparse-auto-encoders-saes-for-mechanistic-interpretability  
- **Neuronpedia** – https://www.neuronpedia.org  
- **Related talks** (mechanistic interpretability & neuro‑stimulation): <br>• *The most complex model we actually understand* – Welch Labs (YouTube) <br>• *Transformers, the tech behind LLMs* – 3Blue1Brown (YouTube) <br>• *RAG vs Fine‑Tuning vs Prompt Engineering* – IBM Technology (YouTube)

---

### 2. (2226) Designing a Customer-Centric Business Model - YouTube

**Source:** [https://www.youtube.com/watch?v=L1Km-hJt-uI](https://www.youtube.com/watch?v=L1Km-hJt-uI)

## What did the author accomplish ?

- **What** – Michael Skok (founding partner at Underscore VC) delivered a concise, practical framework for **designing a customer‑centric business model**. He showed how to surface the core value a startup creates and then shape the revenue‑generation mechanics so that the company captures value **in concert with the customer’s success**.  

- **Why** – Most early‑stage ventures build a product first and only later think about how the model will actually make money. By putting the **customer’s outcomes at the centre of the model**, founders can create sustainable, defensible businesses that grow with their users instead of fighting against them.


## What can you use yourself?

| Resource / Tool | How to Apply |
|-----------------|--------------|
| **Startup Secrets Sandbox** – interactive worksheets & templates | <https://bit.ly/3Cwv0nK> – use the “Customer‑Value Canvas” and “Pricing‑Fit Sheet” to map your own value metric and pricing structure. |
| **Value‑Based Pricing Checklist** (from the talk) | 1. Identify measurable outcome 2. Quantify dollar impact 3. Set price as % of impact 4. Test with pilot 5. Refine. |
| **MVBM (Minimum Viable Business Model) Playbook** | Run a 2‑week pilot with a single customer segment, collect outcome data, and adjust pricing before full launch. |
| **Unit‑Economics Calculator** (simple spreadsheet) | Plug in CAC, churn, LTV derived from the value‑based price to verify profitability early. |
| **Customer‑Success Loop Template** | Set up a quarterly review cadence where product tweaks are directly tied to the value metric trends. |

*No specific hyper‑parameters were discussed (the content is strategic, not technical).*


## References to further follow / read ?

- **Video:** “Designing a Customer‑Centric Business Model” – Harvard Innovation Labs (Mar 25 2023) – <https://www.youtube.com/watch?v=L1Km-hJt-uI>  
- **Speaker Bio:** Michael Skok, Underscore VC – <https://underscoredvc.com/team/michael-skok/>  
- **Startup Secrets Sandbox (frameworks & templates):** <https://bit.ly/3Cwv0nK>  
- Related Harvard i‑lab playlists (for deeper dives):  
  - *Vision, Mission & Culture* – <https://www.youtube.com/watch?v=RI4UKUlnIDc>  
  - *Value Props: Create a Product People Will Actually Buy* – <https://www.youtube.com/watch?v=q8d9uuO1Cf4>  
  - *Startup Business Models and Pricing | Startup School* – <https://www.youtube.com/watch?v=oWZbWzAyHAE>  

These resources give you concrete tools to start building a business model that **captures value together with your customers**, turning their success into your sustainable revenue.

---

## Article

*1 item(s)*

### 1. The Optimal Token Baseline

**Source:** [https://yingru.notion.site/The-Optimal-Token-Baseline-399211a558b782cfa936014c0d42dfb8](https://yingru.notion.site/The-Optimal-Token-Baseline-399211a558b782cfa936014c0d42dfb8)

## What did the author accomplish ?

- **What**  
  The paper introduces the **Optimal Token Baseline (OTB)** – a theoretically‑derived, token‑level variance‑reduction technique for on‑policy reinforcement learning (RL) of large language models (LLMs). OTB eliminates the “training collapse” that plagues long‑horizon, sparse‑reward RL by stabilising gradient norms.

- **Why**  
  In RL‑fine‑tuned LLMs, gradient variance grows with trajectory length and reward sparsity, causing sudden spikes in gradient norm and catastrophic performance drops. Existing baselines (group‑mean, leave‑one‑out, value‑function baselines) treat all tokens as equally noisy and therefore cannot control this variance, especially in multi‑turn, tool‑integrated reasoning (TIR) tasks.


## What can you use yourself?

- **Tools & Resources**  
  - **Code**: Integrated into the VeRL framework – PR [#4678](https://github.com/volcengine/verl/pull/4678)  
  - **Dataset**: Filtered reward‑augmented dataset – HuggingFace 🤗 [`Jiawei415/DPAO_filter`](https://huggingface.co/datasets/Jiawei415/DPAO_filter)  
  - **Models evaluated**:  
    - Qwen2.5‑7B (base)  
    - Qwen3‑8B‑Base & Qwen3‑14B‑Base  

- **Methodology / Recipes**  
  1. **Training loop** – Full on‑policy RL (REINFORCE style) with OTB as the baseline.  
  2. **Batch / Group size** – Small groups (as low as **N = 4**) achieve the same performance as N = 32 baselines, cutting token usage by **≈ 62 % (single‑turn)** and **≈ 66 % (multi‑turn TIR)**.  
  3. **Hyper‑parameters (used in the paper)**  
     - Rollout batch size: **128** (TIR) / **64** (single‑turn)  
     - Mini‑update size: **128**  
     - Max response length: **8192** (extended to 16 k in ablations)  
     - Max turn (TIR): **5** (tested up to 10)  
     - Learning rate: **1e‑6**  
     - Optimiser: AdamW (default VeRL settings)  

- **Practical Tips**  
  - Use the logit‑gradient proxy to compute realised energy **without extra backward passes**.  
  - Exclude padding/EOS tokens when aggregating \(\hat W_t\); OTB naturally handles variable‑length sequences.  
  - Monitor **gradient variance** (Appendix D) – a rising variance predicts imminent collapse; OTB keeps it flat.  
  - Combine OTB with **Geometric‑Mean Sequence Masking** (Geo‑RS) for larger models (14 B) to further improve stability.


## References to further follow / read ?

1. **Original paper (pre‑print)** – “The Optimal Token Baseline: Variance Reduction for Long‑Horizon LLM‑RL” – Dec 20 2025.  
2. **Foundational variance‑reduction works**  
   - Dayan (1991) – *Reinforcement Comparison*  
   - Greensmith et al. (2004) – *Variance reduction techniques for gradient estimates*  
   - Weaver & Tao (2013) – *The optimal reward baseline for gradient‑based RL*  
3. **Related LLM‑RL baselines**  
   - GRPO (Group‑based REINFORCE) – Shao et al., 2024.  
   - RLOO – Ahmadian et al., 2024.  
4. **Masking / Sampling strategies**  
   - Masked Importance Sampling (MIS) – Liu et al., 2025.  
   - Geometric‑Mean Sequence Masking (Geo‑RS) – Liu et al., 2025.  
5. **Logit dynamics** – Li Y., “Logit Dynamics in Softmax Policy Gradient Methods”, arXiv 2025.  
6. **Tool‑Integrated Reasoning (TIR)** – Xue et al., “SimpleTIR”, arXiv 2025.

---

---

*End of newsletter for 2025-12-27*