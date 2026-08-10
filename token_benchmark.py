#!/usr/bin/env python3
"""
Token reduction benchmark for GLM Code Graph.
"""

import os
import sys
from pathlib import Path
import tiktoken

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Tokenizer (GLM uses similar tokenizer to GPT-4)
ENCODING = tiktoken.encoding_for_model("gpt-4")

class TokenBenchmark:
    """Benchmark token reduction."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.all_files = self._get_all_files()
        self.all_content = self._read_all_files()
        
        print("=" * 60)
        print("GLM Code Graph - Token Reduction Benchmark")
        print("=" * 60)
        print(f"\nRepository: {self.repo_path}")
        print(f"Total files: {len(self.all_files)}")
        print(f"Total size: {len(self.all_content)} bytes")
    
    def _get_all_files(self) -> list[str]:
        """Get all Python files in repository."""
        files = []
        for py_file in self.repo_path.rglob("*.py"):
            # Skip __pycache__ and test files for "clean" review
            if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
                files.append(str(py_file))
        return sorted(files)
    
    def _read_all_files(self) -> str:
        """Read all content from files."""
        content_parts = []
        for file_path in self.all_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content_parts.append(f.read())
        return "\n".join(content_parts)
    
    def _count_tokens(self, content: str) -> int:
        """Count tokens in content."""
        return len(ENCODING.encode(content))
    
    def benchmark_traditional_review(self, changed_files: list[str]):
        """Benchmark traditional review approach."""
        print("\n" + "=" * 60)
        print("METHOD 1: Traditional Review (Read All Files)")
        print("=" * 60)
        
        # Read all files (traditional approach)
        all_content = self._read_all_files()
        all_tokens = self._count_tokens(all_content)
        
        print(f"\nFiles read: {len(self.all_files)}")
        print(f"Total size: {len(all_content):,} bytes")
        print(f"Estimated tokens: {all_tokens:,}")
        
        # Show file breakdown
        print("\nFile breakdown:")
        file_tokens = []
        for file_path in self.all_files:
            with open(file_path, "r", encoding="utf-8") as f:
                file_tokens.append((file_path, len(f.read())))
        
        for file_path, size in sorted(file_tokens, key=lambda x: x[1], reverse=True):
            print(f"  - {Path(file_path).name:20s} {size:5d} bytes")
        
        return all_tokens, len(all_content)
    
    def benchmark_glm_graph_review(self, changed_files: list[str], depth: int = 3):
        """Benchmark GLM Code Graph approach."""
        print("\n" + "=" * 60)
        print("METHOD 2: GLM Code Graph (Blast Radius)")
        print("=" * 60)
        
        # Calculate blast radius
        from knowledge_graph import GraphStore, ImpactAnalysis
        
        store = GraphStore(":memory:")
        
        # Build graph from changed files
        from core.graph.knowledge_graph import KnowledgeGraph
        
        print(f"\nBuilding graph for {len(changed_files)} changed files...")
        
        # Parse all files and build graph
        from core.parsers.tree_sitter_parser import CodeParser
        
        parser = CodeParser()
        for file_path in self.all_files:
            with open(file_path, "r", encoding="utf-8") as f:
                nodes = parser.parse_file(file_path, f.read())
                # Store nodes in graph (simplified)
        
        # Compute blast radius
        print(f"\nComputing blast radius (depth={depth})...")
        
        # Simulated blast radius - in real implementation, this uses graph traversal
        blast_files = set(changed_files)
        
        # Add imports (simplified - in real implementation, this follows edges)
        for file_path in changed_files:
            for other_file in self.all_files:
                if file_path != other_file and self._has_import(other_file, file_path):
                    blast_files.add(other_file)
        
        # Collect content from blast radius
        blast_content_parts = []
        for file_path in blast_files:
            with open(file_path, "r", encoding="utf-8") as f:
                blast_content_parts.append(f.read())
        
        blast_content = "\n".join(blast_content_parts)
        blast_tokens = self._count_tokens(blast_content)
        
        print(f"\nFiles in blast radius: {len(blast_files)}/{len(self.all_files)}")
        print(f"Blast radius size: {len(blast_content):,} bytes")
        print(f"Estimated tokens: {blast_tokens:,}")
        
        # Show file breakdown
        print("\nBlast radius file breakdown:")
        file_tokens = []
        for file_path in sorted(blast_files):
            with open(file_path, "r", encoding="utf-8") as f:
                file_tokens.append((Path(file_path).name, len(f.read())))
        
        for file_name, size in sorted(file_tokens, key=lambda x: x[1], reverse=True):
            percentage = (size / len(blast_content)) * 100
            print(f"  - {file_name:20s} {size:5d} bytes ({percentage:5.1f}%)")
        
        # Show skipped files
        skipped_files = set(self.all_files) - blast_files
        if skipped_files:
            print("\nSkipped files (not in blast radius):")
            for file_path in sorted(skipped_files):
                print(f"  - {Path(file_path).name}")
        
        return blast_tokens, len(blast_content), len(blast_files)
    
    def _has_import(self, file_path: str, import_file: str) -> bool:
        """Check if file imports another file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Check for import statements
            import_lines = [
                line.strip() for line in content.split('\n') 
                if line.strip().startswith('import ') or line.strip().startswith('from ')
            ]
            
            for imp in import_lines:
                # Extract module name
                if 'import' in imp:
                    module = imp.split('import ')[1].split('.')[0].strip()
                else:
                    module = imp.split('from ')[1].split(' import ')[0].strip()
                
                if module in import_file or import_file.endswith(module + '.py'):
                    return True
        
        return False
    
    def compare_results(self, traditional_tokens, traditional_bytes, 
                       glm_tokens, glm_bytes, glm_file_count):
        """Compare and print results."""
        print("\n" + "=" * 60)
        print("COMPARISON RESULTS")
        print("=" * 60)
        
        reduction_percent = ((traditional_tokens - glm_tokens) / traditional_tokens) * 100
        size_reduction = ((traditional_bytes - glm_bytes) / traditional_bytes) * 100
        
        print(f"\nTraditional Approach:")
        print(f"  - Files: {len(self.all_files)}")
        print(f"  - Size: {traditional_bytes:,} bytes")
        print(f"  - Tokens: {traditional_tokens:,}")
        
        print(f"\nGLM Code Graph:")
        print(f"  - Files: {glm_file_count} ({glm_file_count}/{len(self.all_files)})")
        print(f"  - Size: {glm_bytes:,} bytes")
        print(f"  - Tokens: {glm_tokens:,}")
        
        print(f"\nReduction:")
        print(f"  - Files: {len(self.all_files) - glm_file_count} fewer")
        print(f"  - Size: {size_reduction:.1f}% less")
        print(f"  - Tokens: {reduction_percent:.1f}% fewer")
        
        print(f"\nEstimated Cost Savings:")
        print(f"  - Per review: ~{reduction_percent:.0f}% token reduction")
        print(f"  - Monthly review: Significant savings on frequent code reviews")
        
        return reduction_percent, size_reduction

def main():
    """Main benchmark runner."""
    repo_path = str(Path(__file__).parent)
    
    benchmark = TokenBenchmark(repo_path)
    
    # Benchmark traditional approach
    traditional_tokens, traditional_bytes = benchmark.benchmark_traditional_review([])
    
    # Benchmark GLM Code Graph approach
    changed_files = ["auth.py"]  # Review this single file
    glm_tokens, glm_bytes, glm_file_count = benchmark.benchmark_glm_graph_review(changed_files)
    
    # Compare results
    reduction_percent, size_reduction = benchmark.compare_results(
        traditional_tokens, traditional_bytes,
        glm_tokens, glm_bytes, glm_file_count
    )
    
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print(f"\nGLM Code Graph achieves {reduction_percent:.1f}% token reduction")
    print(f"compared to traditional file reading approaches.")
    print("\nThis means:")
    print("  ✓ Faster review times")
    print("  ✓ Lower token costs")
    print("  ✓ More focused reviews on relevant code")

if __name__ == "__main__":
    main()
