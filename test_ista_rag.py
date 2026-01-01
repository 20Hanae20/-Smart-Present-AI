#!/usr/bin/env python3
"""Quick test script to verify ISTA RAG integration"""
import sys
sys.path.insert(0, '/app')

from app.rag.pipeline import rag_answer

# Test query
query = "emploi du temps NTIC2-FS201 lundi"
print(f"\n🔍 Query: {query}\n")

context, sources = rag_answer(query, n_results=5)

print("=" * 80)
print("📄 RAG CONTEXT:")
print("=" * 80)
print(context if context else "(empty)")

print("\n" + "=" * 80)
print("🔗 SOURCES:")
print("=" * 80)
for i, src in enumerate(sources, 1):
    print(f"{i}. {src}")

print("\n" + "=" * 80)
