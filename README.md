---
title: HMER System
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# HMER System: Handwritten Mathematical Expression Recognition

## Overview :
This is a handwritten mathematical expression recognizer that takes images of math written by hand and converts them into LaTeX code. Think of it like OCR (optical character recognition), but specifically trained to understand mathematical notation like fractions, integrals, Greek letters, and complex expressions.

---

## Problem & Solution

**The Problem:**
- Computers can't easily understand handwritten math the way they understand printed text
- Manually typing complex mathematical expressions is time-consuming and error-prone
- Existing OCR systems fail on mathematical notation with special symbols and layouts

**The Solution:**
- Deep learning model that recognizes handwritten math from images or canvas drawings
- Outputs proper LaTeX code that can be rendered or used in documents
- Web interface for easy interaction without requiring command-line knowledge

---

## Key Features

✓ Recognizes handwritten mathematical symbols and expressions  
✓ Outputs token sequences that convert to proper LaTeX notation  
✓ Web interface with canvas drawing support  
✓ Image upload functionality  
✓ Live LaTeX rendering in the browser  
✓ Handles complex expressions (fractions, integrals, subscripts, superscripts)  

---

## How It Works: System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT (Image)                            │
│              Handwritten Math Expression                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   DenseNet Encoder           │
        │   (ResNet-based)             │
        │                              │
        │  Extracts visual features    │
        │  from handwritten image      │
        └──────────────┬───────────────┘
                       │
                       ▼ (Dense Feature Vector)
        ┌──────────────────────────────┐
        │  Transformer Decoder         │
        │                              │
        │  Generates token sequence    │
        │  using Beam Search           │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  LaTeX Token Sequence        │
        │  "frac sqrt alpha sin ..."   │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  LaTeX Rendering             │
        │  (MathJax in Browser)        │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   OUTPUT                     │
        │   Rendered Math Expression   │
        └──────────────────────────────┘
```

---

## HMER Pipeline Overview

The HMER System follows a structured end-to-end pipeline:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Input Image │───▶│   Encoder    │───▶│   Decoder    │───▶│   Output     │
│              │    │  (DenseNet)  │    │(Transformer) │    │  (LaTeX)     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      ↓                   ↓                    ↓                    ↓
   Normalize         Extract Features    Generate Tokens      Render Math
   Preprocess        2D Spatial Info     with Attention
   Augment           Dense Vector        Beam Search
```

### Pipeline Stages:

**1. Input Preprocessing**
- Normalize image dimensions and pixel values
- Data augmentation for training robustness
- Convert to tensor format for model input

**2. Encoder (DenseNet)**
- Processes 2D image through convolutional layers
- Outputs dense feature maps representing visual information
- Creates compact representation of mathematical structure

**3. Decoder (Transformer)**
- Reads encoder output using attention mechanisms
- Generates LaTeX tokens sequentially
- Uses beam search to find optimal token sequence

**4. Output Generation**
- Converts token sequence to LaTeX string
- Renders in browser using MathJax
- Returns both LaTeX code and visual representation

---

## Neural Network Architecture in Detail

### Encoder: DenseNet-Based Feature Extractor

#### Layer-by-Layer Breakdown

```
Layer 1: Input Normalization
├── Shape: [Batch, 3, 224, 224]
├── Operation: Normalize pixel values to [0, 1] range
└── Purpose: Standardize image input for consistent model behavior

Layer 2: Initial Convolution Block
├── Conv2d(in_channels=3, out_channels=64, kernel_size=7, stride=2, padding=3)
├── BatchNorm2d(64)
├── ReLU Activation
├── MaxPool2d(kernel_size=3, stride=2, padding=1)
├── Output Shape: [Batch, 64, 56, 56]
└── Purpose: Extract low-level visual features (edges, textures) and reduce spatial dimensions

Layer 3: DenseBlock 1 (6 dense layers)
├── Structure: 6 sequential dense layers with growth_rate=32
├── Each layer: Conv(1×1) → Conv(3×3) with concatenated inputs
├── Input: [Batch, 64, 56, 56] | Output: [Batch, 256, 56, 56]
├── Activation: ReLU (learns non-linear feature representations)
└── Purpose: Build dense feature maps by reusing connections from all previous layers

Layer 4: Transition Layer 1
├── Conv1x1(in_channels=256, out_channels=128)
├── AvgPool2d(kernel_size=2, stride=2)
├── Output Shape: [Batch, 128, 28, 28]
└── Purpose: Reduce channel dimensions and spatial size for computational efficiency

Layer 5: DenseBlock 2 (12 dense layers)
├── Structure: 12 sequential dense layers with growth_rate=32
├── Input: [Batch, 128, 28, 28] | Output: [Batch, 512, 28, 28]
├── Activation: ReLU (learns mid-level features like symbols and strokes)
└── Purpose: Capture more complex structural patterns in mathematical expressions

Layer 6: Transition Layer 2
├── Conv1x1(in_channels=512, out_channels=256)
├── AvgPool2d(kernel_size=2, stride=2)
├── Output Shape: [Batch, 256, 14, 14]
└── Purpose: Compress features while maintaining spatial localization information

Layer 7: DenseBlock 3 (24 dense layers)
├── Structure: 24 sequential dense layers with growth_rate=32
├── Input: [Batch, 256, 14, 14] | Output: [Batch, 1024, 14, 14]
├── Activation: ReLU (learns high-level semantic features)
└── Purpose: Develop deep representations capturing mathematical notation relationships

Layer 8: Transition Layer 3
├── Conv1x1(in_channels=1024, out_channels=512)
├── AvgPool2d(kernel_size=2, stride=2)
├── Output Shape: [Batch, 512, 7, 7]
└── Purpose: Further dimensionality reduction before final dense block

Layer 9: DenseBlock 4 (16 dense layers)
├── Structure: 16 sequential dense layers with growth_rate=32
├── Input: [Batch, 512, 7, 7] | Output: [Batch, 2048, 7, 7]
├── Activation: ReLU (learns finest-grained feature details)
└── Purpose: Create rich, comprehensive feature representation of entire expression

Layer 10: Encoder Output (Feature Maps)
├── Shape: [Batch, 2048, 7, 7]
├── Total Features: 2048 channels × 49 spatial locations
└── Purpose: Provide spatially-aware feature maps ready for transformer decoder attention
```

**Encoder Summary:**
- **Total Parameters:** ~7 million
- **Key Mechanism:** Dense connections allow gradient flow and feature reuse
- **Output:** Compact but information-rich representation capturing visual structure of math

---

### Decoder: Transformer Sequence Generator

#### Layer-by-Layer Breakdown

```
Layer 1: Input Feature Preparation
├── Input: [Batch, 49, 2048] (49 spatial locations, 2048 features each)
├── Operation: Reshape encoder output to sequence format
└── Purpose: Convert 2D feature maps to 1D sequence for transformer processing

Layer 2: Token Embedding
├── Embedding(num_embeddings=vocab_size, embedding_dim=512)
├── Input: Token IDs [Batch, Seq_Length]
├── Output: [Batch, Seq_Length, 512]
├── Purpose: Convert discrete token indices to continuous vector representations

Layer 3: Positional Encoding
├── Operation: Add sinusoidal positional encodings to embeddings
├── Formula: PE(pos, 2i) = sin(pos/10000^(2i/d_model))
├── Output: [Batch, Seq_Length, 512]
└── Purpose: Inject position information so model knows token order and relative positions

Layer 4-9: Transformer Decoder Blocks (6 identical blocks)

  ├─ Block 1 (Example detailed):
  │
  │  Sub-layer 1: Multi-Head Self-Attention
  │  ├── Input: [Batch, Seq_Length, 512]
  │  ├── Num Heads: 8
  │  ├── Head Dimension: 512 / 8 = 64
  │  ├── Operation: Split into 8 parallel attention heads
  │  │   For each head: Q = Linear(512→64), K = Linear(512→64), V = Linear(512→64)
  │  │   Attention = softmax(QK^T / √64) × V
  │  ├── Output: [Batch, Seq_Length, 512]
  │  ├── Activation: Softmax (normalizes attention weights to probability distribution)
  │  └── Purpose: Learn dependencies between previously generated tokens (what to focus on)
  │
  │  Sub-layer 2: Cross-Attention (Encoder-Decoder)
  │  ├── Query: From decoder (self-attention output) [Batch, Seq_Length, 512]
  │  ├── Key, Value: From encoder features [Batch, 49, 512]
  │  ├── Num Heads: 8
  │  ├── Operation: Q from decoder attends to encoder's K,V across all spatial locations
  │  ├── Output: [Batch, Seq_Length, 512]
  │  ├── Activation: Softmax (focuses on relevant image regions)
  │  └── Purpose: Link generated tokens to specific visual features in the image
  │
  │  Sub-layer 3: Feed-Forward Network (FFN)
  │  ├── Dense Layer 1: Linear(512 → 2048)
  │  ├── Activation: ReLU (introduces non-linearity)
  │  ├── Dense Layer 2: Linear(2048 → 512)
  │  ├── Output: [Batch, Seq_Length, 512]
  │  └── Purpose: Apply non-linear transformations for complex token relationships
  │
  │  Sub-layer 4: Residual Connections & Layer Normalization
  │  ├── Operation: Output = LayerNorm(Input + SubLayerOutput)
  │  └── Purpose: Stabilize training and improve gradient flow through deep network
  │
  │  ├─ Block 2-6: Identical structure (repeated 5 more times)
  │  │  └── Each block refines token sequence predictions through stacked attention
  │  │      and non-linear transformations
  │  │
  │  └─ Purpose: Stack multiple layers to capture complex long-range dependencies
  │     (e.g., numerator structure affects denominator in fractions)

Layer 10: Output Projection
├── Linear(in_features=512, out_features=vocab_size)
├── Input: [Batch, Seq_Length, 512]
├── Output: [Batch, Seq_Length, vocab_size]
├── Purpose: Map decoder representations to probability distribution over vocabulary

Layer 11: Beam Search Decoder
├── Algorithm: Width K=10 (maintains top-10 hypotheses)
├── Scoring: log_probability + coverage_penalty (prevents token repetition)
├── Operation: Expands each hypothesis with all possible next tokens
├── Selection: Keeps K best sequences based on combined score
├── Output: Single best LaTeX token sequence
└── Purpose: Find globally optimal token sequence (better than greedy single-token choices)

Layer 12: Output Sequence
├── Output: Token sequence like ["frac", "{", "sqrt", "{", "x", "}", "}", "{", "2", "}"]
├── Shape: [Seq_Length]
└── Purpose: Final LaTeX token representation ready for rendering
```

**Decoder Summary:**
- **Total Parameters:** ~60 million (majority from 6 transformer blocks)
- **Key Mechanism:** Multi-head attention connects decoder tokens to encoder image features
- **Sequence Length:** Variable (longest = ~250 tokens for complex expressions)
- **Output:** Probability distribution over vocabulary at each token position

---

### Complete End-to-End Data Flow

```
INPUT: Handwritten Math Image (3 × 224 × 224)
    │
    ▼
[Encoder: DenseNet]
├─ Conv + Pool (3 → 64 channels) → [Batch, 64, 56, 56]
├─ DenseBlock1 (6 layers) → [Batch, 256, 56, 56]
├─ Transition1 + AvgPool → [Batch, 128, 28, 28]
├─ DenseBlock2 (12 layers) → [Batch, 512, 28, 28]
├─ Transition2 + AvgPool → [Batch, 256, 14, 14]
├─ DenseBlock3 (24 layers) → [Batch, 1024, 14, 14]
├─ Transition3 + AvgPool → [Batch, 512, 7, 7]
├─ DenseBlock4 (16 layers) → [Batch, 2048, 7, 7]
└─ Output: Rich feature maps [Batch, 49, 2048]
    │
    ▼
[Decoder: Transformer]
├─ Token Embedding + Positional Encoding → [Batch, Seq, 512]
├─ Block1: Self-Attention + Cross-Attention + FFN → [Batch, Seq, 512]
├─ Block2-6: (repeat same pattern, refine predictions)
├─ Output Projection → [Batch, Seq, vocab_size]
└─ Beam Search → Final token sequence
    │
    ▼
OUTPUT: LaTeX Token Sequence
"frac { sqrt { x } } { 2 }"
    │
    ▼
[MathJax Rendering]
Display: $$\frac{\sqrt{x}}{2}$$
```

---

```python
Transformer Decoder Structure:
├── Input: Encoder Features [Batch, Seq_Len, Feature_Dim]
│
├── Embedding Layer
│   ├── Token Embedding (vocab_size → embedding_dim)
│   └── Positional Encoding (adds position information)
│
├── Transformer Decoder Blocks (N=6 layers)
│   ├── Block 1
│   │   ├── Multi-Head Self-Attention (8 heads)
│   │   │   ├── Query, Key, Value projections
│   │   │   ├── Scaled Dot-Product Attention
│   │   │   └── Attention(Q,K,V) = softmax(QK^T/√d)V
│   │   │
│   │   ├── Cross-Attention (Encoder-Decoder)
│   │   │   └── Attends to encoder feature maps
│   │   │
│   │   ├── Feed-Forward Network (FFN)
│   │   │   ├── Dense(d_model → 2048)
│   │   │   ├── ReLU Activation
│   │   │   └── Dense(2048 → d_model)
│   │   │
│   │   └── Layer Normalization + Residual Connections
│   │
│   └── Blocks 2-6: (same structure repeated)
│
├── Output Projection
│   └── Dense(d_model → vocab_size)
│
└── Beam Search Decoder
    ├── Maintains top-K hypotheses
    ├── Expands each hypothesis with all possible next tokens
    ├── Scores using log-probability + coverage penalty
    └── Returns best K sequences
```

**Key Characteristics:**
- Multi-head self-attention for parallel information processing
- Cross-attention between decoder and encoder features
- Positional encoding preserves sequence order
- Beam search avoids greedy decoding mistakes

---

## Technology Stack

### Deep Learning & ML
- **Framework:** PyTorch Lightning (training) + PyTorch (inference)
- **Architecture:** Encoder-Decoder with Transformer
- **Computer Vision:** DenseNet encoder for feature extraction
- **Decoding Strategy:** Beam search with coverage mechanism
- **Experiment Tracking:** Weights & Biases (W&B)

### Backend & API
- **REST API:** FastAPI
- **Server:** Runs inference and handles requests

### Frontend
- **UI:** HTML/CSS/JavaScript (vanilla)
- **Math Rendering:** MathJax for LaTeX display
- **Canvas:** Browser drawing support for handwritten input

### Dataset
- **Training Data:** CROHME dataset (Competition on Recognition of Handwritten Mathematical Expressions)

---

## Technical Details

### Why These Choices?

**DenseNet Encoder**
- Efficient feature extraction without excessive memory usage
- Strong performance on visual feature representation
- Handles variable input sizes well
- Dense connections enable feature reuse and gradient flow

**Transformer Decoder**
- Captures long-range dependencies (e.g., numerator affects denominator in fractions)
- Parallel computation during training
- Attention mechanisms focus on relevant image regions
- Self-attention learns structural relationships between tokens

**Beam Search Decoding**
- Explores multiple possible token sequences simultaneously
- Finds globally better solutions than greedy decoding
- Prevents early mistakes from ruining the entire expression
- Includes coverage mechanism to avoid repeating visual regions

**FastAPI**
- Minimal code for exposing model as web service
- Fast asynchronous request handling
- Built-in request validation and documentation

---

## Current State & Future Plans

### What It Does Now
- Recognizes handwritten math expressions from the CROHME dataset
- Achieves competitive accuracy on standard test benchmarks
- Provides interactive web demo with canvas and upload options
- Generates exact LaTeX representation of mathematical notation

### Future Directions
- **Broader Dataset Support:** Train on more diverse handwriting styles and writing tools (pen vs iPad, etc.)
- **Hybrid Recognition:** Support handwritten text mixed with math (like problem annotations)
- **Auto Solver Integration:** Build automatic equation solver that recognizes AND solves expressions
- **Mobile Optimization:** Improve real-time performance for mobile devices
- **Domain-Specific Fine-tuning:** Specialize for calculus, linear algebra, or other mathematical domains
- **Improved Notation:** Better handling of specialized mathematical notation
- **Multi-line Expressions:** Support for systems of equations and multi-line mathematical content

---

## Quick Start

### Installation

**Prerequisites:** 
- Python 3.8+
- NVIDIA GPU (Recommended for training, CPU is fine for inference)
- CUDA toolkit installed

```bash
# Clone the repository and navigate to project
git clone https://github.com/yourusername/HMER-System.git
cd HMER-System

# Install dependencies
pip install -r requirements.txt
```

### Running the Demo

```bash
# Start the web server
fastapi run demo.py

# Open your browser and go to:
# http://localhost:8000
```

### Training & Testing

```bash
# Train a new model
python train.py

# Evaluate on test data
python test.py
```

---

## Project Structure

```
HMER-System/
├── README.md                 # This file
├── demo.py                   # FastAPI web server
├── train.py                  # Model training script
├── test.py                   # Model evaluation script
├── requirements.txt          # Python dependencies
├── checkpoints/              # Saved model weights
├── static/                   # Frontend files (HTML/CSS/JS)
├── templates/                # HTML templates
├── models/                   # Model architecture definitions
│   ├── encoder.py            # DenseNet encoder
│   ├── decoder.py            # Transformer decoder
│   └── hmer_model.py         # Full encoder-decoder
└── utils/                    # Utility functions
    ├── data_loader.py
    ├── preprocessor.py
    └── beam_search.py
```

---

## How to Use the Demo

1. **Canvas Drawing:** Click on the canvas and draw your math expression
2. **Image Upload:** Upload a photo or image file of handwritten math
3. **See Results:** The recognized LaTeX appears below with live rendering
4. **Copy LaTeX:** Use the generated LaTeX code in documents or other applications

---

## Performance Metrics

- Trained on CROHME dataset (handwritten mathematical expressions)
- Beam search (width=10) provides better accuracy than greedy decoding
- Coverage mechanism reduces token repetition errors
- Web interface provides real-time inference
- DenseNet feature extraction provides robust spatial representation
- Multi-head attention (8 heads) captures diverse token relationships

---

## Built As

A student project exploring how Transformers and deep learning solve real computer vision problems beyond standard image classification. This demonstrates practical end-to-end application development: from model architecture design to training to deployment as an interactive web service.

The HMER System showcases the power of combining specialized architectures (DenseNet for vision + Transformers for sequences) to tackle complex structured prediction problems in mathematical expression recognition.
