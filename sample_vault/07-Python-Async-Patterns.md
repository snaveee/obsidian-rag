---
title: Python Async Concurrency Patterns
tags: [python, concurrency, asyncio]
aliases: [Async Patterns]
---

# Python Async Concurrency Patterns

Building scalable AI backends requires non-blocking IO for external HTTP calls and thread pooling for CPU-bound tasks.

## ThreadPoolExecutor for CPU-bound ML

Heavy computation (such as cross-encoder scoring) should never block the main asyncio event loop. Using `run_in_executor` or background threading keeps FastAPI responsive:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def async_rerank(query, candidates):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, sync_reranker, query, candidates)
```

This pattern integrates directly with our overall system design in [[01-System-Architecture]].

