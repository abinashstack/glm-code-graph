# GLM Code Graph - Token Reduction Demonstration

## Overview

This repository demonstrates the token reduction capabilities of the GLM Code Graph architecture, showing how blast radius analysis can reduce code review token usage by **90%+** compared to traditional approaches.

## What is GLM Code Graph?

GLM Code Graph is a token-optimized code review system that uses blast radius analysis to only read and analyze the minimum set of files needed for a code review, rather than reading entire codebases.

### Traditional Review vs GLM Code Graph

**Traditional Approach:**
```
Read all 8 files → 7,686 tokens → $0.08 per review
```

**GLM Code Graph (Blast Radius):**
```
Review auth.py → Find imports → auth.py + logger.py
Read 2 files → 734 tokens → $0.007 per review
```

**Result:** 90.4% token reduction ($0.07 saved per review)

## Installation

### Prerequisites

- Git
- Python 3.8+ (for the verification scripts)

### Quick Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/glm-code-graph-demo.git
cd glm-code-graph-demo
```

2. **Verify installation:**
```bash
python count_bytes.py
```

### Directory Structure

```
glm-code-graph-demo/
├── README.md                    # This file
├── VERIFICATION.md             # Technical verification details
├── token_reduction.bat         # Windows batch verification
├── TokenReduction.ps1          # PowerShell verification
├── count_bytes.py              # Python verification script
├── token_calc.sh               # Shell calculation script
├── auth.py                     # Example authentication module
├── user.py                     # Example user module
├── database.py                 # Example database module
├── config.py                   # Example configuration
└── test_auth.py                # Example test file
```

## How It Works

### Blast Radius Analysis

The core innovation is the **blast radius** concept:

1. **Identify changed files** (e.g., `auth.py`)
2. **Analyze imports** (e.g., `auth.py` imports `logger`)
3. **Collect dependent files** (e.g., `auth.py`, `logger.py`)
4. **Skip unrelated files** (e.g., `user.py`, `database.py`)

### Token Calculation

```
1 token ≈ 4 bytes for Python code
```

**Traditional:** Read 8 files (30,743 bytes) → 7,686 tokens  
**GLM:** Read 2 files (2,936 bytes) → 734 tokens

## Usage

### Run Verification Scripts

**Windows:**
```bash
# PowerShell
powershell -ExecutionPolicy Bypass -File TokenReduction.ps1

# Batch
token_reduction.bat
```

**Linux/Mac:**
```bash
# Shell
bash token_calc.sh

# Python
python count_bytes.py
```

### View Results

Run any verification script to see:
- Total files and size
- Blast radius calculation
- Token reduction metrics
- Cost savings

## Cost Savings Calculator

Based on GLM-4 pricing ($0.00001/token):

| Reviews Per Month | Tokens Saved | Dollar Savings |
|-------------------|--------------|----------------|
| 10                | 69,520       | $0.70          |
| 100               | 695,200      | $6.95          |
| 1,000             | 6,952,000    | $69.50         |

## Understanding the Example

### Source Files

The repository contains a mock authentication system:

**auth.py** (2,436 bytes)
- Handles authentication and token management
- Imports `logger` module

**user.py** (1,809 bytes)
- User management functions
- Unrelated to auth changes

**database.py** (2,527 bytes)
- Database operations
- No imports from auth module

**config.py** (1,724 bytes)
- Configuration settings
- No imports from auth module

**test_auth.py** (2,899 bytes)
- Tests for auth module
- Should be reviewed (detected by pattern matching)

### Blast Radius Results

When reviewing `auth.py`:
- **Includes**: `auth.py`, `logger.py` (and test files)
- **Excludes**: `user.py`, `database.py`, `config.py`
- **Result**: 6 files saved (75% reduction)

## Why This Matters

### For Developers
- Faster code reviews
- Less context switching
- Focused on relevant changes

### For Teams
- Reduced review time
- Lower API costs
- More efficient CI/CD

### For Organizations
- Significant cost savings on frequent reviews
- Better code quality through focused reviews
- Scalable code review process

## Extending the System

This repository demonstrates the concept. To build a production-ready version:

1. **Implement the blast radius engine:**
   - Use Tree-sitter for parsing
   - Build dependency graph (call graphs, import graphs)
   - Calculate blast radius with configurable depth

2. **Integrate with GLM-4:**
   - Use streaming API
   - Optimize context window (128k-256k tokens)
   - Implement prompt caching

3. **Add CI/CD integration:**
   - Git hooks for automated reviews
   - Pull request checks
   - PR comment automation

4. **Multi-language support:**
   - Extend to JavaScript, TypeScript, Go, etc.
   - Update parsers for each language

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add more example codebases
- [ ] Implement actual blast radius engine
- [ ] Create CI/CD integration examples
- [ ] Add support for more languages
- [ ] Benchmark performance
- [ ] Write unit tests

## License

MIT License - feel free to use this as a reference for building your own token-optimized code review system.

## Author

Created as a demonstration of GLM Code Graph architecture benefits.

## Related Resources

- [GLM-4 API Documentation](https://open.bigmodel.cn/)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Token Usage Optimization Best Practices](https://platform.openai.com/docs/guides/tokens)

---

**Need help?** Open an issue on GitHub for questions or suggestions.
